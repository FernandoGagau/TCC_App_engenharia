/**
 * ChatHeader - Header component for chat interface
 * Shows connection status and provides chat controls
 */

import React from 'react';
import {
  Box,
  Typography,
  IconButton,
  Chip,
  Tooltip,
  AppBar,
  Toolbar
} from '@mui/material';
import {
  Close,
  Delete,
  Circle,
  WifiOff,
  Sync
} from '@mui/icons-material';
import { styled } from '@mui/material/styles';

const StyledAppBar = styled(AppBar)(({ theme }) => ({
  position: 'static',
  backgroundColor: theme.palette.background.paper,
  color: theme.palette.text.primary,
  boxShadow: 'none',
  borderBottom: `1px solid ${theme.palette.divider}`,
}));

const StatusChip = styled(Chip)(({ theme, status }) => ({
  height: 24,
  fontSize: '0.75rem',
  '& .MuiChip-icon': {
    width: 12,
    height: 12,
    marginLeft: 8,
  },
  ...(status === 'connected' && {
    backgroundColor: theme.palette.success.light,
    color: theme.palette.success.contrastText,
    '& .MuiChip-icon': {
      color: theme.palette.success.main,
    },
  }),
  ...(status === 'reconnecting' && {
    backgroundColor: theme.palette.warning.light,
    color: theme.palette.warning.contrastText,
    '& .MuiChip-icon': {
      color: theme.palette.warning.main,
    },
  }),
  ...(status === 'disconnected' && {
    backgroundColor: theme.palette.error.light,
    color: theme.palette.error.contrastText,
    '& .MuiChip-icon': {
      color: theme.palette.error.main,
    },
  }),
}));

const SessionInfo = styled(Box)(({ theme }) => ({
  display: 'flex',
  flexDirection: 'column',
  flex: 1,
  minWidth: 0,
}));

const ChatHeader = ({
  sessionId,
  isConnected,
  isReconnecting,
  onClearChat,
  onClose
}) => {
  const getConnectionStatus = () => {
    if (isReconnecting) {
      return {
        status: 'reconnecting',
        label: 'Reconectando...',
        icon: <Sync sx={{ animation: 'spin 1s linear infinite' }} />
      };
    }

    if (isConnected) {
      return {
        status: 'connected',
        label: 'Conectado',
        icon: <Circle />
      };
    }

    return {
      status: 'disconnected',
      label: 'Desconectado',
      icon: <WifiOff />
    };
  };

  const connectionInfo = getConnectionStatus();

  const handleClearChat = () => {
    if (window.confirm('Tem certeza que deseja limpar toda a conversa? Esta ação não pode ser desfeita.')) {
      onClearChat();
    }
  };

  return (
    <StyledAppBar>
      <Toolbar variant="dense" sx={{ minHeight: 56 }}>
        <SessionInfo>
          <Typography
            variant="subtitle1"
            component="h1"
            sx={{
              fontWeight: 600,
              overflow: 'hidden',
              textOverflow: 'ellipsis',
              whiteSpace: 'nowrap'
            }}
          >
            Análise de Projeto
          </Typography>

          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mt: 0.5 }}>
            <StatusChip
              status={connectionInfo.status}
              icon={connectionInfo.icon}
              label={connectionInfo.label}
              size="small"
              variant="filled"
            />

            {sessionId && (
              <Typography
                variant="caption"
                color="text.secondary"
                sx={{
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                  whiteSpace: 'nowrap',
                  maxWidth: 120
                }}
              >
                ID: {sessionId.substring(0, 8)}...
              </Typography>
            )}
          </Box>
        </SessionInfo>

        <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
          <Tooltip title="Limpar conversa">
            <IconButton
              size="small"
              onClick={handleClearChat}
              disabled={!isConnected}
              aria-label="Limpar conversa"
            >
              <Delete />
            </IconButton>
          </Tooltip>

          {onClose && (
            <Tooltip title="Fechar chat">
              <IconButton
                size="small"
                onClick={onClose}
                aria-label="Fechar chat"
              >
                <Close />
              </IconButton>
            </Tooltip>
          )}
        </Box>
      </Toolbar>
    </StyledAppBar>
  );
};

export default ChatHeader;