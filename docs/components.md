# Components Documentation

This document provides comprehensive documentation for the React components used in the Construction Analysis AI frontend application.

## Component Architecture

### Design System
The component architecture follows Material UI design principles with custom theming and construction-specific components.

### Component Categories
- **Layout Components**: Page structure and navigation
- **Form Components**: Data input and validation
- **Display Components**: Data presentation and visualization
- **Interactive Components**: User interaction elements
- **Chat Components**: Real-time communication interface

## Layout Components

### AppLayout
Main application layout wrapper that provides consistent structure across all pages.

```javascript
// components/layout/AppLayout.js
import React from 'react';
import {
  Box,
  Container,
  AppBar,
  Toolbar,
  Typography,
  Drawer,
  List,
  ListItem,
  ListItemIcon,
  ListItemText
} from '@mui/material';
import { Dashboard, Assignment, Analytics, Settings } from '@mui/icons-material';

const DRAWER_WIDTH = 240;

const AppLayout = ({ children, title = "Construction Analysis AI" }) => {
  const [mobileOpen, setMobileOpen] = React.useState(false);

  const handleDrawerToggle = () => {
    setMobileOpen(!mobileOpen);
  };

  const menuItems = [
    { text: 'Dashboard', icon: <Dashboard />, path: '/' },
    { text: 'Projects', icon: <Assignment />, path: '/projects' },
    { text: 'Analytics', icon: <Analytics />, path: '/analytics' },
    { text: 'Settings', icon: <Settings />, path: '/settings' },
  ];

  const drawer = (
    <Box>
      <Toolbar>
        <Typography variant="h6" noWrap>
          Menu
        </Typography>
      </Toolbar>
      <List>
        {menuItems.map((item) => (
          <ListItem button key={item.text}>
            <ListItemIcon>{item.icon}</ListItemIcon>
            <ListItemText primary={item.text} />
          </ListItem>
        ))}
      </List>
    </Box>
  );

  return (
    <Box sx={{ display: 'flex' }}>
      <AppBar position="fixed" sx={{ zIndex: (theme) => theme.zIndex.drawer + 1 }}>
        <Toolbar>
          <Typography variant="h6" noWrap component="div">
            {title}
          </Typography>
        </Toolbar>
      </AppBar>

      <Drawer
        variant="permanent"
        sx={{
          width: DRAWER_WIDTH,
          flexShrink: 0,
          [`& .MuiDrawer-paper`]: { width: DRAWER_WIDTH, boxSizing: 'border-box' },
        }}
      >
        {drawer}
      </Drawer>

      <Box component="main" sx={{ flexGrow: 1, p: 3 }}>
        <Toolbar />
        <Container maxWidth="xl">
          {children}
        </Container>
      </Box>
    </Box>
  );
};

export default AppLayout;
```

### PageHeader
Consistent page header with breadcrumbs and actions.

```javascript
// components/layout/PageHeader.js
import React from 'react';
import {
  Box,
  Typography,
  Breadcrumbs,
  Link,
  Button,
  Stack
} from '@mui/material';
import { Add } from '@mui/icons-material';

const PageHeader = ({
  title,
  breadcrumbs = [],
  actions = [],
  description
}) => {
  return (
    <Box sx={{ mb: 4 }}>
      {breadcrumbs.length > 0 && (
        <Breadcrumbs sx={{ mb: 1 }}>
          {breadcrumbs.map((crumb, index) => (
            <Link
              key={index}
              color="inherit"
              href={crumb.href}
              underline="hover"
            >
              {crumb.text}
            </Link>
          ))}
        </Breadcrumbs>
      )}

      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Box>
          <Typography variant="h4" component="h1" gutterBottom>
            {title}
          </Typography>
          {description && (
            <Typography variant="body1" color="text.secondary">
              {description}
            </Typography>
          )}
        </Box>

        {actions.length > 0 && (
          <Stack direction="row" spacing={2}>
            {actions.map((action, index) => (
              <Button
                key={index}
                variant={action.variant || 'contained'}
                color={action.color || 'primary'}
                startIcon={action.icon}
                onClick={action.onClick}
              >
                {action.text}
              </Button>
            ))}
          </Stack>
        )}
      </Box>
    </Box>
  );
};

export default PageHeader;
```

