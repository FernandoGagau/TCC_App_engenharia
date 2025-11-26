# Prompt: Adicionar Componente de UI de Chat no Frontend

Start Here
- Leia AGENTS.md e agents/README.md para padrões do repositório e checklists.
- Consulte docs/README.md para visão geral e guias (backend, frontend, database, auth).
- Siga os guias: agents/frontend-development.md, docs/frontend.md, docs/components.md.

Objetivo
- Criar componente de chat completo e responsivo para o frontend React.
- Integrar com WebSocket service para comunicação em tempo real.
- Implementar UX moderna com streaming de respostas, indicadores de digitação e reações.

Escopo
- Chat Component: interface completa de conversação.
- Message List: exibição de mensagens com auto-scroll.
- Input Area: campo de entrada com suporte a markdown.
- Streaming UI: visualização de respostas incrementais.
- Mobile Responsive: design adaptativo para todos os dispositivos.
- Accessibility: suporte completo a leitores de tela.

Requisitos de Configuração
- Dependências React:
  ```json
  {
    "react-markdown": "^9.0.1",
    "remark-gfm": "^4.0.0",
    "react-syntax-highlighter": "^15.5.0",
    "framer-motion": "^11.0.0",
    "@mui/material": "^5.15.0",
    "@mui/icons-material": "^5.15.0",
    "date-fns": "^3.0.0"
  }
  ```
- WebSocket service já implementado
- Material UI theme configurado

Arquitetura de Componentes
```
ChatInterface/
├── ChatContainer.jsx       # Container principal
├── ChatHeader.jsx          # Header com info da sessão
├── MessageList.jsx         # Lista de mensagens
├── Message.jsx            # Componente de mensagem individual
├── MessageInput.jsx       # Input com toolbar
├── TypingIndicator.jsx   # Indicador de digitação
├── StreamingMessage.jsx  # Mensagem em streaming
├── MessageReactions.jsx  # Sistema de reações
└── styles/
    └── ChatStyles.js      # Styled components
```

Componente Principal - ChatContainer
```jsx
// frontend/src/components/Chat/ChatContainer.jsx
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
  [theme.breakpoints.down('sm')]: {
    height: '100%',
    borderRadius: 0,
  },
}));

const ChatContainer = ({ sessionId, projectId }) => {
  const [isLoading, setIsLoading] = useState(true);

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
    loadHistory,
    clearMessages
  } = useWebSocket(sessionId, {
    autoConnect: true,
    baseUrl: process.env.REACT_APP_WS_URL
  });

  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  // Load message history on mount
  useEffect(() => {
    const initChat = async () => {
      try {
        await loadHistory(50);
        setIsLoading(false);
      } catch (err) {
        console.error('Failed to load history:', err);
        setIsLoading(false);
      }
    };

    if (sessionId) {
      initChat();
    }
  }, [sessionId, loadHistory]);

  // Auto-scroll to bottom
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSendMessage = (content, attachments = []) => {
    if (content.trim() || attachments.length > 0) {
      sendMessage(content, { attachments, projectId }, true);
      inputRef.current?.focus();
    }
  };

  const handleTyping = () => {
    sendTypingIndicator();
  };

  const handleReaction = (messageId, helpful, rating) => {
    sendReaction(messageId, helpful, rating);
  };

  if (isLoading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" height="100vh">
        <CircularProgress />
      </Box>
    );
  }

  return (
    <ChatWrapper elevation={3}>
      <ChatHeader
        sessionId={sessionId}
        isConnected={isConnected}
        isReconnecting={isReconnecting}
        onClearChat={clearMessages}
      />

      {error && (
        <Alert severity="error" onClose={() => {}}>
          {error}
        </Alert>
      )}

      <MessageList
        messages={messages}
        currentStream={currentStream}
        onReaction={handleReaction}
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
      />
    </ChatWrapper>
  );
};

export default ChatContainer;
```

Lista de Mensagens
```jsx
// frontend/src/components/Chat/MessageList.jsx
import React from 'react';
import { Box, List } from '@mui/material';
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
  gap: theme.spacing(1),
  '&::-webkit-scrollbar': {
    width: '8px',
  },
  '&::-webkit-scrollbar-track': {
    background: theme.palette.background.default,
  },
  '&::-webkit-scrollbar-thumb': {
    background: theme.palette.divider,
    borderRadius: '4px',
  },
}));

const MessageList = ({ messages, currentStream, onReaction }) => {
  return (
    <MessageListContainer>
      <AnimatePresence initial={false}>
        {messages.map((message, index) => {
          const isStreaming = message.id === currentStream;

          return (
            <motion.div
              key={message.id}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              transition={{ duration: 0.3 }}
            >
              {isStreaming ? (
                <StreamingMessage message={message} />
              ) : (
                <Message
                  message={message}
                  isLast={index === messages.length - 1}
                  onReaction={onReaction}
                />
              )}
            </motion.div>
          );
        })}
      </AnimatePresence>
    </MessageListContainer>
  );
};

export default MessageList;
```

