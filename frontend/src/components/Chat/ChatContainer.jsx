/**
 * ChatContainer - Main chat interface component
 * Integrates with WebSocket service for real-time communication
 */

import React, { useState, useEffect, useRef } from 'react';
import { Box, Paper, CircularProgress, Alert } from '@mui/material';
import { styled } from '@mui/material/styles';
import { useWebSocket } from '../../hooks/useWebSocket';
import ChatHeader from './ChatHeader';
import MessageList from './MessageList';
import MessageInput from './MessageInput';
import TypingIndicator from './TypingIndicator';

const ChatWrapper = styled(Paper)(({ theme }) => ({
  height: '100vh',
  display: 'flex',
  flexDirection: 'column',
  position: 'relative',
  backgroundColor: theme.palette.background.default,
  [theme.breakpoints.down('sm')]: {
    height: '100%',
    borderRadius: 0,
  },
}));

const LoadingContainer = styled(Box)(({ theme }) => ({
  display: 'flex',
  justifyContent: 'center',
  alignItems: 'center',
  height: '100vh',
  flexDirection: 'column',
  gap: theme.spacing(2),
}));

const ChatContainer = ({ sessionId, projectId, onClose }) => {
  const [isLoading, setIsLoading] = useState(true);
  const [showAlert, setShowAlert] = useState(true);

  const {
    isConnected,
    isReconnecting,
    messages,
    currentStream,
    typingUsers,
    error,
    sendMessage,
    sendTypingIndicator,
    sendReaction,
    connect,
    loadHistory,
    clearMessages
  } = useWebSocket(sessionId, {
    autoConnect: false, // Don't auto-connect on mount
    baseUrl: process.env.REACT_APP_WS_URL || 'ws://localhost:8000'
  });

  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  // Load message history on mount (only if session exists)
  useEffect(() => {
    const initChat = async () => {
      try {
        if (sessionId) {
          // Only load history if session already exists, don't create it
          await loadHistory(50);
        }
        setIsLoading(false);
      } catch (err) {
        console.error('Failed to load chat history:', err);
        setIsLoading(false);
      }
    };

    initChat();
  }, [sessionId, loadHistory]);

  // Auto-scroll to bottom when new messages arrive
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({
      behavior: 'smooth',
      block: 'end'
    });
  };

  useEffect(() => {
    const timer = setTimeout(scrollToBottom, 100);
    return () => clearTimeout(timer);
  }, [messages, currentStream]);

  // Focus input when connected
  useEffect(() => {
    if (isConnected && !isLoading) {
      inputRef.current?.focus();
    }
  }, [isConnected, isLoading]);

  const handleSendMessage = async (content, metadata = {}) => {
    if (content.trim() || metadata.attachments?.length > 0) {
      try {
        // Connect on first message if not already connected
        if (!isConnected && !isReconnecting) {
          await connect();
        }

        await sendMessage(content, {
          ...metadata,
          projectId,
          timestamp: new Date().toISOString()
        }, true);
        inputRef.current?.focus();
      } catch (err) {
        console.error('Failed to send message:', err);
      }
    }
  };

  const handleTyping = () => {
    if (isConnected) {
      sendTypingIndicator();
    }
  };

  const handleReaction = (messageId, helpful, rating) => {
    if (isConnected) {
      sendReaction(messageId, helpful, rating);
    }
  };

  const handleClearChat = () => {
    clearMessages();
    inputRef.current?.focus();
  };

  const handleCloseAlert = () => {
    setShowAlert(false);
  };

  if (isLoading) {
    return (
      <LoadingContainer>
        <CircularProgress size={40} />
        <Box sx={{ textAlign: 'center', color: 'text.secondary' }}>
          Carregando conversa...
        </Box>
      </LoadingContainer>
    );
  }

  return (
    <ChatWrapper elevation={2}>
      <ChatHeader
        sessionId={sessionId}
        isConnected={isConnected}
        isReconnecting={isReconnecting}
        onClearChat={handleClearChat}
        onClose={onClose}
      />

      {error && showAlert && (
        <Alert
          severity="error"
          onClose={handleCloseAlert}
          sx={{ margin: 1 }}
        >
          {error}
        </Alert>
      )}

      <MessageList
        messages={messages}
        currentStream={currentStream}
        onReaction={handleReaction}
        isConnected={isConnected}
      />

      {typingUsers.length > 0 && (
        <TypingIndicator users={typingUsers} />
      )}

      <div ref={messagesEndRef} />

      <MessageInput
        ref={inputRef}
        onSendMessage={handleSendMessage}
        onTyping={handleTyping}
        disabled={!isConnected || isReconnecting}
        isReconnecting={isReconnecting}
      />
    </ChatWrapper>
  );
};

export default ChatContainer;