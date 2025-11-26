# Frontend Development Guide

This guide covers the React-based frontend development for the Construction Analysis AI System.

## Frontend Overview

### Technology Stack
- **Framework**: React 18 with functional components and hooks
- **UI Library**: Material UI (MUI) for components and theming
- **Build Tool**: Create React App (CRA)
- **Package Manager**: npm
- **State Management**: React hooks and context (no external state library)

### Project Structure
```
frontend/
├── public/              # Static assets
│   ├── index.html      # HTML template
│   └── favicon.ico     # Site icon
├── src/                # React source code
│   ├── components/     # Reusable UI components
│   │   ├── common/     # Generic components
│   │   ├── forms/      # Form components
│   │   ├── layout/     # Layout components
│   │   └── chat/       # Chat interface components
│   ├── services/       # API service functions
│   ├── utils/          # Utility functions
│   ├── App.js          # Main application component
│   ├── App.css         # Global styles
│   ├── index.js        # Entry point
│   └── index.css       # Base styles
├── package.json        # Dependencies and scripts
└── .env                # Environment variables
```

## Component Architecture

### Component Patterns

#### Functional Components with Hooks
All components should be functional components using React hooks:

```javascript
import React, { useState, useEffect } from 'react';
import { Box, Typography, CircularProgress } from '@mui/material';

const ProjectAnalysis = ({ projectId }) => {
  const [analysis, setAnalysis] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchAnalysis = async () => {
      try {
        setLoading(true);
        const response = await fetch(`/api/v1/projects/${projectId}/analysis`);
        const data = await response.json();
        setAnalysis(data);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    if (projectId) {
      fetchAnalysis();
    }
  }, [projectId]);

  if (loading) return <CircularProgress />;
  if (error) return <Typography color="error">{error}</Typography>;

  return (
    <Box>
      <Typography variant="h5">Project Analysis</Typography>
      {/* Analysis content */}
    </Box>
  );
};

export default ProjectAnalysis;
```

#### Component Composition
Break down complex components into smaller, reusable pieces:

```javascript
// components/common/LoadingState.js
const LoadingState = ({ message = "Loading..." }) => (
  <Box display="flex" alignItems="center" gap={2}>
    <CircularProgress size={20} />
    <Typography>{message}</Typography>
  </Box>
);

// components/common/ErrorState.js
const ErrorState = ({ error, onRetry }) => (
  <Box textAlign="center" p={3}>
    <Typography color="error" gutterBottom>
      {error}
    </Typography>
    {onRetry && (
      <Button onClick={onRetry} variant="outlined">
        Try Again
      </Button>
    )}
  </Box>
);
```

### Component Organization

#### Layout Components
```javascript
// components/layout/AppLayout.js
import React from 'react';
import { Box, Container, AppBar, Toolbar, Typography } from '@mui/material';

const AppLayout = ({ children }) => {
  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', minHeight: '100vh' }}>
      <AppBar position="static">
        <Toolbar>
          <Typography variant="h6" component="div" sx={{ flexGrow: 1 }}>
            Construction Analysis AI
          </Typography>
        </Toolbar>
      </AppBar>

      <Container component="main" sx={{ flexGrow: 1, py: 3 }}>
        {children}
      </Container>
    </Box>
  );
};

export default AppLayout;
```