Componente de Mensagem
```jsx
// frontend/src/components/Chat/Message.jsx
import React, { useState } from 'react';
import {
  Box,
  Avatar,
  Typography,
  Paper,
  IconButton,
  Tooltip,
  Chip
} from '@mui/material';
import {
  Person,
  SmartToy,
  ContentCopy,
  ThumbUp,
  ThumbDown,
  Star
} from '@mui/icons-material';
import { styled } from '@mui/material/styles';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism';
import { format } from 'date-fns';
import { ptBR } from 'date-fns/locale';

const MessageContainer = styled(Box)(({ theme, role }) => ({
  display: 'flex',
  gap: theme.spacing(1.5),
  alignItems: 'flex-start',
  flexDirection: role === 'user' ? 'row-reverse' : 'row',
}));

const MessageBubble = styled(Paper)(({ theme, role }) => ({
  padding: theme.spacing(1.5),
  maxWidth: '70%',
  backgroundColor: role === 'user'
    ? theme.palette.primary.main
    : theme.palette.background.paper,
  color: role === 'user'
    ? theme.palette.primary.contrastText
    : theme.palette.text.primary,
  borderRadius: theme.spacing(2),
  borderTopLeftRadius: role === 'assistant' ? 0 : theme.spacing(2),
  borderTopRightRadius: role === 'user' ? 0 : theme.spacing(2),
  [theme.breakpoints.down('sm')]: {
    maxWidth: '85%',
  },
}));

const MessageActions = styled(Box)(({ theme }) => ({
  display: 'flex',
  gap: theme.spacing(0.5),
  marginTop: theme.spacing(1),
  opacity: 0.7,
  '&:hover': {
    opacity: 1,
  },
}));

const Message = ({ message, isLast, onReaction }) => {
  const [copied, setCopied] = useState(false);
  const { id, role, content, timestamp, metadata, reactions } = message;

  const handleCopy = async () => {
    await navigator.clipboard.writeText(content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleReaction = (type) => {
    if (type === 'helpful') {
      onReaction(id, !reactions?.helpful, null);
    } else if (type === 'rating') {
      // Show rating dialog
      onReaction(id, null, 5);
    }
  };

  const renderContent = () => {
    if (role === 'user') {
      return (
        <Typography variant="body1" sx={{ whiteSpace: 'pre-wrap' }}>
          {content}
        </Typography>
      );
    }

    return (
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          code({ node, inline, className, children, ...props }) {
            const match = /language-(\w+)/.exec(className || '');
            return !inline && match ? (
              <Box sx={{ position: 'relative', mt: 1, mb: 1 }}>
                <SyntaxHighlighter
                  style={vscDarkPlus}
                  language={match[1]}
                  PreTag="div"
                  {...props}
                >
                  {String(children).replace(/\n$/, '')}
                </SyntaxHighlighter>
                <IconButton
                  size="small"
                  onClick={() => navigator.clipboard.writeText(children)}
                  sx={{
                    position: 'absolute',
                    top: 8,
                    right: 8,
                    backgroundColor: 'rgba(0, 0, 0, 0.5)',
                  }}
                >
                  <ContentCopy fontSize="small" />
                </IconButton>
              </Box>
            ) : (
              <code className={className} {...props}>
                {children}
              </code>
            );
          },
        }}
      >
        {content}
      </ReactMarkdown>
    );
  };

  return (
    <MessageContainer role={role}>
      <Avatar sx={{ width: 32, height: 32 }}>
        {role === 'user' ? <Person /> : <SmartToy />}
      </Avatar>

      <Box flex={1}>
        <MessageBubble role={role} elevation={1}>
          {renderContent()}

          {metadata?.attachments?.length > 0 && (
            <Box mt={1} display="flex" gap={1} flexWrap="wrap">
              {metadata.attachments.map((attachment, i) => (
                <Chip
                  key={i}
                  label={attachment.name}
                  size="small"
                  variant="outlined"
                />
              ))}
            </Box>
          )}

          <Typography
            variant="caption"
            sx={{
              display: 'block',
              mt: 1,
              opacity: 0.7,
            }}
          >
            {format(new Date(timestamp), 'HH:mm', { locale: ptBR })}
            {metadata?.processing_time && (
              <span> • {metadata.processing_time.toFixed(2)}s</span>
            )}
          </Typography>
        </MessageBubble>

        {role === 'assistant' && isLast && (
          <MessageActions>
            <Tooltip title={copied ? 'Copiado!' : 'Copiar'}>
              <IconButton size="small" onClick={handleCopy}>
                <ContentCopy fontSize="small" />
              </IconButton>
            </Tooltip>

            <Tooltip title="Útil">
              <IconButton
                size="small"
                onClick={() => handleReaction('helpful')}
                color={reactions?.helpful ? 'primary' : 'default'}
              >
                <ThumbUp fontSize="small" />
              </IconButton>
            </Tooltip>

            <Tooltip title="Não útil">
              <IconButton
                size="small"
                onClick={() => handleReaction('helpful')}
                color={reactions?.helpful === false ? 'error' : 'default'}
              >
                <ThumbDown fontSize="small" />
              </IconButton>
            </Tooltip>

            <Tooltip title="Avaliar">
              <IconButton
                size="small"
                onClick={() => handleReaction('rating')}
              >
                <Star fontSize="small" />
              </IconButton>
            </Tooltip>
          </MessageActions>
        )}
      </Box>
    </MessageContainer>
  );
};

export default Message;
```

