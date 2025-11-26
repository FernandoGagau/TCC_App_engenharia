/**
 * Message - Individual message component with markdown support
 * Handles user and assistant messages with reactions and attachments
 */

import React, { useState } from 'react';
import {
  Box,
  Avatar,
  Typography,
  Paper,
  IconButton,
  Tooltip,
  Chip,
  Fade,
  useTheme
} from '@mui/material';
import {
  Person,
  SmartToy,
  ContentCopy,
  ThumbUp,
  ThumbDown,
  Star,
  Check
} from '@mui/icons-material';
import { styled } from '@mui/material/styles';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus, vs } from 'react-syntax-highlighter/dist/esm/styles/prism';
import { format } from 'date-fns';
import { ptBR } from 'date-fns/locale';

const MessageContainer = styled(Box)(({ theme, role }) => ({
  display: 'flex',
  gap: theme.spacing(1.5),
  alignItems: 'flex-start',
  flexDirection: role === 'user' ? 'row-reverse' : 'row',
  maxWidth: '100%',
}));

const MessageBubble = styled(Paper)(({ theme, role }) => ({
  padding: theme.spacing(1.5, 2),
  maxWidth: '75%',
  position: 'relative',
  backgroundColor: role === 'user'
    ? theme.palette.primary.main
    : theme.palette.background.paper,
  color: role === 'user'
    ? theme.palette.primary.contrastText
    : theme.palette.text.primary,
  borderRadius: theme.spacing(2),
  borderTopLeftRadius: role === 'assistant' ? 4 : theme.spacing(2),
  borderTopRightRadius: role === 'user' ? 4 : theme.spacing(2),
  boxShadow: theme.shadows[1],
  [theme.breakpoints.down('sm')]: {
    maxWidth: '85%',
    padding: theme.spacing(1.5),
  },
  '& .markdown-content': {
    '& p': {
      margin: 0,
      marginBottom: theme.spacing(1),
      '&:last-child': {
        marginBottom: 0,
      },
    },
    '& ul, & ol': {
      marginLeft: theme.spacing(2),
      marginBottom: theme.spacing(1),
    },
    '& li': {
      marginBottom: theme.spacing(0.5),
    },
    '& blockquote': {
      borderLeft: `4px solid ${theme.palette.divider}`,
      paddingLeft: theme.spacing(2),
      margin: theme.spacing(1, 0),
      fontStyle: 'italic',
    },
    '& table': {
      borderCollapse: 'collapse',
      width: '100%',
      marginBottom: theme.spacing(1),
    },
    '& th, & td': {
      border: `1px solid ${theme.palette.divider}`,
      padding: theme.spacing(0.5, 1),
      textAlign: 'left',
    },
    '& th': {
      backgroundColor: theme.palette.action.hover,
      fontWeight: 600,
    },
  },
}));

const MessageActions = styled(Box)(({ theme }) => ({
  display: 'flex',
  gap: theme.spacing(0.5),
  marginTop: theme.spacing(1),
  opacity: 0,
  transition: 'opacity 0.2s ease-in-out',
  '.message-container:hover &': {
    opacity: 1,
  },
}));

const AvatarContainer = styled(Box)(({ theme }) => ({
  position: 'sticky',
  top: theme.spacing(1),
}));

