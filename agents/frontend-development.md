# Frontend Development Agent

## Overview

The Frontend Development Agent specializes in React development for the Construction Analysis AI System. This agent provides guidance on UI/UX implementation, component architecture, state management, and user experience optimization.

## Capabilities

### 🎨 UI/UX Development
- React 18 with hooks and modern patterns
- Material-UI (MUI) component library integration
- Responsive design and mobile optimization
- Accessibility (a11y) compliance
- Theme management and design system

### ⚡ Performance Optimization
- Code splitting and lazy loading
- Bundle size optimization
- Memoization strategies
- Virtual scrolling for large datasets
- Image optimization and lazy loading

### 🔄 State Management
- React Context for global state
- Custom hooks for reusable logic
- Local component state optimization
- Server state management with React Query
- Form state with React Hook Form

## Core Responsibilities

### 1. Component Architecture

#### Base Layout Component
```tsx
// components/Layout/Layout.tsx
import React from 'react';
import { Box, Container, AppBar, Toolbar, Typography } from '@mui/material';
import { Sidebar } from './Sidebar';
import { Navigation } from './Navigation';

interface LayoutProps {
  children: React.ReactNode;
  title?: string;
}

export const Layout: React.FC<LayoutProps> = ({ children, title = 'Construction Analysis' }) => {
  return (
    <Box sx={{ display: 'flex', minHeight: '100vh' }}>
      <AppBar position="fixed" sx={{ zIndex: (theme) => theme.zIndex.drawer + 1 }}>
        <Toolbar>
          <Typography variant="h6" component="div" sx={{ flexGrow: 1 }}>
            {title}
          </Typography>
          <Navigation />
        </Toolbar>
      </AppBar>

      <Sidebar />

      <Box component="main" sx={{ flexGrow: 1, p: 3, mt: 8 }}>
        <Container maxWidth="xl">
          {children}
        </Container>
      </Box>
    </Box>
  );
};
```

#### Project Dashboard Component
```tsx
// components/Dashboard/ProjectDashboard.tsx
import React, { useState, useEffect } from 'react';
import {
  Grid,
  Card,
  CardContent,
  Typography,
  Box,
  CircularProgress,
  Alert
} from '@mui/material';
import { ProjectCard } from './ProjectCard';
import { AnalysisMetrics } from './AnalysisMetrics';
import { useProjects } from '../hooks/useProjects';

export const ProjectDashboard: React.FC = () => {
  const { projects, loading, error, refetch } = useProjects();

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" p={4}>
        <CircularProgress />
      </Box>
    );
  }

  if (error) {
    return (
      <Alert severity="error" sx={{ mb: 2 }}>
        Failed to load projects: {error.message}
      </Alert>
    );
  }

  return (
    <Grid container spacing={3}>
      <Grid item xs={12}>
        <AnalysisMetrics projects={projects} />
      </Grid>

      {projects.map((project) => (
        <Grid item xs={12} md={6} lg={4} key={project.id}>
          <ProjectCard
            project={project}
            onUpdate={refetch}
          />
        </Grid>
      ))}
    </Grid>
  );
};
```

### 2. Custom Hooks

#### API Integration Hook
```tsx
// hooks/useApi.ts
import { useState, useCallback } from 'react';
import { apiClient } from '../services/apiClient';

interface UseApiOptions<T> {
  onSuccess?: (data: T) => void;
  onError?: (error: Error) => void;
}

export function useApi<T = any, P = any>() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const [data, setData] = useState<T | null>(null);

  const execute = useCallback(async (
    endpoint: string,
    options?: RequestInit,
    config?: UseApiOptions<T>
  ) => {
    try {
      setLoading(true);
      setError(null);

      const response = await apiClient.request<T>(endpoint, options);
      setData(response);

      config?.onSuccess?.(response);
      return response;
    } catch (err) {
      const error = err instanceof Error ? err : new Error('Unknown error');
      setError(error);
      config?.onError?.(error);
      throw error;
    } finally {
      setLoading(false);
    }
  }, []);

  return { execute, loading, error, data };
}
```