#### Form Components
```javascript
// components/forms/ProjectForm.js
import React, { useState } from 'react';
import {
  Box,
  TextField,
  Button,
  Paper,
  Typography
} from '@mui/material';

const ProjectForm = ({ onSubmit, initialData = {} }) => {
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    location: '',
    ...initialData
  });

  const [errors, setErrors] = useState({});

  const handleChange = (field) => (event) => {
    setFormData(prev => ({
      ...prev,
      [field]: event.target.value
    }));

    // Clear error when user starts typing
    if (errors[field]) {
      setErrors(prev => ({
        ...prev,
        [field]: null
      }));
    }
  };

  const validate = () => {
    const newErrors = {};

    if (!formData.name.trim()) {
      newErrors.name = 'Project name is required';
    }

    if (!formData.location.trim()) {
      newErrors.location = 'Location is required';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (event) => {
    event.preventDefault();

    if (validate()) {
      await onSubmit(formData);
    }
  };

  return (
    <Paper sx={{ p: 3 }}>
      <Typography variant="h6" gutterBottom>
        Project Information
      </Typography>

      <Box component="form" onSubmit={handleSubmit} sx={{ mt: 2 }}>
        <TextField
          fullWidth
          label="Project Name"
          value={formData.name}
          onChange={handleChange('name')}
          error={!!errors.name}
          helperText={errors.name}
          margin="normal"
          required
        />

        <TextField
          fullWidth
          label="Description"
          value={formData.description}
          onChange={handleChange('description')}
          multiline
          rows={3}
          margin="normal"
        />

        <TextField
          fullWidth
          label="Location"
          value={formData.location}
          onChange={handleChange('location')}
          error={!!errors.location}
          helperText={errors.location}
          margin="normal"
          required
        />

        <Button
          type="submit"
          variant="contained"
          sx={{ mt: 3 }}
          fullWidth
        >
          Create Project
        </Button>
      </Box>
    </Paper>
  );
};

export default ProjectForm;
```

## Chat Interface

### Real-time Chat with WebSocket
```javascript
// components/chat/ChatInterface.js
import React, { useState, useEffect, useRef } from 'react';
import {
  Box,
  Paper,
  TextField,
  Button,
  Typography,
  List,
  ListItem,
  Avatar
} from '@mui/material';

const ChatInterface = ({ projectId }) => {
  const [messages, setMessages] = useState([]);
  const [currentMessage, setCurrentMessage] = useState('');
  const [connected, setConnected] = useState(false);
  const wsRef = useRef(null);
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  useEffect(() => {
    const connectWebSocket = () => {
      const wsUrl = `${process.env.REACT_APP_WS_URL}/chat/${projectId}`;
      wsRef.current = new WebSocket(wsUrl);

      wsRef.current.onopen = () => {
        setConnected(true);
        console.log('WebSocket connected');
      };

      wsRef.current.onmessage = (event) => {
        const response = JSON.parse(event.data);
        setMessages(prev => [...prev, {
          id: Date.now(),
          text: response.message,
          sender: 'ai',
          timestamp: new Date()
        }]);
      };

      wsRef.current.onclose = () => {
        setConnected(false);
        console.log('WebSocket disconnected');
      };

      wsRef.current.onerror = (error) => {
        console.error('WebSocket error:', error);
      };
    };

    if (projectId) {
      connectWebSocket();
    }

    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [projectId]);

  const sendMessage = () => {
    if (currentMessage.trim() && connected) {
      // Add user message to UI
      setMessages(prev => [...prev, {
        id: Date.now(),
        text: currentMessage,
        sender: 'user',
        timestamp: new Date()
      }]);

      // Send to WebSocket
      wsRef.current.send(JSON.stringify({
        message: currentMessage,
        project_id: projectId
      }));

      setCurrentMessage('');
    }
  };

  const handleKeyPress = (event) => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      sendMessage();
    }
  };

  return (
    <Paper sx={{ height: 500, display: 'flex', flexDirection: 'column' }}>
      <Box sx={{ p: 2, borderBottom: 1, borderColor: 'divider' }}>
        <Typography variant="h6">
          AI Assistant {connected ? '🟢' : '🔴'}
        </Typography>
      </Box>

      <List sx={{ flexGrow: 1, overflow: 'auto', p: 1 }}>
        {messages.map((message) => (
          <ListItem
            key={message.id}
            sx={{
              justifyContent: message.sender === 'user' ? 'flex-end' : 'flex-start'
            }}
          >
            <Box
              sx={{
                display: 'flex',
                alignItems: 'flex-start',
                gap: 1,
                maxWidth: '70%',
                flexDirection: message.sender === 'user' ? 'row-reverse' : 'row'
              }}
            >
              <Avatar sx={{ width: 32, height: 32 }}>
                {message.sender === 'user' ? 'U' : 'AI'}
              </Avatar>
              <Paper
                sx={{
                  p: 2,
                  backgroundColor: message.sender === 'user' ? 'primary.main' : 'grey.100',
                  color: message.sender === 'user' ? 'primary.contrastText' : 'text.primary'
                }}
              >
                <Typography variant="body2">
                  {message.text}
                </Typography>
              </Paper>
            </Box>
          </ListItem>
        ))}
        <div ref={messagesEndRef} />
      </List>

      <Box sx={{ p: 2, borderTop: 1, borderColor: 'divider' }}>
        <Box sx={{ display: 'flex', gap: 1 }}>
          <TextField
            fullWidth
            multiline
            maxRows={3}
            placeholder="Ask about your construction project..."
            value={currentMessage}
            onChange={(e) => setCurrentMessage(e.target.value)}
            onKeyPress={handleKeyPress}
            disabled={!connected}
          />
          <Button
            variant="contained"
            onClick={sendMessage}
            disabled={!connected || !currentMessage.trim()}
          >
            Send
          </Button>
        </Box>
      </Box>
    </Paper>
  );
};

export default ChatInterface;
```