## Form Components

### ProjectForm
Comprehensive form for creating and editing construction projects.

```javascript
// components/forms/ProjectForm.js
import React, { useState } from 'react';
import {
  Box,
  Card,
  CardContent,
  TextField,
  Button,
  Grid,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Alert,
  LinearProgress
} from '@mui/material';
import { Save, Cancel } from '@mui/icons-material';

const ProjectForm = ({
  initialData = {},
  onSubmit,
  onCancel,
  loading = false
}) => {
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    location: '',
    type: '',
    startDate: '',
    estimatedEndDate: '',
    budget: '',
    contractor: '',
    ...initialData
  });

  const [errors, setErrors] = useState({});
  const [submitError, setSubmitError] = useState(null);

  const projectTypes = [
    'residential',
    'commercial',
    'industrial',
    'infrastructure',
    'renovation'
  ];

  const handleChange = (field) => (event) => {
    const value = event.target.value;
    setFormData(prev => ({ ...prev, [field]: value }));

    // Clear field error when user starts typing
    if (errors[field]) {
      setErrors(prev => ({ ...prev, [field]: null }));
    }
  };

  const validateForm = () => {
    const newErrors = {};

    if (!formData.name.trim()) {
      newErrors.name = 'Project name is required';
    }

    if (!formData.location.trim()) {
      newErrors.location = 'Location is required';
    }

    if (!formData.type) {
      newErrors.type = 'Project type is required';
    }

    if (formData.startDate && formData.estimatedEndDate) {
      if (new Date(formData.startDate) >= new Date(formData.estimatedEndDate)) {
        newErrors.estimatedEndDate = 'End date must be after start date';
      }
    }

    if (formData.budget && isNaN(Number(formData.budget))) {
      newErrors.budget = 'Budget must be a valid number';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    setSubmitError(null);

    if (validateForm()) {
      try {
        await onSubmit(formData);
      } catch (error) {
        setSubmitError(error.message || 'Failed to save project');
      }
    }
  };

  return (
    <Card>
      {loading && <LinearProgress />}

      <CardContent>
        {submitError && (
          <Alert severity="error" sx={{ mb: 3 }}>
            {submitError}
          </Alert>
        )}

        <Box component="form" onSubmit={handleSubmit}>
          <Grid container spacing={3}>
            <Grid item xs={12} md={6}>
              <TextField
                fullWidth
                label="Project Name"
                value={formData.name}
                onChange={handleChange('name')}
                error={!!errors.name}
                helperText={errors.name}
                required
                disabled={loading}
              />
            </Grid>

            <Grid item xs={12} md={6}>
              <FormControl fullWidth error={!!errors.type} required>
                <InputLabel>Project Type</InputLabel>
                <Select
                  value={formData.type}
                  onChange={handleChange('type')}
                  disabled={loading}
                >
                  {projectTypes.map((type) => (
                    <MenuItem key={type} value={type}>
                      {type.charAt(0).toUpperCase() + type.slice(1)}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Grid>

            <Grid item xs={12}>
              <TextField
                fullWidth
                label="Description"
                value={formData.description}
                onChange={handleChange('description')}
                multiline
                rows={3}
                disabled={loading}
              />
            </Grid>

            <Grid item xs={12}>
              <TextField
                fullWidth
                label="Location"
                value={formData.location}
                onChange={handleChange('location')}
                error={!!errors.location}
                helperText={errors.location}
                required
                disabled={loading}
              />
            </Grid>

            <Grid item xs={12} md={6}>
              <TextField
                fullWidth
                label="Start Date"
                type="date"
                value={formData.startDate}
                onChange={handleChange('startDate')}
                InputLabelProps={{ shrink: true }}
                disabled={loading}
              />
            </Grid>

            <Grid item xs={12} md={6}>
              <TextField
                fullWidth
                label="Estimated End Date"
                type="date"
                value={formData.estimatedEndDate}
                onChange={handleChange('estimatedEndDate')}
                error={!!errors.estimatedEndDate}
                helperText={errors.estimatedEndDate}
                InputLabelProps={{ shrink: true }}
                disabled={loading}
              />
            </Grid>

            <Grid item xs={12} md={6}>
              <TextField
                fullWidth
                label="Budget"
                value={formData.budget}
                onChange={handleChange('budget')}
                error={!!errors.budget}
                helperText={errors.budget}
                InputProps={{
                  startAdornment: '$'
                }}
                disabled={loading}
              />
            </Grid>

            <Grid item xs={12} md={6}>
              <TextField
                fullWidth
                label="Contractor"
                value={formData.contractor}
                onChange={handleChange('contractor')}
                disabled={loading}
              />
            </Grid>

            <Grid item xs={12}>
              <Box sx={{ display: 'flex', gap: 2, justifyContent: 'flex-end' }}>
                <Button
                  variant="outlined"
                  onClick={onCancel}
                  startIcon={<Cancel />}
                  disabled={loading}
                >
                  Cancel
                </Button>
                <Button
                  type="submit"
                  variant="contained"
                  startIcon={<Save />}
                  disabled={loading}
                >
                  Save Project
                </Button>
              </Box>
            </Grid>
          </Grid>
        </Box>
      </CardContent>
    </Card>
  );
};

export default ProjectForm;
```