#### WebSocket Hook for Real-time Chat
```tsx
// hooks/useWebSocket.ts
import { useState, useEffect, useRef, useCallback } from 'react';

interface UseWebSocketOptions {
  url: string;
  onMessage?: (message: any) => void;
  onError?: (error: Event) => void;
  reconnectInterval?: number;
}

export function useWebSocket({
  url,
  onMessage,
  onError,
  reconnectInterval = 3000
}: UseWebSocketOptions) {
  const [connectionStatus, setConnectionStatus] = useState<'connecting' | 'connected' | 'disconnected'>('disconnected');
  const [lastMessage, setLastMessage] = useState<any>(null);
  const ws = useRef<WebSocket | null>(null);
  const reconnectTimeoutId = useRef<NodeJS.Timeout | null>(null);

  const connect = useCallback(() => {
    try {
      ws.current = new WebSocket(url);
      setConnectionStatus('connecting');

      ws.current.onopen = () => {
        setConnectionStatus('connected');
      };

      ws.current.onmessage = (event) => {
        const message = JSON.parse(event.data);
        setLastMessage(message);
        onMessage?.(message);
      };

      ws.current.onerror = (error) => {
        onError?.(error);
      };

      ws.current.onclose = () => {
        setConnectionStatus('disconnected');

        // Auto-reconnect
        reconnectTimeoutId.current = setTimeout(() => {
          connect();
        }, reconnectInterval);
      };
    } catch (error) {
      console.error('WebSocket connection error:', error);
    }
  }, [url, onMessage, onError, reconnectInterval]);

  const sendMessage = useCallback((message: any) => {
    if (ws.current?.readyState === WebSocket.OPEN) {
      ws.current.send(JSON.stringify(message));
    }
  }, []);

  useEffect(() => {
    connect();

    return () => {
      if (reconnectTimeoutId.current) {
        clearTimeout(reconnectTimeoutId.current);
      }
      ws.current?.close();
    };
  }, [connect]);

  return { connectionStatus, lastMessage, sendMessage };
}
```

### 3. File Upload Component