## File Upload Components

### Image Upload for Analysis
```javascript
// components/common/ImageUpload.js
import React, { useState } from 'react';
import {
  Box,
  Button,
  Typography,
  LinearProgress,
  Alert
} from '@mui/material';
import { CloudUpload } from '@mui/icons-material';

const ImageUpload = ({ onUpload, accept = "image/*" }) => {
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState(null);
  const [dragOver, setDragOver] = useState(false);

  const handleFileSelect = async (files) => {
    if (files.length === 0) return;

    const file = files[0];

    // Validate file type
    if (!file.type.startsWith('image/')) {
      setError('Please select an image file');
      return;
    }

    // Validate file size (10MB max)
    if (file.size > 10 * 1024 * 1024) {
      setError('File size must be less than 10MB');
      return;
    }

    try {
      setUploading(true);
      setError(null);

      const formData = new FormData();
      formData.append('file', file);

      const response = await fetch('/api/v1/analysis/visual', {
        method: 'POST',
        body: formData
      });

      if (!response.ok) {
        throw new Error('Upload failed');
      }

      const result = await response.json();
      onUpload(result);
    } catch (err) {
      setError(err.message);
    } finally {
      setUploading(false);
    }
  };

  const handleDrop = (event) => {
    event.preventDefault();
    setDragOver(false);
    handleFileSelect(event.dataTransfer.files);
  };

  const handleDragOver = (event) => {
    event.preventDefault();
    setDragOver(true);
  };

  const handleDragLeave = () => {
    setDragOver(false);
  };

  return (
    <Box>
      <Box
        sx={{
          border: 2,
          borderColor: dragOver ? 'primary.main' : 'grey.300',
          borderStyle: 'dashed',
          borderRadius: 2,
          p: 4,
          textAlign: 'center',
          cursor: 'pointer',
          backgroundColor: dragOver ? 'primary.50' : 'transparent',
          transition: 'all 0.2s'
        }}
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
      >
        <input
          type="file"
          accept={accept}
          onChange={(e) => handleFileSelect(e.target.files)}
          style={{ display: 'none' }}
          id="file-upload"
        />

        <label htmlFor="file-upload">
          <CloudUpload sx={{ fontSize: 48, color: 'grey.400', mb: 2 }} />
          <Typography variant="h6" gutterBottom>
            Drop images here or click to upload
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Supports JPG, PNG up to 10MB
          </Typography>
        </label>
      </Box>

      {uploading && (
        <Box sx={{ mt: 2 }}>
          <LinearProgress />
          <Typography variant="body2" sx={{ mt: 1 }}>
            Analyzing image...
          </Typography>
        </Box>
      )}

      {error && (
        <Alert severity="error" sx={{ mt: 2 }}>
          {error}
        </Alert>
      )}
    </Box>
  );
};

export default ImageUpload;
```

## API Service Layer

