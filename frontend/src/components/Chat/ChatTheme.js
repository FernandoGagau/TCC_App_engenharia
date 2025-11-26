/**
 * ChatTheme - Theme configuration for Chat components
 * Provides light and dark theme variants for the chat interface
 */

import { createTheme } from '@mui/material/styles';

// Base chat theme configuration
const baseChatTheme = {
  spacing: 8,
  shape: {
    borderRadius: 8,
  },
  typography: {
    fontFamily: '"Inter", "Roboto", "Helvetica", "Arial", sans-serif',
    body1: {
      fontSize: '0.95rem',
      lineHeight: 1.6,
    },
    body2: {
      fontSize: '0.875rem',
      lineHeight: 1.5,
    },
    caption: {
      fontSize: '0.75rem',
      lineHeight: 1.4,
    },
  },
  components: {
    MuiPaper: {
      styleOverrides: {
        root: {
          backgroundImage: 'none',
        },
      },
    },
    MuiButton: {
      styleOverrides: {
        root: {
          textTransform: 'none',
          borderRadius: 8,
        },
      },
    },
    MuiIconButton: {
      styleOverrides: {
        root: {
          borderRadius: 8,
        },
      },
    },
    MuiAvatar: {
      styleOverrides: {
        root: {
          fontWeight: 600,
        },
      },
    },
  },
};

// Light theme for chat
export const chatTheme = createTheme({
  ...baseChatTheme,
  palette: {
    mode: 'light',
    primary: {
      main: '#1976d2',
      light: '#42a5f5',
      dark: '#1565c0',
      contrastText: '#ffffff',
    },
    secondary: {
      main: '#9c27b0',
      light: '#ba68c8',
      dark: '#7b1fa2',
      contrastText: '#ffffff',
    },
    success: {
      main: '#2e7d32',
      light: '#4caf50',
      dark: '#1b5e20',
    },
    warning: {
      main: '#ed6c02',
      light: '#ff9800',
      dark: '#e65100',
    },
    error: {
      main: '#d32f2f',
      light: '#ef5350',
      dark: '#c62828',
    },
    info: {
      main: '#0288d1',
      light: '#03a9f4',
      dark: '#01579b',
    },
    background: {
      default: '#fafafa',
      paper: '#ffffff',
    },
    text: {
      primary: '#1a1a1a',
      secondary: '#666666',
      disabled: '#9e9e9e',
    },
    divider: '#e0e0e0',
    action: {
      hover: 'rgba(0, 0, 0, 0.04)',
      selected: 'rgba(0, 0, 0, 0.08)',
      disabled: 'rgba(0, 0, 0, 0.26)',
      disabledBackground: 'rgba(0, 0, 0, 0.12)',
    },
    chat: {
      // Custom chat-specific colors
      userBubble: '#1976d2',
      userBubbleText: '#ffffff',
      assistantBubble: '#ffffff',
      assistantBubbleText: '#1a1a1a',
      assistantBubbleBorder: '#e0e0e0',
      streamingBubbleBorder: '#1976d2',
      typingIndicator: '#666666',
      connectionConnected: '#2e7d32',
      connectionReconnecting: '#ed6c02',
      connectionDisconnected: '#d32f2f',
      inputBackground: '#ffffff',
      inputBorder: '#e0e0e0',
      inputFocusBorder: '#1976d2',
      dragOverlay: 'rgba(25, 118, 210, 0.1)',
      dragBorder: '#1976d2',
      scrollbarThumb: '#e0e0e0',
      scrollbarTrack: '#fafafa',
      codeBackground: '#f5f5f5',
      codeBorder: '#e0e0e0',
    },
  },
  shadows: [
    'none',
    '0px 1px 3px rgba(0, 0, 0, 0.12), 0px 1px 2px rgba(0, 0, 0, 0.24)',
    '0px 3px 6px rgba(0, 0, 0, 0.16), 0px 3px 6px rgba(0, 0, 0, 0.23)',
    '0px 10px 20px rgba(0, 0, 0, 0.19), 0px 6px 6px rgba(0, 0, 0, 0.23)',
    '0px 14px 28px rgba(0, 0, 0, 0.25), 0px 10px 10px rgba(0, 0, 0, 0.22)',
    '0px 19px 38px rgba(0, 0, 0, 0.30), 0px 15px 12px rgba(0, 0, 0, 0.22)',
  ],
});