```tsx
// components/FileUpload/FileUpload.tsx
import React, { useCallback, useState } from 'react';
import { useDropzone } from 'react-dropzone';
import {
  Box,
  Typography,
  LinearProgress,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  IconButton,
  Alert
} from '@mui/material';
import { CloudUpload, InsertDriveFile, Delete } from '@mui/icons-material';
import { uploadFile } from '../services/fileService';

interface FileUploadProps {
  onUploadComplete: (files: FileUploadResult[]) => void;
  acceptedFileTypes?: string[];
  maxFiles?: number;
  maxSize?: number; // in bytes
}

interface FileUploadResult {
  id: string;
  name: string;
  url: string;
  size: number;
  type: string;
}

export const FileUpload: React.FC<FileUploadProps> = ({
  onUploadComplete,
  acceptedFileTypes = ['image/*', '.pdf', '.doc', '.docx'],
  maxFiles = 10,
  maxSize = 10 * 1024 * 1024 // 10MB
}) => {
  const [uploadProgress, setUploadProgress] = useState<Record<string, number>>({});
  const [uploadedFiles, setUploadedFiles] = useState<FileUploadResult[]>([]);
  const [error, setError] = useState<string | null>(null);

  const onDrop = useCallback(async (acceptedFiles: File[]) => {
    setError(null);

    for (const file of acceptedFiles) {
      if (file.size > maxSize) {
        setError(`File ${file.name} is too large. Maximum size is ${maxSize / (1024 * 1024)}MB`);
        continue;
      }

      try {
        const fileId = `${Date.now()}-${file.name}`;
        setUploadProgress(prev => ({ ...prev, [fileId]: 0 }));

        const result = await uploadFile(file, {
          onProgress: (progress) => {
            setUploadProgress(prev => ({ ...prev, [fileId]: progress }));
          }
        });

        const uploadResult: FileUploadResult = {
          id: result.id,
          name: file.name,
          url: result.url,
          size: file.size,
          type: file.type
        };

        setUploadedFiles(prev => [...prev, uploadResult]);
        setUploadProgress(prev => {
          const { [fileId]: _, ...rest } = prev;
          return rest;
        });
      } catch (error) {
        setError(`Failed to upload ${file.name}`);
        setUploadProgress(prev => {
          const { [fileId]: _, ...rest } = prev;
          return rest;
        });
      }
    }
  }, [maxSize]);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: acceptedFileTypes.reduce((acc, type) => ({ ...acc, [type]: [] }), {}),
    maxFiles,
    multiple: true
  });

  const removeFile = (fileId: string) => {
    setUploadedFiles(prev => prev.filter(f => f.id !== fileId));
  };

  React.useEffect(() => {
    if (uploadedFiles.length > 0) {
      onUploadComplete(uploadedFiles);
    }
  }, [uploadedFiles, onUploadComplete]);

  return (
    <Box>
      <Box
        {...getRootProps()}
        sx={{
          border: '2px dashed',
          borderColor: isDragActive ? 'primary.main' : 'grey.300',
          borderRadius: 2,
          p: 3,
          textAlign: 'center',
          cursor: 'pointer',
          bgcolor: isDragActive ? 'action.hover' : 'background.paper',
          '&:hover': {
            bgcolor: 'action.hover'
          }
        }}
      >
        <input {...getInputProps()} />
        <CloudUpload sx={{ fontSize: 48, color: 'text.secondary', mb: 2 }} />
        <Typography variant="h6" gutterBottom>
          {isDragActive ? 'Drop files here' : 'Drag & drop files here'}
        </Typography>
        <Typography variant="body2" color="text.secondary">
          or click to select files
        </Typography>
        <Typography variant="caption" display="block" sx={{ mt: 1 }}>
          Supported formats: {acceptedFileTypes.join(', ')}
        </Typography>
      </Box>

      {error && (
        <Alert severity="error" sx={{ mt: 2 }}>
          {error}
        </Alert>
      )}

      {Object.keys(uploadProgress).length > 0 && (
        <Box sx={{ mt: 2 }}>
          {Object.entries(uploadProgress).map(([fileId, progress]) => (
            <Box key={fileId} sx={{ mb: 1 }}>
              <Typography variant="body2">Uploading...</Typography>
              <LinearProgress variant="determinate" value={progress} />
            </Box>
          ))}
        </Box>
      )}

      {uploadedFiles.length > 0 && (
        <List sx={{ mt: 2 }}>
          {uploadedFiles.map((file) => (
            <ListItem
              key={file.id}
              secondaryAction={
                <IconButton edge="end" onClick={() => removeFile(file.id)}>
                  <Delete />
                </IconButton>
              }
            >
              <ListItemIcon>
                <InsertDriveFile />
              </ListItemIcon>
              <ListItemText
                primary={file.name}
                secondary={`${(file.size / 1024 / 1024).toFixed(2)} MB`}
              />
            </ListItem>
          ))}
        </List>
      )}
    </Box>
  );
};
```

### 4. Chat Interface Component

