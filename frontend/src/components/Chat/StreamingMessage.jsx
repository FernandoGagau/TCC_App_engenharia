/**
 * StreamingMessage - Component for displaying streaming message responses
 * Shows real-time text as it's being generated
 */

import React, { useEffect, useState } from 'react';
import {
  Box,
  Avatar,
  Typography,
  Paper,
  useTheme
} from '@mui/material';
import {
  SmartToy
} from '@mui/icons-material';
import { styled, keyframes } from '@mui/material/styles';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus, vs } from 'react-syntax-highlighter/dist/esm/styles/prism';

const typewriter = keyframes`
  0% { opacity: 1; }
  50% { opacity: 0; }
  100% { opacity: 1; }
`;

const StreamingContainer = styled(Box)(({ theme }) => ({
  display: 'flex',
  gap: theme.spacing(1.5),
  alignItems: 'flex-start',
  maxWidth: '100%',
}));

const StreamingBubble = styled(Paper)(({ theme }) => ({
  padding: theme.spacing(1.5, 2),
  maxWidth: '75%',
  position: 'relative',
  backgroundColor: theme.palette.background.paper,
  color: theme.palette.text.primary,
  borderRadius: theme.spacing(2),
  borderTopLeftRadius: 4,
  boxShadow: theme.shadows[1],
  border: `2px solid ${theme.palette.primary.main}`,
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
  },
}));

const TypingIndicator = styled('span')(({ theme }) => ({
  display: 'inline-block',
  width: '3px',
  height: '1em',
  backgroundColor: theme.palette.primary.main,
  animation: `${typewriter} 1s infinite`,
  marginLeft: '2px',
  verticalAlign: 'baseline',
}));

const StreamingIndicator = styled(Box)(({ theme }) => ({
  display: 'flex',
  alignItems: 'center',
  gap: theme.spacing(1),
  marginTop: theme.spacing(1),
  padding: theme.spacing(0.5, 1),
  backgroundColor: theme.palette.action.hover,
  borderRadius: theme.spacing(1),
  fontSize: '0.75rem',
  color: theme.palette.text.secondary,
}));

const StreamingMessage = ({ message, streamContent, isComplete }) => {
  const theme = useTheme();
  const [displayContent, setDisplayContent] = useState('');

  // Update displayed content as stream progresses
  useEffect(() => {
    if (streamContent) {
      setDisplayContent(streamContent);
    }
  }, [streamContent]);

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

  const renderStreamingContent = () => {
    const content = displayContent || message.content || '';

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
        {!isComplete && <TypingIndicator />}
      </div>
    );
  };

  return (
    <StreamingContainer>
      <Box sx={{ position: 'sticky', top: theme.spacing(1) }}>
        <Avatar
          sx={{
            width: 36,
            height: 36,
            backgroundColor: theme.palette.secondary.main,
          }}
        >
          <SmartToy />
        </Avatar>
      </Box>

      <Box flex={1} minWidth={0}>
        <StreamingBubble elevation={2}>
          {renderStreamingContent()}

          {!isComplete && (
            <StreamingIndicator>
              <Box
                sx={{
                  display: 'flex',
                  gap: 0.5,
                  alignItems: 'center',
                }}
              >
                <Box
                  sx={{
                    width: 4,
                    height: 4,
                    borderRadius: '50%',
                    backgroundColor: 'primary.main',
                    animation: `${typewriter} 1.5s infinite`,
                  }}
                />
                <Box
                  sx={{
                    width: 4,
                    height: 4,
                    borderRadius: '50%',
                    backgroundColor: 'primary.main',
                    animation: `${typewriter} 1.5s infinite 0.2s`,
                  }}
                />
                <Box
                  sx={{
                    width: 4,
                    height: 4,
                    borderRadius: '50%',
                    backgroundColor: 'primary.main',
                    animation: `${typewriter} 1.5s infinite 0.4s`,
                  }}
                />
              </Box>
              <Typography variant="caption">
                Gerando resposta...
              </Typography>
            </StreamingIndicator>
          )}
        </StreamingBubble>
      </Box>
    </StreamingContainer>
  );
};

export default StreamingMessage;