/**
 * MessageInput - Input component for chat messages
 * Supports text input, file attachments, and keyboard shortcuts
 */

import React, { useState, useRef, forwardRef, useCallback, useEffect } from 'react';
import {
  Box,
  TextField,
  IconButton,
  Paper,
  Tooltip,
  CircularProgress,
  Chip,
  Typography,
  Fade
} from '@mui/material';
import {
  Send,
  AttachFile,
  EmojiEmotions,
  Close
} from '@mui/icons-material';
import { styled } from '@mui/material/styles';

const InputContainer = styled(Paper)(({ theme }) => ({
  margin: theme.spacing(1),
  padding: theme.spacing(1),
  borderRadius: theme.spacing(2),
  border: `1px solid ${theme.palette.divider}`,
  display: 'flex',
  flexDirection: 'column',
  gap: theme.spacing(1),
  backgroundColor: theme.palette.background.paper,
  boxShadow: theme.shadows[2],
}));

const InputRow = styled(Box)(({ theme }) => ({
  display: 'flex',
  alignItems: 'flex-end',
  gap: theme.spacing(1),
}));

const StyledTextField = styled(TextField)(({ theme }) => ({
  flex: 1,
  '& .MuiOutlinedInput-root': {
    borderRadius: theme.spacing(2),
    backgroundColor: 'transparent',
    '& fieldset': {
      border: 'none',
    },
    '&:hover fieldset': {
      border: 'none',
    },
    '&.Mui-focused fieldset': {
      border: 'none',
    },
  },
  '& .MuiOutlinedInput-input': {
    padding: theme.spacing(1, 1.5),
    fontSize: '0.95rem',
    lineHeight: 1.5,
  },
}));

const AttachmentPreview = styled(Box)(({ theme }) => ({
  display: 'flex',
  flexWrap: 'wrap',
  gap: theme.spacing(1),
  padding: theme.spacing(0.5, 0),
}));

const FileChip = styled(Chip)(({ theme }) => ({
  maxWidth: 200,
  '& .MuiChip-label': {
    overflow: 'hidden',
    textOverflow: 'ellipsis',
    whiteSpace: 'nowrap',
  },
}));

const StatusIndicator = styled(Box)(({ theme }) => ({
  display: 'flex',
  alignItems: 'center',
  gap: theme.spacing(0.5),
  paddingLeft: theme.spacing(1),
  color: theme.palette.text.secondary,
  fontSize: '0.75rem',
}));

