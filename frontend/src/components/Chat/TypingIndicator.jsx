/**
 * TypingIndicator - Shows when other users are typing
 * Animated indicator with bouncing dots
 */

import React from 'react';
import { Box, Typography, Avatar } from '@mui/material';
import { SmartToy } from '@mui/icons-material';
import { styled, keyframes } from '@mui/material/styles';

const bounce = keyframes`
  0%, 60%, 100% {
    transform: translateY(0);
  }
  30% {
    transform: translateY(-8px);
  }
`;

const fadeIn = keyframes`
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
`;

const TypingContainer = styled(Box)(({ theme }) => ({
  display: 'flex',
  alignItems: 'flex-start',
  gap: theme.spacing(1.5),
  padding: theme.spacing(1, 2),
  animation: `${fadeIn} 0.3s ease-out`,
  maxWidth: '100%',
}));

const TypingBubble = styled(Box)(({ theme }) => ({
  backgroundColor: theme.palette.background.paper,
  border: `1px solid ${theme.palette.divider}`,
  borderRadius: theme.spacing(2),
  borderTopLeftRadius: 4,
  padding: theme.spacing(1, 1.5),
  display: 'flex',
  alignItems: 'center',
  gap: theme.spacing(1),
  boxShadow: theme.shadows[1],
  minHeight: 36,
}));

const TypingDot = styled('span')(({ theme, delay = 0 }) => ({
  display: 'inline-block',
  width: '6px',
  height: '6px',
  borderRadius: '50%',
  backgroundColor: theme.palette.text.secondary,
  animation: `${bounce} 1.4s infinite ease-in-out`,
  animationDelay: `${delay}s`,
}));

const DotsContainer = styled(Box)({
  display: 'flex',
  alignItems: 'center',
  gap: '3px',
  marginLeft: '8px',
});

const TypingIndicator = ({ users = [] }) => {
  if (!users || users.length === 0) {
    return null;
  }

  const getTypingText = () => {
    if (users.length === 1) {
      return users[0] === 'assistant' ? 'Assistente está digitando' : `${users[0]} está digitando`;
    }

    if (users.length === 2) {
      return `${users[0]} e ${users[1]} estão digitando`;
    }

    return `${users[0]} e mais ${users.length - 1} pessoas estão digitando`;
  };

  return (
    <TypingContainer>
      <Avatar
        sx={{
          width: 32,
          height: 32,
          backgroundColor: 'secondary.main',
        }}
      >
        <SmartToy sx={{ fontSize: 18 }} />
      </Avatar>

      <TypingBubble>
        <Typography
          variant="body2"
          color="text.secondary"
          sx={{ fontSize: '0.875rem' }}
        >
          {getTypingText()}
        </Typography>

        <DotsContainer>
          <TypingDot delay={0} />
          <TypingDot delay={0.2} />
          <TypingDot delay={0.4} />
        </DotsContainer>
      </TypingBubble>
    </TypingContainer>
  );
};

export default TypingIndicator;