### API Service Functions
```javascript
// services/api.js
const API_BASE = process.env.REACT_APP_API_URL || 'http://localhost:8000';

class ApiError extends Error {
  constructor(message, status, data) {
    super(message);
    this.status = status;
    this.data = data;
  }
}

const handleResponse = async (response) => {
  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new ApiError(
      error.detail || 'An error occurred',
      response.status,
      error
    );
  }
  return response.json();
};

export const api = {
  // Projects
  projects: {
    list: () =>
      fetch(`${API_BASE}/api/v1/projects`).then(handleResponse),

    get: (id) =>
      fetch(`${API_BASE}/api/v1/projects/${id}`).then(handleResponse),

    create: (data) =>
      fetch(`${API_BASE}/api/v1/projects`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
      }).then(handleResponse),

    update: (id, data) =>
      fetch(`${API_BASE}/api/v1/projects/${id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
      }).then(handleResponse),

    delete: (id) =>
      fetch(`${API_BASE}/api/v1/projects/${id}`, {
        method: 'DELETE'
      }).then(handleResponse)
  },

  // Analysis
  analysis: {
    visual: (file) => {
      const formData = new FormData();
      formData.append('file', file);

      return fetch(`${API_BASE}/api/v1/analysis/visual`, {
        method: 'POST',
        body: formData
      }).then(handleResponse);
    },

    document: (file) => {
      const formData = new FormData();
      formData.append('file', file);

      return fetch(`${API_BASE}/api/v1/analysis/document`, {
        method: 'POST',
        body: formData
      }).then(handleResponse);
    }
  },

  // Reports
  reports: {
    get: (id) =>
      fetch(`${API_BASE}/api/v1/reports/${id}`).then(handleResponse),

    generate: (projectId, type) =>
      fetch(`${API_BASE}/api/v1/reports`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ project_id: projectId, type })
      }).then(handleResponse)
  }
};
```

### Custom Hooks for Data Fetching
```javascript
// hooks/useApi.js
import { useState, useEffect } from 'react';

export const useApi = (apiCall, dependencies = []) => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        setError(null);
        const result = await apiCall();
        setData(result);
      } catch (err) {
        setError(err);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, dependencies);

  const refetch = () => {
    return fetchData();
  };

  return { data, loading, error, refetch };
};

// hooks/useProjects.js
import { useApi } from './useApi';
import { api } from '../services/api';

export const useProjects = () => {
  return useApi(() => api.projects.list());
};

export const useProject = (projectId) => {
  return useApi(() => api.projects.get(projectId), [projectId]);
};
```

## Styling and Theming

### Material UI Theme
```javascript
// theme.js
import { createTheme } from '@mui/material/styles';

export const theme = createTheme({
  palette: {
    primary: {
      main: '#1976d2',
      light: '#42a5f5',
      dark: '#1565c0',
    },
    secondary: {
      main: '#f57c00',
      light: '#ffb74d',
      dark: '#ef6c00',
    },
    error: {
      main: '#d32f2f',
    },
    warning: {
      main: '#f57c00',
    },
    info: {
      main: '#0288d1',
    },
    success: {
      main: '#388e3c',
    },
  },
  typography: {
    fontFamily: '"Roboto", "Helvetica", "Arial", sans-serif',
    h4: {
      fontWeight: 600,
    },
    h5: {
      fontWeight: 500,
    },
    h6: {
      fontWeight: 500,
    },
  },
  components: {
    MuiButton: {
      styleOverrides: {
        root: {
          textTransform: 'none',
          borderRadius: 8,
        },
      },
    },
    MuiPaper: {
      styleOverrides: {
        root: {
          borderRadius: 12,
        },
      },
    },
  },
});
```

### Using the Theme
```javascript
// App.js
import React from 'react';
import { ThemeProvider } from '@mui/material/styles';
import { CssBaseline } from '@mui/material';
import { theme } from './theme';
import AppLayout from './components/layout/AppLayout';
import ProjectDashboard from './components/ProjectDashboard';

