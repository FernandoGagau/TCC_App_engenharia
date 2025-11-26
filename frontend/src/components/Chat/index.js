/**
 * Chat Components Index
 * Centralized exports for all chat-related components
 */

// Main chat components
export { default as ChatContainer } from './ChatContainer';
export { default as ChatHeader } from './ChatHeader';
export { default as MessageList } from './MessageList';
export { default as Message } from './Message';
export { default as StreamingMessage } from './StreamingMessage';
export { default as MessageInput } from './MessageInput';
export { default as TypingIndicator } from './TypingIndicator';

// Theme and styling
export {
  default as ChatTheme,
  chatTheme,
  darkChatTheme,
  getChatTheme,
  useChatTheme,
  getChatColors,
  chatBreakpoints,
  chatAnimations,
  chatZIndex,
} from './ChatTheme';

// Default export for main chat interface
export { default } from './ChatContainer';