/**
 * FileBrowser - Component for browsing and managing uploaded files
 * Integrates with MinIO storage and file metadata
 */

import React, { useState, useEffect, useCallback } from 'react';
import {
  Box,
  Paper,
  Typography,
  IconButton,
  Button,
  Grid,
  Card,
  CardContent,
  CardMedia,
  Chip,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Menu,
  MenuItem,
  Tooltip,
  Alert,
  Skeleton,
  Pagination,
  FormControl,
  InputLabel,
  Select,
  InputAdornment
} from '@mui/material';
import {
  Download,
  Delete,
  Visibility,
  MoreVert,
  Search,
  FilterList,
  GridView,
  ViewList,
  Image,
  PictureAsPdf,
  Description,
  InsertDriveFile,
  Tag,
  Share,
  Info,
  Optimize
} from '@mui/icons-material';
import { styled } from '@mui/material/styles';
import { format } from 'date-fns';
import { ptBR } from 'date-fns/locale';
import axios from 'axios';

const FileCard = styled(Card)(({ theme, viewMode }) => ({
  height: viewMode === 'grid' ? 280 : 'auto',
  cursor: 'pointer',
  transition: 'all 0.2s ease-in-out',
  '&:hover': {
    transform: viewMode === 'grid' ? 'translateY(-2px)' : 'none',
    boxShadow: theme.shadows[4],
  }
}));

const FilePreview = styled(Box)(({ theme }) => ({
  width: '100%',
  height: 160,
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  backgroundColor: theme.palette.grey[100],
  position: 'relative',
  overflow: 'hidden'
}));

