/**
 * FileUpload - Advanced file upload component with MinIO integration
 * Supports drag-drop, progress tracking, and validation
 */

import React, { useState, useCallback, useRef } from 'react';
import {
  Box,
  Paper,
  Typography,
  IconButton,
  LinearProgress,
  Chip,
  Alert,
  Button,
  Grid,
  Card,
  CardContent,
  Tooltip,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Select,
  MenuItem,
  FormControl,
  InputLabel
} from '@mui/material';
import {
  CloudUpload,
  Delete,
  InsertDriveFile,
  Image,
  PictureAsPdf,
  Description,
  Close,
  CheckCircle,
  Error,
  Refresh
} from '@mui/icons-material';
import { useDropzone } from 'react-dropzone';
import { styled } from '@mui/material/styles';
import axios from 'axios';
import API_BASE_URL from '../../config/api';

const DropzoneContainer = styled(Paper)(({ theme, isDragActive, hasError }) => ({
  padding: theme.spacing(4),
  textAlign: 'center',
  border: `2px dashed ${isDragActive ? theme.palette.primary.main : theme.palette.divider}`,
  backgroundColor: isDragActive
    ? theme.palette.primary.light + '10'
    : hasError
    ? theme.palette.error.light + '10'
    : theme.palette.background.default,
  cursor: 'pointer',
  transition: 'all 0.3s ease',
  minHeight: 200,
  display: 'flex',
  flexDirection: 'column',
  alignItems: 'center',
  justifyContent: 'center',
  '&:hover': {
    backgroundColor: theme.palette.action.hover,
    borderColor: theme.palette.primary.main,
  }
}));

const FilePreviewCard = styled(Card)(({ theme }) => ({
  marginBottom: theme.spacing(1),
  '& .upload-progress': {
    width: '100%',
    marginTop: theme.spacing(1)
  }
}));