### FileUploadZone
Drag-and-drop file upload component with progress tracking.

```javascript
// components/forms/FileUploadZone.js
import React, { useState, useCallback } from 'react';
import {
  Box,
  Typography,
  Button,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  LinearProgress,
  Chip,
  Alert,
  IconButton
} from '@mui/material';
import {
  CloudUpload,
  Image,
  Description,
  Delete,
  CheckCircle,
  Error
} from '@mui/icons-material';

const FileUploadZone = ({
  onFilesSelected,
  acceptedTypes = ["image/*", "application/pdf"],
  maxFileSize = 10 * 1024 * 1024, // 10MB
  maxFiles = 10,
  uploadProgress = {}
}) => {
  const [dragOver, setDragOver] = useState(false);
  const [selectedFiles, setSelectedFiles] = useState([]);
  const [errors, setErrors] = useState([]);

  const validateFile = (file) => {
    const errors = [];

    // Check file size
    if (file.size > maxFileSize) {
      errors.push(`File "${file.name}" is too large. Maximum size is ${maxFileSize / 1024 / 1024}MB`);
    }

    // Check file type
    const isValidType = acceptedTypes.some(type => {
      if (type.includes('*')) {
        const baseType = type.split('/')[0];
        return file.type.startsWith(baseType);
      }
      return file.type === type;
    });

    if (!isValidType) {
      errors.push(`File "${file.name}" type is not supported`);
    }

    return errors;
  };

  const handleFiles = useCallback((files) => {
    const fileList = Array.from(files);
    const newErrors = [];
    const validFiles = [];

    // Check total file count
    if (selectedFiles.length + fileList.length > maxFiles) {
      newErrors.push(`Maximum ${maxFiles} files allowed`);
      setErrors(newErrors);
      return;
    }

    fileList.forEach(file => {
      const fileErrors = validateFile(file);
      if (fileErrors.length > 0) {
        newErrors.push(...fileErrors);
      } else {
        validFiles.push(file);
      }
    });

    if (newErrors.length > 0) {
      setErrors(newErrors);
    } else {
      setErrors([]);
      const updatedFiles = [...selectedFiles, ...validFiles];
      setSelectedFiles(updatedFiles);
      onFilesSelected(updatedFiles);
    }
  }, [selectedFiles, maxFiles, maxFileSize, acceptedTypes, onFilesSelected]);

  const handleDrop = useCallback((event) => {
    event.preventDefault();
    setDragOver(false);

    const files = event.dataTransfer.files;
    handleFiles(files);
  }, [handleFiles]);

  const handleDragOver = useCallback((event) => {
    event.preventDefault();
    setDragOver(true);
  }, []);

  const handleDragLeave = useCallback(() => {
    setDragOver(false);
  }, []);

  const handleFileSelect = (event) => {
    const files = event.target.files;
    handleFiles(files);
  };

  const handleRemoveFile = (index) => {
    const updatedFiles = selectedFiles.filter((_, i) => i !== index);
    setSelectedFiles(updatedFiles);
    onFilesSelected(updatedFiles);
  };

  const getFileIcon = (file) => {
    if (file.type.startsWith('image/')) {
      return <Image color="primary" />;
    } else if (file.type === 'application/pdf') {
      return <Description color="primary" />;
    }
    return <Description />;
  };

  const getUploadStatus = (fileName) => {
    const progress = uploadProgress[fileName];
    if (!progress) return null;

    if (progress.status === 'completed') {
      return <CheckCircle color="success" />;
    } else if (progress.status === 'error') {
      return <Error color="error" />;
    } else {
      return <LinearProgress variant="determinate" value={progress.percentage} sx={{ width: 100 }} />;
    }
  };

  return (
    <Box>
      {/* Upload Zone */}
      <Box
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        sx={{
          border: 2,
          borderColor: dragOver ? 'primary.main' : 'grey.300',
          borderStyle: 'dashed',
          borderRadius: 2,
          p: 4,
          textAlign: 'center',
          cursor: 'pointer',
          backgroundColor: dragOver ? 'primary.50' : 'transparent',
          transition: 'all 0.2s ease-in-out',
          '&:hover': {
            borderColor: 'primary.main',
            backgroundColor: 'primary.50'
          }
        }}
      >
        <input
          type="file"
          multiple
          accept={acceptedTypes.join(',')}
          onChange={handleFileSelect}
          style={{ display: 'none' }}
          id="file-upload-input"
        />

        <label htmlFor="file-upload-input">
          <CloudUpload sx={{ fontSize: 48, color: 'grey.400', mb: 2 }} />
          <Typography variant="h6" gutterBottom>
            Drop files here or click to upload
          </Typography>
          <Typography variant="body2" color="text.secondary" gutterBottom>
            Supports images and PDF documents up to {maxFileSize / 1024 / 1024}MB
          </Typography>
          <Button variant="outlined" component="span" sx={{ mt: 2 }}>
            Select Files
          </Button>
        </label>
      </Box>

      {/* Error Messages */}
      {errors.length > 0 && (
        <Box sx={{ mt: 2 }}>
          {errors.map((error, index) => (
            <Alert key={index} severity="error" sx={{ mb: 1 }}>
              {error}
            </Alert>
          ))}
        </Box>
      )}

      {/* Selected Files List */}
      {selectedFiles.length > 0 && (
        <Box sx={{ mt: 3 }}>
          <Typography variant="h6" gutterBottom>
            Selected Files ({selectedFiles.length})
          </Typography>
          <List>
            {selectedFiles.map((file, index) => (
              <ListItem
                key={index}
                sx={{
                  border: 1,
                  borderColor: 'grey.200',
                  borderRadius: 1,
                  mb: 1
                }}
              >
                <ListItemIcon>
                  {getFileIcon(file)}
                </ListItemIcon>
                <ListItemText
                  primary={file.name}
                  secondary={
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                      <Chip
                        label={`${(file.size / 1024 / 1024).toFixed(2)} MB`}
                        size="small"
                      />
                      {getUploadStatus(file.name)}
                    </Box>
                  }
                />
                <IconButton
                  edge="end"
                  onClick={() => handleRemoveFile(index)}
                  disabled={uploadProgress[file.name]?.status === 'uploading'}
                >
                  <Delete />
                </IconButton>
              </ListItem>
            ))}
          </List>
        </Box>
      )}
    </Box>
  );
};

export default FileUploadZone;
```