```tsx
// components/Chat/ChatInterface.tsx
import React, { useState, useRef, useEffect } from 'react';
import {
  Box,
  Paper,
  TextField,
  IconButton,
  List,
  ListItem,
  Typography,
  Avatar,
  Chip
} from '@mui/material';
import { Send, AttachFile } from '@mui/icons-material';
import { useWebSocket } from '../hooks/useWebSocket';

interface Message {
  id: string;
  content: string;
  sender: 'user' | 'agent';
  timestamp: Date;
  type: 'text' | 'file' | 'analysis';
  metadata?: any;
}

interface ChatInterfaceProps {
  sessionId: string;
  onFileUpload?: (files: File[]) => void;
}

export const ChatInterface: React.FC<ChatInterfaceProps> = ({
  sessionId,
  onFileUpload
}) => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputValue, setInputValue] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const { connectionStatus, sendMessage } = useWebSocket({
    url: `ws://localhost:8000/ws/${sessionId}`,
    onMessage: (message) => {
      if (message.type === 'message') {
        setMessages(prev => [...prev, {
          id: message.id,
          content: message.content,
          sender: 'agent',
          timestamp: new Date(message.timestamp),
          type: message.messageType || 'text',
          metadata: message.metadata
        }]);
      } else if (message.type === 'typing') {
        setIsTyping(message.isTyping);
      }
    }
  });

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSendMessage = () => {
    if (!inputValue.trim()) return;

    const newMessage: Message = {
      id: Date.now().toString(),
      content: inputValue,
      sender: 'user',
      timestamp: new Date(),
      type: 'text'
    };

    setMessages(prev => [...prev, newMessage]);

    sendMessage({
      type: 'message',
      content: inputValue,
      sessionId
    });

    setInputValue('');
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || []);
    if (files.length > 0) {
      onFileUpload?.(files);
    }
  };

  const formatMessage = (message: Message) => {
    switch (message.type) {
      case 'analysis':
        return (
          <Box>
            <Typography variant="body1" gutterBottom>
              {message.content}
            </Typography>
            {message.metadata?.analysisType && (
              <Chip
                label={message.metadata.analysisType}
                size="small"
                color="primary"
              />
            )}
          </Box>
        );
      default:
        return <Typography variant="body1">{message.content}</Typography>;
    }
  };

  return (
    <Paper sx={{ height: '600px', display: 'flex', flexDirection: 'column' }}>
      {/* Connection Status */}
      <Box sx={{ p: 1, bgcolor: 'grey.100', textAlign: 'center' }}>
        <Chip
          label={connectionStatus}
          color={connectionStatus === 'connected' ? 'success' : 'default'}
          size="small"
        />
      </Box>

      {/* Messages */}
      <List sx={{ flex: 1, overflow: 'auto', p: 1 }}>
        {messages.map((message) => (
          <ListItem
            key={message.id}
            sx={{
              display: 'flex',
              justifyContent: message.sender === 'user' ? 'flex-end' : 'flex-start',
              alignItems: 'flex-start',
              mb: 1
            }}
          >
            <Box
              sx={{
                display: 'flex',
                flexDirection: message.sender === 'user' ? 'row-reverse' : 'row',
                alignItems: 'flex-start',
                maxWidth: '70%'
              }}
            >
              <Avatar
                sx={{
                  bgcolor: message.sender === 'user' ? 'primary.main' : 'secondary.main',
                  mx: 1
                }}
              >
                {message.sender === 'user' ? 'U' : 'AI'}
              </Avatar>
              <Paper
                sx={{
                  p: 2,
                  bgcolor: message.sender === 'user' ? 'primary.light' : 'grey.100',
                  color: message.sender === 'user' ? 'white' : 'text.primary'
                }}
              >
                {formatMessage(message)}
                <Typography variant="caption" sx={{ display: 'block', mt: 1, opacity: 0.7 }}>
                  {message.timestamp.toLocaleTimeString()}
                </Typography>
              </Paper>
            </Box>
          </ListItem>
        ))}

        {isTyping && (
          <ListItem>
            <Box sx={{ display: 'flex', alignItems: 'center' }}>
              <Avatar sx={{ bgcolor: 'secondary.main', mr: 1 }}>AI</Avatar>
              <Typography variant="body2" sx={{ fontStyle: 'italic' }}>
                Agent is typing...
              </Typography>
            </Box>
          </ListItem>
        )}

        <div ref={messagesEndRef} />
      </List>

      {/* Input */}
      <Box sx={{ p: 2, borderTop: 1, borderColor: 'divider' }}>
        <Box sx={{ display: 'flex', alignItems: 'center' }}>
          <input
            type="file"
            ref={fileInputRef}
            onChange={handleFileSelect}
            style={{ display: 'none' }}
            multiple
            accept="image/*,.pdf,.doc,.docx"
          />

          <IconButton onClick={() => fileInputRef.current?.click()}>
            <AttachFile />
          </IconButton>

          <TextField
            fullWidth
            multiline
            maxRows={4}
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="Type your message..."
            variant="outlined"
            size="small"
            sx={{ mx: 1 }}
          />

          <IconButton
            onClick={handleSendMessage}
            disabled={!inputValue.trim() || connectionStatus !== 'connected'}
            color="primary"
          >
            <Send />
          </IconButton>
        </Box>
      </Box>
    </Paper>
  );
};
```

## State Management

### Context Provider
```tsx
// contexts/AppContext.tsx
import React, { createContext, useContext, useReducer, ReactNode } from 'react';