const FileBrowser = ({
  projectId,
  onFileSelect,
  onFileDelete,
  allowDownload = true,
  allowDelete = true,
  allowOptimize = true,
  categories = [],
  initialView = 'grid'
}) => {
  const [files, setFiles] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedFile, setSelectedFile] = useState(null);
  const [viewMode, setViewMode] = useState(initialView);
  const [searchTerm, setSearchTerm] = useState('');
  const [categoryFilter, setCategoryFilter] = useState('');
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [contextMenu, setContextMenu] = useState(null);
  const [detailsDialog, setDetailsDialog] = useState(false);
  const [deleteDialog, setDeleteDialog] = useState(false);
  const [fileToDelete, setFileToDelete] = useState(null);

  const filesPerPage = 20;

  const getFileIcon = (mimeType, size = 'large') => {
    const iconProps = {
      fontSize: size,
      color: 'action'
    };

    if (mimeType.startsWith('image/')) {
      return <Image {...iconProps} color="primary" />;
    }
    if (mimeType === 'application/pdf') {
      return <PictureAsPdf {...iconProps} color="error" />;
    }
    if (mimeType.includes('word') || mimeType.includes('document')) {
      return <Description {...iconProps} color="info" />;
    }
    if (mimeType.includes('spreadsheet') || mimeType.includes('excel')) {
      return <Description {...iconProps} color="success" />;
    }

    return <InsertDriveFile {...iconProps} />;
  };

  const formatFileSize = (bytes) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const getCategoryColor = (category) => {
    const colors = {
      general: 'default',
      construction: 'primary',
      bim: 'secondary',
      document: 'info',
      image: 'success',
      report: 'warning'
    };
    return colors[category] || 'default';
  };

  const loadFiles = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      const params = new URLSearchParams({
        limit: filesPerPage.toString(),
        skip: ((page - 1) * filesPerPage).toString()
      });

      if (categoryFilter) {
        params.append('category', categoryFilter);
      }

      const response = await axios.get(`/api/storage/project/${projectId}/files?${params}`);

      let filesList = response.data.files || [];

      // Filtrar por termo de busca no frontend
      if (searchTerm) {
        filesList = filesList.filter(file =>
          file.original_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
          file.tags.some(tag => tag.toLowerCase().includes(searchTerm.toLowerCase()))
        );
      }

      setFiles(filesList);
      setTotalPages(Math.ceil(response.data.total / filesPerPage));

    } catch (err) {
      console.error('Error loading files:', err);
      setError('Erro ao carregar arquivos');
    } finally {
      setLoading(false);
    }
  }, [projectId, page, categoryFilter, searchTerm]);

  useEffect(() => {
    if (projectId) {
      loadFiles();
    }
  }, [projectId, loadFiles]);

  const handleFileClick = (file) => {
    setSelectedFile(file);
    if (onFileSelect) {
      onFileSelect(file);
    }
  };

  const handleContextMenu = (event, file) => {
    event.preventDefault();
    setContextMenu({
      mouseX: event.clientX - 2,
      mouseY: event.clientY - 4,
      file
    });
  };

  const closeContextMenu = () => {
    setContextMenu(null);
  };

  const handleDownload = async (file) => {
    try {
      const response = await axios.get(`/api/storage/download/${file.file_id}`, {
        responseType: 'blob'
      });

      // Criar URL temporária para download
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', file.original_name);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);

    } catch (err) {
      console.error('Download error:', err);
      setError('Erro ao fazer download do arquivo');
    }

    closeContextMenu();
  };

  const handleDeleteClick = (file) => {
    setFileToDelete(file);
    setDeleteDialog(true);
    closeContextMenu();
  };

  const handleDeleteConfirm = async () => {
    if (!fileToDelete) return;

    try {
      await axios.delete(`/api/storage/file/${fileToDelete.file_id}`);

      // Remover arquivo da lista
      setFiles(prev => prev.filter(f => f.file_id !== fileToDelete.file_id));

      if (onFileDelete) {
        onFileDelete(fileToDelete);
      }

      setDeleteDialog(false);
      setFileToDelete(null);

    } catch (err) {
      console.error('Delete error:', err);
      setError('Erro ao deletar arquivo');
    }
  };

  const handleOptimize = async (file) => {
    if (!file.mime_type.startsWith('image/')) return;

    try {
      await axios.post(`/api/storage/optimize/${file.file_id}`, {
        max_width: 2048,
        quality: 85
      });

      // Recarregar lista para mostrar arquivo otimizado
      loadFiles();

    } catch (err) {
      console.error('Optimize error:', err);
      setError('Erro ao otimizar imagem');
    }

    closeContextMenu();
  };

  const showFileDetails = (file) => {
    setSelectedFile(file);
    setDetailsDialog(true);
    closeContextMenu();
  };

  const renderFileCard = (file) => (
    <FileCard
      key={file.file_id}
      viewMode={viewMode}
      onClick={() => handleFileClick(file)}
      onContextMenu={(e) => handleContextMenu(e, file)}
    >
      {viewMode === 'grid' ? (
        <>
          <FilePreview>
            {file.thumbnails?.medium ? (
              <CardMedia
                component="img"
                sx={{ width: '100%', height: '100%', objectFit: 'cover' }}
                image={`/api/storage/download/${file.file_id}?thumbnail=medium`}
                alt={file.original_name}
              />
            ) : (
              getFileIcon(file.mime_type, 64)
            )}
          </FilePreview>

          <CardContent sx={{ p: 1.5 }}>
            <Typography variant="subtitle2" noWrap title={file.original_name}>
              {file.original_name}
            </Typography>

            <Typography variant="caption" color="text.secondary" display="block">
              {formatFileSize(file.size_bytes)}
            </Typography>

            <Box display="flex" gap={0.5} mt={1} flexWrap="wrap">
              <Chip
                label={file.category}
                size="small"
                color={getCategoryColor(file.category)}
              />

              {file.tags?.slice(0, 2).map(tag => (
                <Chip key={tag} label={tag} size="small" variant="outlined" />
              ))}
            </Box>
          </CardContent>
        </>
      ) : (
        <CardContent>
          <Grid container spacing={2} alignItems="center">
            <Grid item xs="auto">
              {getFileIcon(file.mime_type)}
            </Grid>

            <Grid item xs>
              <Typography variant="subtitle2" noWrap>
                {file.original_name}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                {formatFileSize(file.size_bytes)} • {format(new Date(file.created_at), 'dd/MM/yyyy', { locale: ptBR })}
              </Typography>
            </Grid>

            <Grid item xs="auto">
              <Chip
                label={file.category}
                size="small"
                color={getCategoryColor(file.category)}
              />
            </Grid>

            <Grid item xs="auto">
              <IconButton size="small" onClick={(e) => handleContextMenu(e, file)}>
                <MoreVert />
              </IconButton>
            </Grid>
          </Grid>
        </CardContent>
      )}
    </FileCard>
  );

  return (
    <Box>
      {/* Header with Controls */}
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Typography variant="h6">
          Arquivos do Projeto
        </Typography>

        <Box display="flex" gap={1} alignItems="center">
          <TextField
            size="small"
            placeholder="Buscar arquivos..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            InputProps={{
              startAdornment: (
                <InputAdornment position="start">
                  <Search />
                </InputAdornment>
              )
            }}
            sx={{ width: 250 }}
          />

          <FormControl size="small" sx={{ minWidth: 120 }}>
            <InputLabel>Categoria</InputLabel>
            <Select
              value={categoryFilter}
              onChange={(e) => setCategoryFilter(e.target.value)}
              label="Categoria"
            >
              <MenuItem value="">Todas</MenuItem>
              <MenuItem value="general">Geral</MenuItem>
              <MenuItem value="construction">Construção</MenuItem>
              <MenuItem value="bim">BIM</MenuItem>
              <MenuItem value="document">Documento</MenuItem>
              <MenuItem value="image">Imagem</MenuItem>
              <MenuItem value="report">Relatório</MenuItem>
            </Select>
          </FormControl>

          <IconButton
            onClick={() => setViewMode(viewMode === 'grid' ? 'list' : 'grid')}
            title={`Alternar para ${viewMode === 'grid' ? 'lista' : 'grade'}`}
          >
            {viewMode === 'grid' ? <ViewList /> : <GridView />}
          </IconButton>
        </Box>
      </Box>

      {/* Error Display */}
      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      {/* Files Grid/List */}
      {loading ? (
        <Grid container spacing={2}>
          {Array.from({ length: 8 }).map((_, index) => (
            <Grid item xs={viewMode === 'grid' ? 6 : 12} sm={viewMode === 'grid' ? 4 : 12} md={viewMode === 'grid' ? 3 : 12} key={index}>
              <Skeleton variant="rectangular" height={viewMode === 'grid' ? 280 : 80} />
            </Grid>
          ))}
        </Grid>
      ) : files.length === 0 ? (
        <Paper sx={{ p: 4, textAlign: 'center' }}>
          <InsertDriveFile sx={{ fontSize: 64, color: 'text.secondary' }} />
          <Typography variant="h6" color="text.secondary" mt={2}>
            Nenhum arquivo encontrado
          </Typography>
          <Typography variant="body2" color="text.secondary">
            {searchTerm || categoryFilter
              ? 'Tente ajustar os filtros de busca'
              : 'Faça upload de arquivos para começar'
            }
          </Typography>
        </Paper>
      ) : (
        <Grid container spacing={2}>
          {files.map(file => (
            <Grid item xs={viewMode === 'grid' ? 6 : 12} sm={viewMode === 'grid' ? 4 : 12} md={viewMode === 'grid' ? 3 : 12} key={file.file_id}>
              {renderFileCard(file)}
            </Grid>
          ))}
        </Grid>
      )}

      {/* Pagination */}
      {totalPages > 1 && (
        <Box display="flex" justifyContent="center" mt={3}>
          <Pagination
            count={totalPages}
            page={page}
            onChange={(_, newPage) => setPage(newPage)}
            color="primary"
          />
        </Box>
      )}

      {/* Context Menu */}
      <Menu
        open={contextMenu !== null}
        onClose={closeContextMenu}
        anchorReference="anchorPosition"
        anchorPosition={
          contextMenu !== null
            ? { top: contextMenu.mouseY, left: contextMenu.mouseX }
            : undefined
        }
      >
        <MenuItem onClick={() => showFileDetails(contextMenu?.file)}>
          <Info sx={{ mr: 1 }} />
          Detalhes
        </MenuItem>

        {allowDownload && (
          <MenuItem onClick={() => handleDownload(contextMenu?.file)}>
            <Download sx={{ mr: 1 }} />
            Download
          </MenuItem>
        )}

        {allowOptimize && contextMenu?.file?.mime_type.startsWith('image/') && (
          <MenuItem onClick={() => handleOptimize(contextMenu?.file)}>
            <Optimize sx={{ mr: 1 }} />
            Otimizar
          </MenuItem>
        )}

        {allowDelete && (
          <MenuItem onClick={() => handleDeleteClick(contextMenu?.file)} sx={{ color: 'error.main' }}>
            <Delete sx={{ mr: 1 }} />
            Deletar
          </MenuItem>
        )}
      </Menu>

      {/* File Details Dialog */}
      <Dialog open={detailsDialog} onClose={() => setDetailsDialog(false)} maxWidth="md" fullWidth>
        <DialogTitle>Detalhes do Arquivo</DialogTitle>
        <DialogContent>
          {selectedFile && (
            <Grid container spacing={2}>
              <Grid item xs={12} md={4}>
                <Box textAlign="center">
                  {selectedFile.thumbnails?.large ? (
                    <img
                      src={`/api/storage/download/${selectedFile.file_id}?thumbnail=large`}
                      alt={selectedFile.original_name}
                      style={{ maxWidth: '100%', maxHeight: 200 }}
                    />
                  ) : (
                    getFileIcon(selectedFile.mime_type, 120)
                  )}
                </Box>
              </Grid>

              <Grid item xs={12} md={8}>
                <Typography variant="h6" gutterBottom>{selectedFile.original_name}</Typography>

                <Typography variant="body2" paragraph>
                  <strong>Tamanho:</strong> {formatFileSize(selectedFile.size_bytes)}
                </Typography>

                <Typography variant="body2" paragraph>
                  <strong>Tipo:</strong> {selectedFile.mime_type}
                </Typography>

                <Typography variant="body2" paragraph>
                  <strong>Categoria:</strong> {selectedFile.category}
                </Typography>

                <Typography variant="body2" paragraph>
                  <strong>Criado em:</strong> {format(new Date(selectedFile.created_at), 'dd/MM/yyyy HH:mm', { locale: ptBR })}
                </Typography>

                {selectedFile.dimensions && (
                  <Typography variant="body2" paragraph>
                    <strong>Dimensões:</strong> {selectedFile.dimensions.width} × {selectedFile.dimensions.height} pixels
                  </Typography>
                )}

                {selectedFile.tags?.length > 0 && (
                  <Box>
                    <Typography variant="body2" gutterBottom><strong>Tags:</strong></Typography>
                    <Box display="flex" gap={0.5} flexWrap="wrap">
                      {selectedFile.tags.map(tag => (
                        <Chip key={tag} label={tag} size="small" />
                      ))}
                    </Box>
                  </Box>
                )}
              </Grid>
            </Grid>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDetailsDialog(false)}>Fechar</Button>
        </DialogActions>
      </Dialog>

      {/* Delete Confirmation Dialog */}
      <Dialog open={deleteDialog} onClose={() => setDeleteDialog(false)}>
        <DialogTitle>Confirmar Exclusão</DialogTitle>
        <DialogContent>
          <Typography>
            Tem certeza que deseja excluir o arquivo <strong>{fileToDelete?.original_name}</strong>?
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
            Esta ação não pode ser desfeita.
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDeleteDialog(false)}>Cancelar</Button>
          <Button onClick={handleDeleteConfirm} color="error" variant="contained">
            Excluir
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default FileBrowser;