## Display Components

### ProjectCard
Card component for displaying project information in lists.

```javascript
// components/display/ProjectCard.js
import React from 'react';
import {
  Card,
  CardContent,
  CardActions,
  Typography,
  Button,
  Chip,
  Box,
  LinearProgress,
  Avatar
} from '@mui/material';
import {
  Visibility,
  Edit,
  LocationOn,
  CalendarToday,
  TrendingUp
} from '@mui/icons-material';

const ProjectCard = ({
  project,
  onView,
  onEdit,
  showProgress = true
}) => {
  const getStatusColor = (status) => {
    switch (status) {
      case 'active':
        return 'success';
      case 'completed':
        return 'primary';
      case 'suspended':
        return 'warning';
      case 'cancelled':
        return 'error';
      default:
        return 'default';
    }
  };

  const formatDate = (dateString) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric'
    });
  };

  return (
    <Card
      sx={{
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
        transition: 'transform 0.2s ease-in-out',
        '&:hover': {
          transform: 'translateY(-2px)',
          boxShadow: 3
        }
      }}
    >
      <CardContent sx={{ flexGrow: 1 }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 2 }}>
          <Typography variant="h6" component="h2" gutterBottom>
            {project.name}
          </Typography>
          <Chip
            label={project.status}
            color={getStatusColor(project.status)}
            size="small"
          />
        </Box>

        {project.description && (
          <Typography
            variant="body2"
            color="text.secondary"
            sx={{
              mb: 2,
              overflow: 'hidden',
              textOverflow: 'ellipsis',
              display: '-webkit-box',
              WebkitLineClamp: 2,
              WebkitBoxOrient: 'vertical'
            }}
          >
            {project.description}
          </Typography>
        )}

        <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
          <LocationOn sx={{ fontSize: 16, mr: 1, color: 'text.secondary' }} />
          <Typography variant="body2" color="text.secondary">
            {project.location}
          </Typography>
        </Box>

        {project.startDate && (
          <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
            <CalendarToday sx={{ fontSize: 16, mr: 1, color: 'text.secondary' }} />
            <Typography variant="body2" color="text.secondary">
              Started: {formatDate(project.startDate)}
            </Typography>
          </Box>
        )}

        {showProgress && project.progress !== undefined && (
          <Box sx={{ mt: 2 }}>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
              <Typography variant="body2" color="text.secondary">
                Progress
              </Typography>
              <Typography variant="body2" color="text.secondary">
                {Math.round(project.progress)}%
              </Typography>
            </Box>
            <LinearProgress
              variant="determinate"
              value={project.progress}
              sx={{ height: 8, borderRadius: 1 }}
            />
          </Box>
        )}

        {project.lastActivity && (
          <Box sx={{ display: 'flex', alignItems: 'center', mt: 2 }}>
            <TrendingUp sx={{ fontSize: 16, mr: 1, color: 'text.secondary' }} />
            <Typography variant="caption" color="text.secondary">
              Last updated: {formatDate(project.lastActivity)}
            </Typography>
          </Box>
        )}
      </CardContent>

      <CardActions>
        <Button
          size="small"
          startIcon={<Visibility />}
          onClick={() => onView(project.id)}
        >
          View
        </Button>
        <Button
          size="small"
          startIcon={<Edit />}
          onClick={() => onEdit(project.id)}
        >
          Edit
        </Button>
      </CardActions>
    </Card>
  );
};

export default ProjectCard;
```