const FileUpload = ({
  projectId,
  category = 'general',
  maxFiles = 10,
  maxSize = 50 * 1024 * 1024, // 50MB
  acceptedTypes = {
    'image/*': ['.jpeg', '.jpg', '.png', '.gif', '.bmp', '.webp'],
    'application/pdf': ['.pdf'],
    'application/msword': ['.doc'],
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
    'application/vnd.ms-excel': ['.xls'],
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx'],
    'text/plain': ['.txt'],
    'text/csv': ['.csv'],
    'application/json': ['.json']
  },
  onUploadComplete,
  onUploadError,
  disabled = false
}) => {
  const [files, setFiles] = useState([]);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState({});
  const [errors, setErrors] = useState([]);
  const [quotaInfo, setQuotaInfo] = useState(null);
  const [showQuotaDialog, setShowQuotaDialog] = useState(false);
  const [selectedCategory, setSelectedCategory] = useState(category);

  const abortControllers = useRef({});

  const categories = [
    { value: 'general', label: 'Geral' },
    { value: 'construction', label: 'Construção' },
    { value: 'bim', label: 'BIM' },
    { value: 'document', label: 'Documento' },
    { value: 'image', label: 'Imagem' },
    { value: 'report', label: 'Relatório' }
  ];

  const getFileIcon = (type) => {
    if (type.startsWith('image/')) return <Image color="primary" />;
    if (type === 'application/pdf') return <PictureAsPdf color="error" />;
    if (type.includes('word') || type.includes('document')) return <Description color="info" />;
    return <InsertDriveFile color="action" />;
  };

  const formatFileSize = (bytes) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const validateFile = (file) => {
    const errors = [];

    // Verificar tamanho
    if (file.size > maxSize) {
      errors.push(`Arquivo muito grande (máximo ${formatFileSize(maxSize)})`);
    }

    // Verificar tipo
    const isAccepted = Object.keys(acceptedTypes).some(acceptedType => {
      return file.type.match(acceptedType) ||
             acceptedTypes[acceptedType].some(ext => file.name.toLowerCase().endsWith(ext));
    });

    if (!isAccepted) {
      errors.push('Tipo de arquivo não suportado');
    }

    return errors;
  };

  const onDrop = useCallback((acceptedFiles, rejectedFiles) => {
    setErrors([]);

    // Processar arquivos rejeitados
    if (rejectedFiles.length > 0) {
      const rejectionErrors = rejectedFiles.map(({ file, errors }) =>
        `${file.name}: ${errors.map(e => e.message).join(', ')}`
      );
      setErrors(rejectionErrors);
    }

    // Processar arquivos aceitos
    const newFiles = acceptedFiles.map(file => {
      const validationErrors = validateFile(file);
      return {
        id: Math.random().toString(36).substr(2, 9),
        file,
        preview: file.type.startsWith('image/') ? URL.createObjectURL(file) : null,
        status: validationErrors.length > 0 ? 'error' : 'pending',
        errors: validationErrors,
        progress: 0
      };
    });

    // Verificar limite de arquivos
    const totalFiles = files.length + newFiles.length;
    if (totalFiles > maxFiles) {
      setErrors(prev => [...prev, `Máximo ${maxFiles} arquivos permitidos`]);
      return;
    }

    setFiles(prev => [...prev, ...newFiles.filter(f => f.status !== 'error')]);

    // Mostrar erros de validação
    const fileErrors = newFiles
      .filter(f => f.status === 'error')
      .map(f => `${f.file.name}: ${f.errors.join(', ')}`);

    if (fileErrors.length > 0) {
      setErrors(prev => [...prev, ...fileErrors]);
    }
  }, [files, maxFiles, maxSize, acceptedTypes]);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: acceptedTypes,
    maxSize,
    maxFiles,
    disabled: disabled || uploading
  });

  const removeFile = (fileId) => {
    // Cancelar upload se estiver em progresso
    if (abortControllers.current[fileId]) {
      abortControllers.current[fileId].abort();
      delete abortControllers.current[fileId];
    }

    setFiles(prev => prev.filter(f => f.id !== fileId));
    setUploadProgress(prev => {
      const newProgress = { ...prev };
      delete newProgress[fileId];
      return newProgress;
    });
  };

  const clearFiles = () => {
    // Cancelar todos os uploads
    Object.values(abortControllers.current).forEach(controller => {
      controller.abort();
    });
    abortControllers.current = {};

    setFiles([]);
    setUploadProgress({});
    setErrors([]);
  };

  const uploadFile = async (fileData) => {
    const controller = new AbortController();
    abortControllers.current[fileData.id] = controller;

    const formData = new FormData();
    formData.append('file', fileData.file);
    formData.append('project_id', projectId);
    formData.append('category', selectedCategory);

    try {
      const response = await axios.post(`${API_BASE_URL}/storage/upload`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
        signal: controller.signal,
        onUploadProgress: (progressEvent) => {
          const percentCompleted = Math.round(
            (progressEvent.loaded * 100) / progressEvent.total
          );
          setUploadProgress(prev => ({
            ...prev,
            [fileData.id]: percentCompleted
          }));
        },
      });

      // Atualizar status do arquivo
      setFiles(prev => prev.map(f =>
        f.id === fileData.id
          ? { ...f, status: 'completed', response: response.data }
          : f
      ));

      delete abortControllers.current[fileData.id];
      return response.data;

    } catch (error) {
      delete abortControllers.current[fileData.id];

      if (error.name === 'AbortError') {
        // Upload cancelado
        return null;
      }

      // Erro no upload
      setFiles(prev => prev.map(f =>
        f.id === fileData.id
          ? { ...f, status: 'error', errors: [error.response?.data?.detail || error.message] }
          : f
      ));

      throw error;
    }
  };

  const uploadAllFiles = async () => {
    if (files.length === 0) return;

    setUploading(true);
    setErrors([]);

    const pendingFiles = files.filter(f => f.status === 'pending');
    const results = [];
    const uploadErrors = [];

    try {
      // Upload em paralelo com limite de 3 arquivos simultâneos
      const chunks = [];
      for (let i = 0; i < pendingFiles.length; i += 3) {
        chunks.push(pendingFiles.slice(i, i + 3));
      }

      for (const chunk of chunks) {
        const chunkPromises = chunk.map(async (fileData) => {
          try {
            const result = await uploadFile(fileData);
            if (result) {
              results.push(result);
            }
          } catch (error) {
            uploadErrors.push(`${fileData.file.name}: ${error.message}`);
          }
        });

        await Promise.all(chunkPromises);
      }

      // Verificar quota após upload
      await checkQuota();

      // Callback de sucesso
      if (onUploadComplete && results.length > 0) {
        onUploadComplete(results);
      }

      // Callback de erro
      if (onUploadError && uploadErrors.length > 0) {
        onUploadError(uploadErrors);
        setErrors(uploadErrors);
      }

    } catch (error) {
      console.error('Upload error:', error);
      setErrors([error.message]);
    } finally {
      setUploading(false);
    }
  };

  const checkQuota = async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/storage/quota`);
      setQuotaInfo(response.data);

      if (response.data.is_over_limit || response.data.is_near_limit) {
        setShowQuotaDialog(true);
      }
    } catch (error) {
      console.error('Error checking quota:', error);
    }
  };

  const retryFailedUploads = () => {
    setFiles(prev => prev.map(f =>
      f.status === 'error'
        ? { ...f, status: 'pending', errors: [] }
        : f
    ));
    setErrors([]);
  };

  React.useEffect(() => {
    checkQuota();
  }, []);

  const pendingCount = files.filter(f => f.status === 'pending').length;
  const completedCount = files.filter(f => f.status === 'completed').length;
  const errorCount = files.filter(f => f.status === 'error').length;

  return (
    <Box>
      {/* Quota Warning Dialog */}
      <Dialog open={showQuotaDialog} onClose={() => setShowQuotaDialog(false)}>
        <DialogTitle>Aviso de Quota</DialogTitle>
        <DialogContent>
          <Typography paragraph>
            {quotaInfo?.is_over_limit
              ? 'Sua quota de armazenamento foi excedida.'
              : 'Você está próximo do limite de armazenamento.'
            }
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Usado: {quotaInfo ? formatFileSize(quotaInfo.used_bytes) : '0'} / {quotaInfo ? formatFileSize(quotaInfo.quota_bytes) : '0'}
            ({quotaInfo?.usage_percentage.toFixed(1)}%)
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setShowQuotaDialog(false)}>Fechar</Button>
        </DialogActions>
      </Dialog>

      {/* Category Selection */}
      <Box mb={2}>
        <FormControl size="small" sx={{ minWidth: 200 }}>
          <InputLabel>Categoria</InputLabel>
          <Select
            value={selectedCategory}
            onChange={(e) => setSelectedCategory(e.target.value)}
            label="Categoria"
            disabled={uploading}
          >
            {categories.map(cat => (
              <MenuItem key={cat.value} value={cat.value}>
                {cat.label}
              </MenuItem>
            ))}
          </Select>
        </FormControl>
      </Box>

      {/* Upload Zone */}
      <DropzoneContainer
        {...getRootProps()}
        isDragActive={isDragActive}
        hasError={errors.length > 0}
        elevation={isDragActive ? 4 : 1}
      >
        <input {...getInputProps()} />
        <CloudUpload sx={{ fontSize: 48, color: 'text.secondary', mb: 2 }} />
        <Typography variant="h6" gutterBottom>
          {isDragActive
            ? 'Solte os arquivos aqui...'
            : 'Arraste arquivos ou clique para selecionar'
          }
        </Typography>
        <Typography variant="body2" color="text.secondary">
          Máximo {maxFiles} arquivos, {formatFileSize(maxSize)} cada
        </Typography>
        <Typography variant="caption" color="text.secondary" sx={{ mt: 1 }}>
          Tipos suportados: Imagens, PDF, Word, Excel, TXT, CSV, JSON
        </Typography>
      </DropzoneContainer>

      {/* Error Messages */}
      {errors.length > 0 && (
        <Box mt={2}>
          {errors.map((error, index) => (
            <Alert key={index} severity="error" sx={{ mb: 1 }}>
              {error}
            </Alert>
          ))}
        </Box>
      )}

      {/* File List */}
      {files.length > 0 && (
        <Box mt={3}>
          <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
            <Typography variant="h6">
              Arquivos ({files.length})
            </Typography>
            <Box>
              {errorCount > 0 && (
                <Button
                  startIcon={<Refresh />}
                  onClick={retryFailedUploads}
                  size="small"
                  sx={{ mr: 1 }}
                >
                  Tentar Novamente
                </Button>
              )}
              <Button
                startIcon={<Delete />}
                onClick={clearFiles}
                disabled={uploading}
                size="small"
                color="error"
              >
                Limpar
              </Button>
            </Box>
          </Box>

          {files.map((fileData) => (
            <FilePreviewCard key={fileData.id} variant="outlined">
              <CardContent sx={{ p: 2, '&:last-child': { pb: 2 } }}>
                <Grid container spacing={2} alignItems="center">
                  <Grid item xs="auto">
                    {getFileIcon(fileData.file.type)}
                  </Grid>

                  <Grid item xs>
                    <Typography variant="subtitle2" noWrap>
                      {fileData.file.name}
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      {formatFileSize(fileData.file.size)}
                    </Typography>
                  </Grid>

                  <Grid item xs="auto">
                    {fileData.status === 'pending' && (
                      <Chip label="Pendente" size="small" />
                    )}
                    {fileData.status === 'completed' && (
                      <Chip
                        icon={<CheckCircle />}
                        label="Concluído"
                        size="small"
                        color="success"
                      />
                    )}
                    {fileData.status === 'error' && (
                      <Chip
                        icon={<Error />}
                        label="Erro"
                        size="small"
                        color="error"
                      />
                    )}
                  </Grid>

                  <Grid item xs="auto">
                    <Tooltip title="Remover arquivo">
                      <IconButton
                        size="small"
                        onClick={() => removeFile(fileData.id)}
                        disabled={uploading && fileData.status !== 'error'}
                      >
                        <Close />
                      </IconButton>
                    </Tooltip>
                  </Grid>
                </Grid>

                {/* Progress Bar */}
                {uploadProgress[fileData.id] !== undefined && (
                  <LinearProgress
                    variant="determinate"
                    value={uploadProgress[fileData.id]}
                    className="upload-progress"
                    sx={{ mt: 1 }}
                  />
                )}

                {/* Error Messages */}
                {fileData.errors && fileData.errors.length > 0 && (
                  <Box mt={1}>
                    {fileData.errors.map((error, index) => (
                      <Typography key={index} variant="caption" color="error">
                        {error}
                      </Typography>
                    ))}
                  </Box>
                )}
              </CardContent>
            </FilePreviewCard>
          ))}

          {/* Upload Button */}
          {pendingCount > 0 && (
            <Box mt={2} textAlign="center">
              <Button
                variant="contained"
                size="large"
                startIcon={<CloudUpload />}
                onClick={uploadAllFiles}
                disabled={uploading || disabled}
                sx={{ minWidth: 200 }}
              >
                {uploading
                  ? `Enviando... (${completedCount}/${pendingCount + completedCount})`
                  : `Enviar ${pendingCount} arquivo${pendingCount > 1 ? 's' : ''}`
                }
              </Button>
            </Box>
          )}

          {/* Summary */}
          {(completedCount > 0 || errorCount > 0) && (
            <Box mt={2}>
              <Alert severity={errorCount > 0 ? "warning" : "success"}>
                {completedCount > 0 && `${completedCount} arquivo(s) enviado(s) com sucesso. `}
                {errorCount > 0 && `${errorCount} arquivo(s) com erro.`}
              </Alert>
            </Box>
          )}
        </Box>
      )}

      {/* Quota Information */}
      {quotaInfo && (
        <Box mt={3}>
          <Typography variant="caption" color="text.secondary">
            Armazenamento: {formatFileSize(quotaInfo.used_bytes)} / {formatFileSize(quotaInfo.quota_bytes)}
            ({quotaInfo.usage_percentage.toFixed(1)}%)
          </Typography>
          <LinearProgress
            variant="determinate"
            value={quotaInfo.usage_percentage}
            sx={{ mt: 0.5 }}
            color={quotaInfo.is_over_limit ? "error" : quotaInfo.is_near_limit ? "warning" : "primary"}
          />
        </Box>
      )}
    </Box>
  );
};

export default FileUpload;