const Message = ({ message, isLast, onReaction }) => {
  const theme = useTheme();
  const [copied, setCopied] = useState(false);
  const { id, role, content, timestamp, metadata, reactions } = message;

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(content);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('Failed to copy text:', err);
    }
  };

  const handleReaction = (type, value) => {
    if (type === 'helpful') {
      onReaction?.(id, value, null);
    } else if (type === 'rating') {
      onReaction?.(id, null, value);
    }
  };

  const renderCodeBlock = ({ node, inline, className, children, ...props }) => {
    const match = /language-(\w+)/.exec(className || '');
    const language = match ? match[1] : '';

    if (!inline && language) {
      return (
        <Box sx={{ position: 'relative', mt: 1, mb: 1 }}>
          <SyntaxHighlighter
            style={theme.palette.mode === 'dark' ? vscDarkPlus : vs}
            language={language}
            PreTag="div"
            customStyle={{
              borderRadius: theme.shape.borderRadius,
              fontSize: '0.875rem',
            }}
            {...props}
          >
            {String(children).replace(/\n$/, '')}
          </SyntaxHighlighter>
          <IconButton
            size="small"
            onClick={() => navigator.clipboard.writeText(String(children))}
            sx={{
              position: 'absolute',
              top: 8,
              right: 8,
              backgroundColor: 'rgba(0, 0, 0, 0.6)',
              color: 'white',
              '&:hover': {
                backgroundColor: 'rgba(0, 0, 0, 0.8)',
              },
            }}
          >
            <ContentCopy fontSize="small" />
          </IconButton>
        </Box>
      );
    }

    return (
      <code
        className={className}
        style={{
          backgroundColor: theme.palette.action.hover,
          padding: '2px 4px',
          borderRadius: 4,
          fontSize: '0.875em',
        }}
        {...props}
      >
        {children}
      </code>
    );
  };

  const renderContent = () => {
    if (role === 'user') {
      return (
        <Typography
          variant="body1"
          sx={{ whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}
        >
          {content}
        </Typography>
      );
    }

    return (
      <div className="markdown-content">
        <ReactMarkdown
          remarkPlugins={[remarkGfm]}
          components={{
            code: renderCodeBlock,
            a: ({ children, ...props }) => (
              <a
                {...props}
                target="_blank"
                rel="noopener noreferrer"
                style={{
                  color: theme.palette.primary.main,
                  textDecoration: 'underline',
                }}
              >
                {children}
              </a>
            ),
          }}
        >
          {content}
        </ReactMarkdown>
      </div>
    );
  };

  return (
    <MessageContainer role={role} className="message-container">
      <AvatarContainer>
        <Avatar
          sx={{
            width: 36,
            height: 36,
            backgroundColor: role === 'user'
              ? theme.palette.primary.main
              : theme.palette.secondary.main,
          }}
        >
          {role === 'user' ? <Person /> : <SmartToy />}
        </Avatar>
      </AvatarContainer>

      <Box flex={1} minWidth={0}>
        <MessageBubble role={role} elevation={1}>
          {renderContent()}

          {metadata?.attachments?.length > 0 && (
            <Box mt={1.5} display="flex" gap={1} flexWrap="wrap">
              {metadata.attachments.map((attachment, i) => (
                <Chip
                  key={i}
                  label={attachment.name}
                  size="small"
                  variant="outlined"
                  sx={{
                    backgroundColor: theme.palette.action.hover,
                    borderColor: theme.palette.divider,
                  }}
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
              fontSize: '0.75rem',
            }}
          >
            {format(new Date(timestamp), 'HH:mm', { locale: ptBR })}
            {metadata?.processing_time && (
              <span> • {metadata.processing_time.toFixed(2)}s</span>
            )}
          </Typography>
        </MessageBubble>

        {role === 'assistant' && isLast && (
          <Fade in timeout={200}>
            <MessageActions>
              <Tooltip title={copied ? 'Copiado!' : 'Copiar mensagem'}>
                <IconButton size="small" onClick={handleCopy}>
                  {copied ? <Check color="success" /> : <ContentCopy />}
                </IconButton>
              </Tooltip>

              <Tooltip title="Resposta útil">
                <IconButton
                  size="small"
                  onClick={() => handleReaction('helpful', !reactions?.helpful)}
                  color={reactions?.helpful ? 'success' : 'default'}
                >
                  <ThumbUp />
                </IconButton>
              </Tooltip>

              <Tooltip title="Resposta não útil">
                <IconButton
                  size="small"
                  onClick={() => handleReaction('helpful', false)}
                  color={reactions?.helpful === false ? 'error' : 'default'}
                >
                  <ThumbDown />
                </IconButton>
              </Tooltip>

              <Tooltip title="Avaliar resposta">
                <IconButton
                  size="small"
                  onClick={() => handleReaction('rating', 5)}
                  color={reactions?.rating ? 'primary' : 'default'}
                >
                  <Star />
                </IconButton>
              </Tooltip>
            </MessageActions>
          </Fade>
        )}
      </Box>
    </MessageContainer>
  );
};

export default Message;