### AnalysisResultCard
Component for displaying AI analysis results.

```javascript
// components/display/AnalysisResultCard.js
import React, { useState } from 'react';
import {
  Card,
  CardContent,
  CardHeader,
  Typography,
  Box,
  Chip,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  Collapse,
  Button,
  LinearProgress
} from '@mui/material';
import {
  ExpandMore,
  ExpandLess,
  CheckCircle,
  Warning,
  Error,
  Info,
  TrendingUp,
  Security,
  Build
} from '@mui/icons-material';

const AnalysisResultCard = ({ analysis, type = 'visual' }) => {
  const [expanded, setExpanded] = useState(false);

  const getProgressColor = (progress) => {
    if (progress >= 80) return 'success';
    if (progress >= 60) return 'info';
    if (progress >= 40) return 'warning';
    return 'error';
  };

  const getSeverityIcon = (severity) => {
    switch (severity) {
      case 'high':
        return <Error color="error" />;
      case 'medium':
        return <Warning color="warning" />;
      case 'low':
        return <Info color="info" />;
      default:
        return <CheckCircle color="success" />;
    }
  };

  const formatTimestamp = (timestamp) => {
    return new Date(timestamp).toLocaleString();
  };

  return (
    <Card>
      <CardHeader
        title={
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
            <Typography variant="h6">
              {type === 'visual' ? 'Visual Analysis' : 'Document Analysis'}
            </Typography>
            <Chip
              label={`${Math.round(analysis.confidence_score * 100)}% confidence`}
              color={analysis.confidence_score > 0.8 ? 'success' : 'warning'}
              size="small"
            />
          </Box>
        }
        subheader={`Analyzed: ${formatTimestamp(analysis.timestamp)}`}
      />

      <CardContent>
        {/* Progress Section (for visual analysis) */}
        {type === 'visual' && analysis.progress_percentage !== undefined && (
          <Box sx={{ mb: 3 }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 1 }}>
              <TrendingUp color="primary" />
              <Typography variant="subtitle1">Project Progress</Typography>
            </Box>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
              <LinearProgress
                variant="determinate"
                value={analysis.progress_percentage}
                color={getProgressColor(analysis.progress_percentage)}
                sx={{ flexGrow: 1, height: 8, borderRadius: 1 }}
              />
              <Typography variant="h6" color="primary">
                {Math.round(analysis.progress_percentage)}%
              </Typography>
            </Box>
          </Box>
        )}

        {/* Detected Elements */}
        {analysis.detected_elements && analysis.detected_elements.length > 0 && (
          <Box sx={{ mb: 3 }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 1 }}>
              <Build color="primary" />
              <Typography variant="subtitle1">Detected Elements</Typography>
            </Box>
            <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
              {analysis.detected_elements.map((element, index) => (
                <Chip
                  key={index}
                  label={element}
                  variant="outlined"
                  size="small"
                />
              ))}
            </Box>
          </Box>
        )}

        {/* Safety Issues */}
        {analysis.safety_issues && analysis.safety_issues.length > 0 && (
          <Box sx={{ mb: 3 }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 1 }}>
              <Security color="error" />
              <Typography variant="subtitle1" color="error">
                Safety Issues ({analysis.safety_issues.length})
              </Typography>
            </Box>
            <List dense>
              {analysis.safety_issues.slice(0, expanded ? undefined : 3).map((issue, index) => (
                <ListItem key={index}>
                  <ListItemIcon>
                    {getSeverityIcon('high')}
                  </ListItemIcon>
                  <ListItemText primary={issue} />
                </ListItem>
              ))}
            </List>
            {analysis.safety_issues.length > 3 && (
              <Button
                size="small"
                onClick={() => setExpanded(!expanded)}
                endIcon={expanded ? <ExpandLess /> : <ExpandMore />}
              >
                {expanded ? 'Show Less' : `Show ${analysis.safety_issues.length - 3} More`}
              </Button>
            )}
          </Box>
        )}

        {/* Quality Observations */}
        {analysis.quality_observations && analysis.quality_observations.length > 0 && (
          <Box sx={{ mb: 3 }}>
            <Typography variant="subtitle1" gutterBottom>
              Quality Observations
            </Typography>
            <List dense>
              {analysis.quality_observations.map((observation, index) => (
                <ListItem key={index}>
                  <ListItemIcon>
                    <CheckCircle color="success" />
                  </ListItemIcon>
                  <ListItemText primary={observation} />
                </ListItem>
              ))}
            </List>
          </Box>
        )}

        {/* Recommendations */}
        {analysis.recommendations && analysis.recommendations.length > 0 && (
          <Box>
            <Typography variant="subtitle1" gutterBottom>
              Recommendations
            </Typography>
            <List dense>
              {analysis.recommendations.map((recommendation, index) => (
                <ListItem key={index}>
                  <ListItemIcon>
                    <Info color="info" />
                  </ListItemIcon>
                  <ListItemText primary={recommendation} />
                </ListItem>
              ))}
            </List>
          </Box>
        )}

        {/* Processing Time */}
        <Box sx={{ mt: 2, pt: 2, borderTop: 1, borderColor: 'divider' }}>
          <Typography variant="caption" color="text.secondary">
            Processing time: {analysis.processing_time || 'N/A'}s
          </Typography>
        </Box>
      </CardContent>
    </Card>
  );
};

export default AnalysisResultCard;
```