const MessageInput = forwardRef(({
  onSendMessage,
  onTyping,
  disabled = false,
  isReconnecting = false,
  placeholder = "Digite sua mensagem...",
  maxLength = 2000
}, ref) => {
  const [message, setMessage] = useState('');
  const [attachments, setAttachments] = useState([]);
  const [isSending, setIsSending] = useState(false);
  const [dragOver, setDragOver] = useState(false);

  const typingTimeoutRef = useRef(null);
  const fileInputRef = useRef(null);
  const textFieldRef = useRef(null);

  // Expose focus method via ref
  React.useImperativeHandle(ref, () => ({
    focus: () => {
      textFieldRef.current?.focus();
    },
    clear: () => {
      setMessage('');
      setAttachments([]);
    }
  }));

  const handleInputChange = (e) => {
    const value = e.target.value;

    if (value.length <= maxLength) {
      setMessage(value);

      // Trigger typing indicator
      if (onTyping && !disabled) {
        if (typingTimeoutRef.current) {
          clearTimeout(typingTimeoutRef.current);
        }

        onTyping();

        typingTimeoutRef.current = setTimeout(() => {
          // Stop typing indicator after 2 seconds of inactivity
        }, 2000);
      }
    }
  };

  const handleSend = useCallback(async () => {
    if ((message.trim() || attachments.length > 0) && !disabled && !isSending) {
      setIsSending(true);

      try {
        await onSendMessage(message.trim(), {
          attachments: attachments.map(file => ({
            name: file.name,
            size: file.size,
            type: file.type,
            data: file.data || null
          }))
        });

        setMessage('');
        setAttachments([]);
        textFieldRef.current?.focus();
      } catch (error) {
        console.error('Failed to send message:', error);
      } finally {
        setIsSending(false);
      }
    }
  }, [message, attachments, disabled, isSending, onSendMessage]);

  const handleKeyPress = (e) => {
    if (e.key === 'Enter') {
      if (e.shiftKey) {
        // Allow new line
        return;
      } else {
        e.preventDefault();
        handleSend();
      }
    }
  };

  const handleFileSelect = (e) => {
    const files = Array.from(e.target.files);
    processFiles(files);
    e.target.value = ''; // Reset input
  };

  const processFiles = (files) => {
    const validFiles = files.filter(file => {
      // Basic file validation
      const maxSize = 10 * 1024 * 1024; // 10MB
      const allowedTypes = [
        'image/', 'text/', 'application/pdf',
        'application/msword', 'application/vnd.openxmlformats-officedocument'
      ];

      if (file.size > maxSize) {
        console.warn(`File ${file.name} is too large (max 10MB)`);
        return false;
      }

      if (!allowedTypes.some(type => file.type.startsWith(type))) {
        console.warn(`File type ${file.type} not supported`);
        return false;
      }

      return true;
    });

    setAttachments(prev => [...prev, ...validFiles].slice(0, 5)); // Max 5 files
  };

  const removeAttachment = (index) => {
    setAttachments(prev => prev.filter((_, i) => i !== index));
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    setDragOver(true);
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    setDragOver(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setDragOver(false);

    const files = Array.from(e.dataTransfer.files);
    processFiles(files);
  };

  const getStatusText = () => {
    if (isReconnecting) return 'Reconectando...';
    if (!disabled && message.length > 0) {
      return `${message.length}/${maxLength}`;
    }
    if (!disabled) return 'Digite sua mensagem...';
    return 'Desconectado';
  };

  const canSend = !disabled && !isSending && (message.trim() || attachments.length > 0);

  return (
    <InputContainer
      elevation={0}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
      sx={{
        borderColor: dragOver ? 'primary.main' : 'divider',
        backgroundColor: dragOver ? 'action.hover' : 'background.paper',
      }}
    >
      {/* File input */}
      <input
        ref={fileInputRef}
        type="file"
        multiple
        hidden
        onChange={handleFileSelect}
        accept="image/*,.pdf,.doc,.docx,.txt,.md"
      />

      {/* Attachment preview */}
      {attachments.length > 0 && (
        <Fade in>
          <AttachmentPreview>
            {attachments.map((file, index) => (
              <FileChip
                key={index}
                label={file.name}
                variant="outlined"
                size="small"
                onDelete={() => removeAttachment(index)}
                deleteIcon={<Close />}
              />
            ))}
          </AttachmentPreview>
        </Fade>
      )}

      {/* Input row */}
      <InputRow>
        <Tooltip title="Anexar arquivo">
          <IconButton
            size="small"
            onClick={() => fileInputRef.current?.click()}
            disabled={disabled || attachments.length >= 5}
            aria-label="Anexar arquivo"
          >
            <AttachFile />
          </IconButton>
        </Tooltip>

        <StyledTextField
          ref={textFieldRef}
          multiline
          maxRows={6}
          placeholder={placeholder}
          value={message}
          onChange={handleInputChange}
          onKeyPress={handleKeyPress}
          disabled={disabled}
          inputProps={{
            'aria-label': 'Campo de mensagem',
            maxLength
          }}
        />

        <Tooltip title="Enviar mensagem">
          <span>
            <IconButton
              size="small"
              onClick={handleSend}
              disabled={!canSend}
              color="primary"
              aria-label="Enviar mensagem"
              sx={{
                backgroundColor: canSend ? 'primary.main' : 'action.disabled',
                color: canSend ? 'primary.contrastText' : 'action.disabled',
                '&:hover': {
                  backgroundColor: canSend ? 'primary.dark' : 'action.disabled',
                },
              }}
            >
              {isSending ? (
                <CircularProgress size={18} color="inherit" />
              ) : (
                <Send />
              )}
            </IconButton>
          </span>
        </Tooltip>
      </InputRow>

      {/* Status indicator */}
      <StatusIndicator>
        <Typography variant="caption" color="inherit">
          {getStatusText()}
        </Typography>

        {!disabled && !isReconnecting && (
          <Typography variant="caption" color="inherit">
            • Enter para enviar, Shift+Enter para nova linha
          </Typography>
        )}
      </StatusIndicator>

      {/* Drag overlay */}
      {dragOver && (
        <Box
          sx={{
            position: 'absolute',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            backgroundColor: 'rgba(25, 118, 210, 0.1)',
            border: '2px dashed',
            borderColor: 'primary.main',
            borderRadius: 2,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 1,
          }}
        >
          <Typography variant="h6" color="primary">
            Solte os arquivos aqui
          </Typography>
        </Box>
      )}
    </InputContainer>
  );
});

MessageInput.displayName = 'MessageInput';

export default MessageInput;