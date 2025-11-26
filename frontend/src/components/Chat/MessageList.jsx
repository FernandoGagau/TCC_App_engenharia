/**
 * MessageList - Displays list of chat messages with animations
 * Handles both regular messages and streaming responses
 */

import React from 'react';
import { Box, Typography } from '@mui/material';
import { styled } from '@mui/material/styles';
import { AnimatePresence, motion } from 'framer-motion';
import Message from './Message';
import StreamingMessage from './StreamingMessage';

const MessageListContainer = styled(Box)(({ theme }) => ({
  flex: 1,
  overflowY: 'auto',
  padding: theme.spacing(2),
  display: 'flex',
  flexDirection: 'column',
  gap: theme.spacing(2),
  minHeight: 0,
  '&::-webkit-scrollbar': {
    width: '8px',
  },
  '&::-webkit-scrollbar-track': {
    background: theme.palette.background.default,
    borderRadius: '4px',
  },
  '&::-webkit-scrollbar-thumb': {
    background: theme.palette.divider,
    borderRadius: '4px',
    '&:hover': {
      background: theme.palette.action.hover,
    },
  },
  [theme.breakpoints.down('sm')]: {
    padding: theme.spacing(1),
    gap: theme.spacing(1),
  },
}));

const EmptyState = styled(Box)(({ theme }) => ({
  display: 'flex',
  flexDirection: 'column',
  alignItems: 'center',
  justifyContent: 'center',
  flex: 1,
  textAlign: 'center',
  padding: theme.spacing(4),
  color: theme.palette.text.secondary,
}));

const MessageWrapper = styled(motion.div)({
  width: '100%',
});

const MessageList = ({ messages = [], currentStream, onReaction, isConnected }) => {
  // If no messages and connected, show welcome message
  if (messages.length === 0 && isConnected) {
    return (
      <MessageListContainer>
        <EmptyState>
          <Typography variant="h6" gutterBottom>
            👋 Olá! Como posso ajudar você hoje?
          </Typography>
          <Typography variant="body2" sx={{ maxWidth: 400 }}>
            Sou um assistente especializado em análise de projetos de construção.
            Faça uma pergunta ou envie documentos para começarmos!
          </Typography>
        </EmptyState>
      </MessageListContainer>
    );
  }

  // If no messages and disconnected, show connection message
  if (messages.length === 0 && !isConnected) {
    return (
      <MessageListContainer>
        <EmptyState>
          <Typography variant="h6" gutterBottom>
            🔌 Conectando...
          </Typography>
          <Typography variant="body2">
            Aguarde enquanto estabelecemos a conexão com o servidor.
          </Typography>
        </EmptyState>
      </MessageListContainer>
    );
  }

  return (
    <MessageListContainer>
      <AnimatePresence initial={false}>
        {messages.map((message, index) => {
          const isStreaming = currentStream && message.id === currentStream.messageId;
          const isLast = index === messages.length - 1;

          return (
            <MessageWrapper
              key={message.id}
              initial={{ opacity: 0, y: 20, scale: 0.95 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: -20, scale: 0.95 }}
              transition={{
                duration: 0.3,
                ease: 'easeOut',
              }}
            >
              {isStreaming ? (
                <StreamingMessage
                  message={message}
                  streamContent={currentStream.content}
                  isComplete={currentStream.isComplete}
                />
              ) : (
                <Message
                  message={message}
                  isLast={isLast}
                  onReaction={onReaction}
                />
              )}
            </MessageWrapper>
          );
        })}
      </AnimatePresence>
    </MessageListContainer>
  );
};

export default MessageList;