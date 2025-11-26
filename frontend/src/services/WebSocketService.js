/**
 * WebSocket Service for real-time chat communication
 */

class WebSocketService {
    constructor(baseUrl = 'ws://localhost:8000') {
        this.baseUrl = baseUrl;
        this.ws = null;
        this.sessionId = null;
        this.listeners = new Map();
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.reconnectDelay = 3000;
        this.isConnected = false;
        this.messageQueue = [];
    }

    /**
     * Connect to WebSocket server
     * @param {string} sessionId - Chat session ID
     * @param {string} token - Authentication token
     */
    async connect(sessionId, token) {
        this.sessionId = sessionId;
        const wsUrl = `${this.baseUrl}/ws/${sessionId}?token=${token || localStorage.getItem('auth_token')}`;

        return new Promise((resolve, reject) => {
            try {
                this.ws = new WebSocket(wsUrl);

                this.ws.onopen = () => {
                    console.log('WebSocket connected');
                    this.isConnected = true;
                    this.reconnectAttempts = 0;

                    // Process queued messages
                    this.processMessageQueue();

                    // Emit connected event
                    this.emit('connected', { sessionId });
                    resolve();
                };

                this.ws.onmessage = (event) => {
                    try {
                        const data = JSON.parse(event.data);
                        this.handleMessage(data);
                    } catch (error) {
                        console.error('Failed to parse WebSocket message:', error);
                        this.emit('error', { error: 'Invalid message format' });
                    }
                };

                this.ws.onerror = (error) => {
                    console.error('WebSocket error:', error);
                    this.emit('error', { error });
                    reject(error);
                };

                this.ws.onclose = (event) => {
                    console.log('WebSocket disconnected', event);
                    this.isConnected = false;
                    this.emit('disconnected', { code: event.code, reason: event.reason });

                    // Attempt reconnection if not intentionally closed
                    if (event.code !== 1000) {
                        this.handleReconnection();
                    }
                };
            } catch (error) {
                console.error('Failed to create WebSocket:', error);
                reject(error);
            }
        });
    }

    /**
     * Handle incoming WebSocket messages
     * @param {Object} data - Message data
     */
    handleMessage(data) {
        const { type } = data;

        switch (type) {
            case 'connected':
                this.emit('connected', data);
                break;

            case 'message':
                this.emit('message', data);
                break;

            case 'stream_start':
                this.emit('streamStart', data);
                break;

            case 'stream_chunk':
                this.emit('streamChunk', data);
                break;

            case 'stream_end':
                this.emit('streamEnd', data);
                break;

            case 'typing':
                this.emit('typing', data);
                break;

            case 'error':
                this.emit('error', data);
                break;

            case 'ping':
                this.sendPong();
                break;

            case 'pong':
                // Heartbeat response received
                break;

            case 'reaction_saved':
                this.emit('reactionSaved', data);
                break;

            default:
                console.warn('Unknown message type:', type);
                this.emit('unknown', data);
        }
    }

    /**
     * Send a message through WebSocket
     * @param {string} content - Message content
     * @param {Object} metadata - Additional metadata
     * @param {boolean} stream - Enable response streaming
     */
    sendMessage(content, metadata = {}, stream = true) {
        const message = {
            type: 'message',
            content,
            metadata,
            stream,
            timestamp: new Date().toISOString()
        };

        if (this.isConnected && this.ws?.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify(message));
            this.emit('messageSent', message);
        } else {
            // Queue message if not connected
            this.messageQueue.push(message);
            console.warn('WebSocket not connected. Message queued.');
        }
    }

    /**
     * Send typing indicator
     */
    sendTypingIndicator() {
        if (this.isConnected && this.ws?.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify({
                type: 'typing',
                timestamp: new Date().toISOString()
            }));
        }
    }

    /**
     * Send message reaction
     * @param {string} messageId - Message ID
     * @param {boolean} helpful - Is helpful
     * @param {number} rating - Rating (1-5)
     */
    sendReaction(messageId, helpful, rating) {
        if (this.isConnected && this.ws?.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify({
                type: 'reaction',
                message_id: messageId,
                helpful,
                rating,
                timestamp: new Date().toISOString()
            }));
        }
    }

    /**
     * Send pong response
     */
    sendPong() {
        if (this.isConnected && this.ws?.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify({
                type: 'pong',
                timestamp: new Date().toISOString()
            }));
        }
    }

    /**
     * Process queued messages
     */
    processMessageQueue() {
        while (this.messageQueue.length > 0 && this.isConnected) {
            const message = this.messageQueue.shift();
            this.ws.send(JSON.stringify(message));
        }
    }

    /**
     * Handle reconnection logic
     */
    async handleReconnection() {
        if (this.reconnectAttempts >= this.maxReconnectAttempts) {
            console.error('Max reconnection attempts reached');
            this.emit('reconnectFailed', { attempts: this.reconnectAttempts });
            return;
        }

        this.reconnectAttempts++;
        const delay = this.reconnectDelay * Math.min(this.reconnectAttempts, 3);

        console.log(`Attempting to reconnect (${this.reconnectAttempts}/${this.maxReconnectAttempts}) in ${delay}ms...`);
        this.emit('reconnecting', { attempt: this.reconnectAttempts });

        setTimeout(async () => {
            try {
                await this.connect(this.sessionId);
                console.log('Reconnection successful');
                this.emit('reconnected');
            } catch (error) {
                console.error('Reconnection failed:', error);
                this.handleReconnection();
            }
        }, delay);
    }

    /**
     * Register event listener
     * @param {string} event - Event name
     * @param {Function} callback - Event callback
     */
    on(event, callback) {
        if (!this.listeners.has(event)) {
            this.listeners.set(event, []);
        }
        this.listeners.get(event).push(callback);
    }

    /**
     * Remove event listener
     * @param {string} event - Event name
     * @param {Function} callback - Event callback
     */
    off(event, callback) {
        if (this.listeners.has(event)) {
            const callbacks = this.listeners.get(event);
            const index = callbacks.indexOf(callback);
            if (index > -1) {
                callbacks.splice(index, 1);
            }
        }
    }

    /**
     * Emit event to listeners
     * @param {string} event - Event name
     * @param {any} data - Event data
     */
    emit(event, data) {
        if (this.listeners.has(event)) {
            this.listeners.get(event).forEach(callback => {
                try {
                    callback(data);
                } catch (error) {
                    console.error(`Error in event listener for ${event}:`, error);
                }
            });
        }
    }

    /**
     * Disconnect WebSocket
     */
    disconnect() {
        if (this.ws) {
            this.isConnected = false;
            this.ws.close(1000, 'Normal closure');
            this.ws = null;
        }
    }

    /**
     * Get connection status
     * @returns {boolean} Connection status
     */
    isConnected() {
        return this.isConnected && this.ws?.readyState === WebSocket.OPEN;
    }

    /**
     * Get session ID
     * @returns {string} Current session ID
     */
    getSessionId() {
        return this.sessionId;
    }
}

// Singleton instance
let webSocketServiceInstance = null;

/**
 * Get WebSocket service instance
 * @param {string} baseUrl - WebSocket base URL
 * @returns {WebSocketService} WebSocket service instance
 */
export const getWebSocketService = (baseUrl) => {
    if (!webSocketServiceInstance) {
        webSocketServiceInstance = new WebSocketService(baseUrl);
    }
    return webSocketServiceInstance;
};

export default WebSocketService;