Input de Mensagem
```jsx
// frontend/src/components/Chat/MessageInput.jsx
import React, { useState, useRef, forwardRef } from 'react';
import {
  Box,
  TextField,
  IconButton,
  Paper,
  Tooltip,
  CircularProgress
} from '@mui/material';
import {
  Send,
  AttachFile,
  Mic,
  Stop,
  EmojiEmotions
} from '@mui/icons-material';
import { styled } from '@mui/material/styles';

const InputContainer = styled(Paper)(({ theme }) => ({
  padding: theme.spacing(1),
  borderRadius: 0,
  borderTop: `1px solid ${theme.palette.divider}`,
  display: 'flex',
  alignItems: 'flex-end',
  gap: theme.spacing(1),
}));

const StyledTextField = styled(TextField)(({ theme }) => ({
  '& .MuiOutlinedInput-root': {
    borderRadius: theme.spacing(3),
    backgroundColor: theme.palette.background.default,
  },
}));

const MessageInput = forwardRef(({ onSendMessage, onTyping, disabled }, ref) => {
  const [message, setMessage] = useState('');
  const [isRecording, setIsRecording] = useState(false);
  const [isSending, setIsSending] = useState(false);
  const typingTimeoutRef = useRef(null);
  const fileInputRef = useRef(null);

  const handleInputChange = (e) => {
    setMessage(e.target.value);

    // Typing indicator
    if (typingTimeoutRef.current) {
      clearTimeout(typingTimeoutRef.current);
    }

    onTyping();

    typingTimeoutRef.current = setTimeout(() => {
      // Stop typing indicator after 2 seconds
    }, 2000);
  };

  const handleSend = async () => {
    if (message.trim() && !disabled && !isSending) {
      setIsSending(true);
      await onSendMessage(message);
      setMessage('');
      setIsSending(false);
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleFileSelect = (e) => {
    const files = Array.from(e.target.files);
    // Process files
    console.log('Files selected:', files);
  };

  const toggleRecording = () => {
    setIsRecording(!isRecording);
    // Implement voice recording
  };

  return (
    <InputContainer elevation={0}>
      <input
        ref={fileInputRef}
        type="file"
        multiple
        hidden
        onChange={handleFileSelect}
      />

      <Tooltip title="Anexar arquivo">
        <IconButton
          size="small"
          onClick={() => fileInputRef.current?.click()}
          disabled={disabled}
        >
          <AttachFile />
        </IconButton>
      </Tooltip>

      <StyledTextField
        ref={ref}
        fullWidth
        multiline
        maxRows={4}
        placeholder="Digite sua mensagem..."
        value={message}
        onChange={handleInputChange}
        onKeyPress={handleKeyPress}
        disabled={disabled || isSending}
        size="small"
        InputProps={{
          endAdornment: (
            <Box display="flex" alignItems="center">
              <Tooltip title="Emojis">
                <IconButton size="small" disabled={disabled}>
                  <EmojiEmotions />
                </IconButton>
              </Tooltip>
            </Box>
          ),
        }}
      />

      <Tooltip title={isRecording ? 'Parar gravação' : 'Gravar áudio'}>
        <IconButton
          size="small"
          onClick={toggleRecording}
          disabled={disabled}
          color={isRecording ? 'error' : 'default'}
        >
          {isRecording ? <Stop /> : <Mic />}
        </IconButton>
      </Tooltip>

      <Tooltip title="Enviar">
        <IconButton
          size="small"
          onClick={handleSend}
          disabled={disabled || !message.trim() || isSending}
          color="primary"
        >
          {isSending ? (
            <CircularProgress size={20} />
          ) : (
            <Send />
          )}
        </IconButton>
      </Tooltip>
    </InputContainer>
  );
});

MessageInput.displayName = 'MessageInput';

export default MessageInput;
```