function App() {
  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <AppLayout>
        <ProjectDashboard />
      </AppLayout>
    </ThemeProvider>
  );
}

export default App;
```

## Testing

### Component Testing with React Testing Library
```javascript
// components/__tests__/ProjectForm.test.js
import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { ThemeProvider } from '@mui/material/styles';
import { theme } from '../../theme';
import ProjectForm from '../forms/ProjectForm';

const renderWithTheme = (component) => {
  return render(
    <ThemeProvider theme={theme}>
      {component}
    </ThemeProvider>
  );
};

describe('ProjectForm', () => {
  test('renders form fields', () => {
    renderWithTheme(<ProjectForm onSubmit={jest.fn()} />);

    expect(screen.getByLabelText(/project name/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/description/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/location/i)).toBeInTheDocument();
  });

  test('validates required fields', async () => {
    const mockSubmit = jest.fn();
    renderWithTheme(<ProjectForm onSubmit={mockSubmit} />);

    fireEvent.click(screen.getByText(/create project/i));

    await waitFor(() => {
      expect(screen.getByText(/project name is required/i)).toBeInTheDocument();
      expect(screen.getByText(/location is required/i)).toBeInTheDocument();
    });

    expect(mockSubmit).not.toHaveBeenCalled();
  });

  test('submits form with valid data', async () => {
    const mockSubmit = jest.fn();
    renderWithTheme(<ProjectForm onSubmit={mockSubmit} />);

    fireEvent.change(screen.getByLabelText(/project name/i), {
      target: { value: 'Test Project' }
    });
    fireEvent.change(screen.getByLabelText(/location/i), {
      target: { value: 'Test Location' }
    });

    fireEvent.click(screen.getByText(/create project/i));

    await waitFor(() => {
      expect(mockSubmit).toHaveBeenCalledWith({
        name: 'Test Project',
        description: '',
        location: 'Test Location'
      });
    });
  });
});
```

## Performance Optimization

### Code Splitting and Lazy Loading
```javascript
// App.js with lazy loading
import React, { Suspense } from 'react';
import { CircularProgress, Box } from '@mui/material';

// Lazy load components
const ProjectDashboard = React.lazy(() => import('./components/ProjectDashboard'));
const ProjectDetail = React.lazy(() => import('./components/ProjectDetail'));

const LoadingSpinner = () => (
  <Box display="flex" justifyContent="center" alignItems="center" height="200px">
    <CircularProgress />
  </Box>
);

function App() {
  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <AppLayout>
        <Suspense fallback={<LoadingSpinner />}>
          <ProjectDashboard />
        </Suspense>
      </AppLayout>
    </ThemeProvider>
  );
}
```

### Memoization for Performance
```javascript
import React, { memo, useMemo } from 'react';

const ProjectCard = memo(({ project, onClick }) => {
  const formattedDate = useMemo(() => {
    return new Intl.DateTimeFormat('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric'
    }).format(new Date(project.created_at));
  }, [project.created_at]);

  return (
    <Card onClick={() => onClick(project.id)}>
      <CardContent>
        <Typography variant="h6">{project.name}</Typography>
        <Typography variant="body2" color="text.secondary">
          Created: {formattedDate}
        </Typography>
      </CardContent>
    </Card>
  );
});
```

## Environment Configuration

### Environment Variables
```bash
# .env (frontend)
REACT_APP_API_URL=http://localhost:8000
REACT_APP_WS_URL=ws://localhost:8000
REACT_APP_APP_NAME=Construction Analysis AI
REACT_APP_VERSION=1.0.0
```

### Build Configuration
```json
// package.json scripts
{
  "scripts": {
    "start": "react-scripts start",
    "build": "react-scripts build",
    "test": "react-scripts test",
    "test:coverage": "react-scripts test --coverage --watchAll=false",
    "lint": "eslint src/**/*.{js,jsx}",
    "lint:fix": "eslint src/**/*.{js,jsx} --fix"
  }
}
```

This frontend guide provides a comprehensive foundation for building the React-based user interface for the Construction Analysis AI System, following modern React patterns and Material UI best practices.