## Interactive Components

### ProgressChart
Interactive chart component for visualizing project progress over time.

```javascript
// components/interactive/ProgressChart.js
import React from 'react';
import {
  Box,
  Card,
  CardContent,
  CardHeader,
  Typography,
  FormControl,
  Select,
  MenuItem
} from '@mui/material';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend
} from 'recharts';

const ProgressChart = ({ data, timeRange = '30d', onTimeRangeChange }) => {
  const timeRangeOptions = [
    { value: '7d', label: 'Last 7 days' },
    { value: '30d', label: 'Last 30 days' },
    { value: '90d', label: 'Last 3 months' },
    { value: '1y', label: 'Last year' },
    { value: 'all', label: 'All time' }
  ];

  const formatDate = (dateString) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric'
    });
  };

  const CustomTooltip = ({ active, payload, label }) => {
    if (active && payload && payload.length) {
      return (
        <Card sx={{ p: 2, minWidth: 200 }}>
          <Typography variant="subtitle2" gutterBottom>
            {formatDate(label)}
          </Typography>
          {payload.map((entry, index) => (
            <Typography key={index} variant="body2" color={entry.color}>
              {entry.name}: {entry.value.toFixed(1)}%
            </Typography>
          ))}
        </Card>
      );
    }
    return null;
  };

  return (
    <Card>
      <CardHeader
        title="Project Progress Timeline"
        action={
          <FormControl size="small" sx={{ minWidth: 120 }}>
            <Select
              value={timeRange}
              onChange={(e) => onTimeRangeChange(e.target.value)}
            >
              {timeRangeOptions.map((option) => (
                <MenuItem key={option.value} value={option.value}>
                  {option.label}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
        }
      />
      <CardContent>
        <Box sx={{ width: '100%', height: 300 }}>
          <ResponsiveContainer>
            <LineChart data={data}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis
                dataKey="date"
                tickFormatter={formatDate}
                tick={{ fontSize: 12 }}
              />
              <YAxis
                domain={[0, 100]}
                tick={{ fontSize: 12 }}
                label={{ value: 'Progress (%)', angle: -90, position: 'insideLeft' }}
              />
              <Tooltip content={<CustomTooltip />} />
              <Legend />
              <Line
                type="monotone"
                dataKey="actual"
                stroke="#2196f3"
                strokeWidth={2}
                name="Actual Progress"
                dot={{ r: 4 }}
              />
              <Line
                type="monotone"
                dataKey="planned"
                stroke="#ff9800"
                strokeWidth={2}
                strokeDasharray="5 5"
                name="Planned Progress"
                dot={{ r: 4 }}
              />
            </LineChart>
          </ResponsiveContainer>
        </Box>
      </CardContent>
    </Card>
  );
};

export default ProgressChart;
```

This components documentation provides a comprehensive foundation for building consistent, reusable UI components for the Construction Analysis AI frontend application using Material UI and React best practices.