interface AppState {
  user: User | null;
  projects: Project[];
  currentProject: Project | null;
  theme: 'light' | 'dark';
  notifications: Notification[];
}

type AppAction =
  | { type: 'SET_USER'; payload: User | null }
  | { type: 'SET_PROJECTS'; payload: Project[] }
  | { type: 'SET_CURRENT_PROJECT'; payload: Project | null }
  | { type: 'TOGGLE_THEME' }
  | { type: 'ADD_NOTIFICATION'; payload: Notification }
  | { type: 'REMOVE_NOTIFICATION'; payload: string };

const initialState: AppState = {
  user: null,
  projects: [],
  currentProject: null,
  theme: 'light',
  notifications: []
};

const appReducer = (state: AppState, action: AppAction): AppState => {
  switch (action.type) {
    case 'SET_USER':
      return { ...state, user: action.payload };
    case 'SET_PROJECTS':
      return { ...state, projects: action.payload };
    case 'SET_CURRENT_PROJECT':
      return { ...state, currentProject: action.payload };
    case 'TOGGLE_THEME':
      return { ...state, theme: state.theme === 'light' ? 'dark' : 'light' };
    case 'ADD_NOTIFICATION':
      return { ...state, notifications: [...state.notifications, action.payload] };
    case 'REMOVE_NOTIFICATION':
      return {
        ...state,
        notifications: state.notifications.filter(n => n.id !== action.payload)
      };
    default:
      return state;
  }
};

const AppContext = createContext<{
  state: AppState;
  dispatch: React.Dispatch<AppAction>;
} | null>(null);

export const AppProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [state, dispatch] = useReducer(appReducer, initialState);

  return (
    <AppContext.Provider value={{ state, dispatch }}>
      {children}
    </AppContext.Provider>
  );
};

export const useAppContext = () => {
  const context = useContext(AppContext);
  if (!context) {
    throw new Error('useAppContext must be used within AppProvider');
  }
  return context;
};
```

## Performance Optimization

### Memoization
```tsx
// Memoized components for performance
export const ProjectCard = React.memo<ProjectCardProps>(({ project, onUpdate }) => {
  const handleUpdate = useCallback(() => {
    onUpdate(project.id);
  }, [project.id, onUpdate]);

  return (
    <Card>
      <CardContent>
        <Typography variant="h6">{project.name}</Typography>
        <Button onClick={handleUpdate}>Update</Button>
      </CardContent>
    </Card>
  );
});
```

### Code Splitting
```tsx
// Lazy loading for route components
const Dashboard = React.lazy(() => import('../pages/Dashboard'));
const Projects = React.lazy(() => import('../pages/Projects'));
const Analysis = React.lazy(() => import('../pages/Analysis'));

function AppRoutes() {
  return (
    <Suspense fallback={<CircularProgress />}>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/projects" element={<Projects />} />
        <Route path="/analysis/:id" element={<Analysis />} />
      </Routes>
    </Suspense>
  );
}
```

## Testing Strategies

### Component Testing
```tsx
// __tests__/components/ProjectCard.test.tsx
import { render, screen, fireEvent } from '@testing-library/react';
import { ProjectCard } from '../ProjectCard';

describe('ProjectCard', () => {
  const mockProject = {
    id: '1',
    name: 'Test Project',
    status: 'active'
  };

  it('renders project information correctly', () => {
    render(<ProjectCard project={mockProject} onUpdate={jest.fn()} />);

    expect(screen.getByText('Test Project')).toBeInTheDocument();
    expect(screen.getByText('active')).toBeInTheDocument();
  });

  it('calls onUpdate when update button is clicked', () => {
    const mockOnUpdate = jest.fn();
    render(<ProjectCard project={mockProject} onUpdate={mockOnUpdate} />);

    fireEvent.click(screen.getByText('Update'));
    expect(mockOnUpdate).toHaveBeenCalledWith('1');
  });
});
```

This Frontend Development Agent provides comprehensive guidance for building a modern, performant React application for the Construction Analysis AI System.