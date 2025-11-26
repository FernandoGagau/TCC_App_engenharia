/**
 * React hook for WebSocket integration
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import { getWebSocketService } from '../services/WebSocketService';

/**
 * Custom hook for WebSocket chat functionality
 * @param {string} sessionId - Chat session ID
 * @param {Object} options - Hook options
 * @returns {Object} WebSocket state and methods
 */
export const useWebSocket = (sessionId, options = {}) => {
    const {
        autoConnect = false, // Changed to false to avoid immediate connection
        onMessage = null,
        onStreamStart = null,
        onStreamChunk = null,
        onStreamEnd = null,
        onError = null,
        baseUrl = 'ws://localhost:8000'
    } = options;

    const [isConnected, setIsConnected] = useState(false);
    const [isReconnecting, setIsReconnecting] = useState(false);
    const [messages, setMessages] = useState([]);
    const [currentStream, setCurrentStream] = useState(null);
    const [typingUsers, setTypingUsers] = useState(new Set());
    const [error, setError] = useState(null);

    const wsService = useRef(null);
    const streamBuffer = useRef({});
    const typingTimeout = useRef({});

    // Initialize WebSocket service
    useEffect(() => {
        wsService.current = getWebSocketService(baseUrl);

        // Setup event listeners
        const handleConnected = () => {
            setIsConnected(true);
            setIsReconnecting(false);
            setError(null);
        };

        const handleDisconnected = () => {
            setIsConnected(false);
        };

        const handleReconnecting = () => {
            setIsReconnecting(true);
        };

        const handleMessage = (data) => {
            const message = {
                id: data.message_id,
                content: data.content,
                role: 'assistant',
                timestamp: data.timestamp,
                metadata: data.metadata
            };

            setMessages((prev) => [...prev, message]);

            if (onMessage) {
                onMessage(message);
            }
        };

        const handleStreamStart = (data) => {
            const streamId = data.message_id;
            streamBuffer.current[streamId] = '';
            setCurrentStream(streamId);

            if (onStreamStart) {
                onStreamStart(data);
            }
        };

        const handleStreamChunk = (data) => {
            const streamId = data.message_id;
            streamBuffer.current[streamId] = (streamBuffer.current[streamId] || '') + data.content;

            // Update message in real-time
            setMessages((prev) => {
                const existingIndex = prev.findIndex(m => m.id === streamId);
                if (existingIndex >= 0) {
                    const updated = [...prev];
                    updated[existingIndex] = {
                        ...updated[existingIndex],
                        content: streamBuffer.current[streamId],
                        isStreaming: true
                    };
                    return updated;
                } else {
                    return [...prev, {
                        id: streamId,
                        content: streamBuffer.current[streamId],
                        role: 'assistant',
                        timestamp: new Date().toISOString(),
                        isStreaming: true
                    }];
                }
            });

            if (onStreamChunk) {
                onStreamChunk(data);
            }
        };

        const handleStreamEnd = (data) => {
            const streamId = data.message_id;

            // Finalize message
            setMessages((prev) => {
                const updated = [...prev];
                const index = updated.findIndex(m => m.id === streamId);
                if (index >= 0) {
                    updated[index] = {
                        ...updated[index],
                        isStreaming: false,
                        metadata: data.metadata
                    };
                }
                return updated;
            });

            // Clean up stream buffer
            delete streamBuffer.current[streamId];
            setCurrentStream(null);

            if (onStreamEnd) {
                onStreamEnd(data);
            }
        };

        const handleTyping = (data) => {
            const userId = data.user_id;

            setTypingUsers((prev) => new Set(prev).add(userId));

            // Clear existing timeout
            if (typingTimeout.current[userId]) {
                clearTimeout(typingTimeout.current[userId]);
            }

            // Remove typing indicator after 3 seconds
            typingTimeout.current[userId] = setTimeout(() => {
                setTypingUsers((prev) => {
                    const updated = new Set(prev);
                    updated.delete(userId);
                    return updated;
                });
            }, 3000);
        };

        const handleError = (data) => {
            setError(data.error);

            if (onError) {
                onError(data);
            }
        };

        // Register event listeners
        wsService.current.on('connected', handleConnected);
        wsService.current.on('disconnected', handleDisconnected);
        wsService.current.on('reconnecting', handleReconnecting);
        wsService.current.on('message', handleMessage);
        wsService.current.on('streamStart', handleStreamStart);
        wsService.current.on('streamChunk', handleStreamChunk);
        wsService.current.on('streamEnd', handleStreamEnd);
        wsService.current.on('typing', handleTyping);
        wsService.current.on('error', handleError);

        // Auto-connect if enabled
        if (autoConnect && sessionId) {
            wsService.current.connect(sessionId).catch((err) => {
                setError(err.message || 'Failed to connect');
            });
        }

        // Cleanup
        return () => {
            wsService.current.off('connected', handleConnected);
            wsService.current.off('disconnected', handleDisconnected);
            wsService.current.off('reconnecting', handleReconnecting);
            wsService.current.off('message', handleMessage);
            wsService.current.off('streamStart', handleStreamStart);
            wsService.current.off('streamChunk', handleStreamChunk);
            wsService.current.off('streamEnd', handleStreamEnd);
            wsService.current.off('typing', handleTyping);
            wsService.current.off('error', handleError);

            // Clear all typing timeouts
            Object.values(typingTimeout.current).forEach(clearTimeout);
        };
    }, [sessionId, autoConnect, onMessage, onStreamStart, onStreamChunk, onStreamEnd, onError, baseUrl]);

    // Send message
    const sendMessage = useCallback((content, metadata = {}, stream = true) => {
        if (wsService.current && content.trim()) {
            // Add user message to local state immediately
            const userMessage = {
                id: Date.now().toString(),
                content,
                role: 'user',
                timestamp: new Date().toISOString(),
                metadata
            };

            setMessages((prev) => [...prev, userMessage]);

            // Send via WebSocket
            wsService.current.sendMessage(content, metadata, stream);
        }
    }, []);

    // Send typing indicator
    const sendTypingIndicator = useCallback(() => {
        if (wsService.current) {
            wsService.current.sendTypingIndicator();
        }
    }, []);

    // Send reaction
    const sendReaction = useCallback((messageId, helpful, rating) => {
        if (wsService.current) {
            wsService.current.sendReaction(messageId, helpful, rating);
        }
    }, []);

    // Connect manually
    const connect = useCallback(async () => {
        if (wsService.current && sessionId) {
            try {
                await wsService.current.connect(sessionId);
            } catch (err) {
                setError(err.message || 'Failed to connect');
            }
        }
    }, [sessionId]);

    // Disconnect manually
    const disconnect = useCallback(() => {
        if (wsService.current) {
            wsService.current.disconnect();
        }
    }, []);

    // Clear messages
    const clearMessages = useCallback(() => {
        setMessages([]);
        streamBuffer.current = {};
    }, []);

    // Load message history
    const loadHistory = useCallback(async (limit = 50, offset = 0) => {
        try {
            const token = localStorage.getItem('auth_token');
            const response = await fetch(
                `/api/chat/sessions/${sessionId}/messages?limit=${limit}&offset=${offset}`,
                {
                    headers: {
                        'Authorization': `Bearer ${token}`
                    }
                }
            );

            if (response.ok) {
                const data = await response.json();
                const historicalMessages = data.messages.map(m => ({
                    id: m.message_id,
                    content: m.content,
                    role: m.role,
                    timestamp: m.timestamp,
                    metadata: m.metadata,
                    reactions: m.reactions
                }));

                setMessages(historicalMessages);
                return data;
            } else {
                throw new Error('Failed to load message history');
            }
        } catch (err) {
            setError(err.message);
            return null;
        }
    }, [sessionId]);

    return {
        // State
        isConnected,
        isReconnecting,
        messages,
        currentStream,
        typingUsers: Array.from(typingUsers),
        error,

        // Methods
        sendMessage,
        sendTypingIndicator,
        sendReaction,
        connect,
        disconnect,
        clearMessages,
        loadHistory
    };
};

export default useWebSocket;