Indicador de Digitação
```jsx
// frontend/src/components/Chat/TypingIndicator.jsx
import React from 'react';
import { Box, Typography } from '@mui/material';
import { styled, keyframes } from '@mui/material/styles';

const bounce = keyframes`
  0%, 60%, 100% {
    transform: translateY(0);
  }
  30% {
    transform: translateY(-10px);
  }
`;

const TypingDot = styled('span')(({ theme, delay }) => ({
  display: 'inline-block',
  width: '8px',
  height: '8px',
  borderRadius: '50%',
  backgroundColor: theme.palette.text.secondary,
  margin: '0 2px',
  animation: `${bounce} 1.4s infinite`,
  animationDelay: `${delay}s`,
}));

const TypingContainer = styled(Box)(({ theme }) => ({
  padding: theme.spacing(1, 2),
  display: 'flex',
  alignItems: 'center',
  gap: theme.spacing(1),
}));

const TypingIndicator = ({ users = [] }) => {
  const displayText = users.length === 1
    ? `${users[0]} está digitando`
    : `${users.length} pessoas estão digitando`;

  return (
    <TypingContainer>
      <Typography variant="caption" color="text.secondary">
        {displayText}
      </Typography>
      <Box>
        <TypingDot delay={0} />
        <TypingDot delay={0.2} />
        <TypingDot delay={0.4} />
      </Box>
    </TypingContainer>
  );
};

export default TypingIndicator;
```

Temas e Estilos
```javascript
// frontend/src/components/Chat/styles/ChatTheme.js
import { createTheme } from '@mui/material/styles';

export const chatTheme = createTheme({
  palette: {
    mode: 'light',
    primary: {
      main: '#2563eb',
    },
    background: {
      default: '#f3f4f6',
      paper: '#ffffff',
    },
  },
  typography: {
    fontFamily: '"Inter", "Roboto", "Helvetica", "Arial", sans-serif',
  },
  shape: {
    borderRadius: 12,
  },
  components: {
    MuiPaper: {
      styleOverrides: {
        root: {
          backgroundImage: 'none',
        },
      },
    },
  },
});

export const darkChatTheme = createTheme({
  palette: {
    mode: 'dark',
    primary: {
      main: '#3b82f6',
    },
    background: {
      default: '#111827',
      paper: '#1f2937',
    },
  },
  // ... rest of dark theme
});
```

Acessibilidade
- Suporte a navegação por teclado (Tab, Enter, Escape)
- ARIA labels em todos os elementos interativos
- Anúncios de mudanças de estado para leitores de tela
- Contraste adequado de cores (WCAG AAA)
- Suporte a modo de alto contraste

Testes
```jsx
// frontend/src/components/Chat/__tests__/ChatContainer.test.jsx
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import ChatContainer from '../ChatContainer';

describe('ChatContainer', () => {
  test('renders chat interface', () => {
    render(<ChatContainer sessionId="test-session" />);
    expect(screen.getByPlaceholderText(/digite sua mensagem/i)).toBeInTheDocument();
  });

  test('sends message on enter key', async () => {
    const { getByPlaceholderText } = render(<ChatContainer sessionId="test-session" />);
    const input = getByPlaceholderText(/digite sua mensagem/i);

    fireEvent.change(input, { target: { value: 'Test message' } });
    fireEvent.keyPress(input, { key: 'Enter', code: 13 });

    await waitFor(() => {
      expect(input.value).toBe('');
    });
  });

  test('shows typing indicator', async () => {
    // Test typing indicator visibility
  });
});
```

Entregáveis do PR
- Componente ChatContainer completo
- Todos os subcomponentes (Message, Input, etc.)
- Hook useWebSocket integrado
- Estilos e temas (light/dark)
- Testes unitários e de integração
- Documentação de uso
- Exemplos de implementação
- Suporte a acessibilidade

Checklists úteis
- Revisar agents/frontend-development.md para padrões React
- Seguir docs/components.md para estrutura
- Validar com agents/security-check.md
- Testar responsividade em múltiplos dispositivos

Notas
- Considerar lazy loading para histórico de mensagens
- Implementar virtual scrolling para grandes conversas
- Adicionar suporte a rich text editor (opcional)
- Preparar para internacionalização (i18n)
- Otimizar re-renders com React.memo e useMemo