// Dark theme for chat
export const darkChatTheme = createTheme({
  ...baseChatTheme,
  palette: {
    mode: 'dark',
    primary: {
      main: '#90caf9',
      light: '#bbdefb',
      dark: '#42a5f5',
      contrastText: '#000000',
    },
    secondary: {
      main: '#ce93d8',
      light: '#f3e5f5',
      dark: '#ab47bc',
      contrastText: '#000000',
    },
    success: {
      main: '#66bb6a',
      light: '#81c784',
      dark: '#4caf50',
    },
    warning: {
      main: '#ffa726',
      light: '#ffb74d',
      dark: '#ff9800',
    },
    error: {
      main: '#f44336',
      light: '#e57373',
      dark: '#d32f2f',
    },
    info: {
      main: '#29b6f6',
      light: '#4fc3f7',
      dark: '#0288d1',
    },
    background: {
      default: '#121212',
      paper: '#1e1e1e',
    },
    text: {
      primary: '#ffffff',
      secondary: '#b3b3b3',
      disabled: '#666666',
    },
    divider: '#333333',
    action: {
      hover: 'rgba(255, 255, 255, 0.08)',
      selected: 'rgba(255, 255, 255, 0.12)',
      disabled: 'rgba(255, 255, 255, 0.26)',
      disabledBackground: 'rgba(255, 255, 255, 0.12)',
    },
    chat: {
      // Custom chat-specific colors for dark mode
      userBubble: '#90caf9',
      userBubbleText: '#000000',
      assistantBubble: '#2d2d2d',
      assistantBubbleText: '#ffffff',
      assistantBubbleBorder: '#404040',
      streamingBubbleBorder: '#90caf9',
      typingIndicator: '#b3b3b3',
      connectionConnected: '#66bb6a',
      connectionReconnecting: '#ffa726',
      connectionDisconnected: '#f44336',
      inputBackground: '#2d2d2d',
      inputBorder: '#404040',
      inputFocusBorder: '#90caf9',
      dragOverlay: 'rgba(144, 202, 249, 0.1)',
      dragBorder: '#90caf9',
      scrollbarThumb: '#404040',
      scrollbarTrack: '#1e1e1e',
      codeBackground: '#0d1117',
      codeBorder: '#404040',
    },
  },
  shadows: [
    'none',
    '0px 1px 3px rgba(0, 0, 0, 0.5), 0px 1px 2px rgba(0, 0, 0, 0.6)',
    '0px 3px 6px rgba(0, 0, 0, 0.6), 0px 3px 6px rgba(0, 0, 0, 0.7)',
    '0px 10px 20px rgba(0, 0, 0, 0.7), 0px 6px 6px rgba(0, 0, 0, 0.8)',
    '0px 14px 28px rgba(0, 0, 0, 0.8), 0px 10px 10px rgba(0, 0, 0, 0.9)',
    '0px 19px 38px rgba(0, 0, 0, 0.9), 0px 15px 12px rgba(0, 0, 0, 1.0)',
  ],
});

// Theme selector utility
export const getChatTheme = (isDarkMode = false) => {
  return isDarkMode ? darkChatTheme : chatTheme;
};

// Custom hook for chat theming
export const useChatTheme = (isDarkMode = false) => {
  return getChatTheme(isDarkMode);
};

// Theme-aware chat colors utility
export const getChatColors = (theme) => {
  return theme.palette.chat;
};

// Responsive breakpoints for chat components
export const chatBreakpoints = {
  mobile: '@media (max-width: 768px)',
  tablet: '@media (max-width: 1024px)',
  desktop: '@media (min-width: 1025px)',
};

// Animation configurations
export const chatAnimations = {
  messageEntry: {
    initial: { opacity: 0, y: 20, scale: 0.95 },
    animate: { opacity: 1, y: 0, scale: 1 },
    exit: { opacity: 0, y: -20, scale: 0.95 },
    transition: { duration: 0.3, ease: 'easeOut' },
  },
  fadeIn: {
    initial: { opacity: 0 },
    animate: { opacity: 1 },
    transition: { duration: 0.3 },
  },
  slideUp: {
    initial: { opacity: 0, y: 20 },
    animate: { opacity: 1, y: 0 },
    transition: { duration: 0.4, ease: 'easeOut' },
  },
  typing: {
    keyframes: {
      '0%, 60%, 100%': { opacity: 1 },
      '30%': { opacity: 0 },
    },
    animation: 'typing 1s infinite',
  },
  bounce: {
    keyframes: {
      '0%, 60%, 100%': { transform: 'translateY(0)' },
      '30%': { transform: 'translateY(-8px)' },
    },
    animation: 'bounce 1.4s infinite ease-in-out',
  },
};

// Z-index configuration for chat layers
export const chatZIndex = {
  backdrop: 1000,
  modal: 1200,
  tooltip: 1500,
  dragOverlay: 10,
  messageActions: 1,
  avatar: 1,
  typingIndicator: 1,
};

export default {
  chatTheme,
  darkChatTheme,
  getChatTheme,
  useChatTheme,
  getChatColors,
  chatBreakpoints,
  chatAnimations,
  chatZIndex,
};