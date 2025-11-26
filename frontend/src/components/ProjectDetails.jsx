import React, { useState, useEffect, useCallback } from 'react';
import {
  Box,
  Container,
  Paper,
  Typography,
  Tabs,
  Tab,
  Grid,
  Card,
  CardContent,
  CardMedia,
  Chip,
  LinearProgress,
  CircularProgress,
  Button,
  IconButton,
  Dialog,
  DialogContent,
  Divider,
  List,
  ListItem,
  ListItemText,
  Alert
} from '@mui/material';
import {
  ArrowBack,
  LocationOn,
  CalendarToday,
  TrendingUp,
  Image as ImageIcon,
  Assessment,
  Timeline,
  Construction,
  Close as CloseIcon,
  Refresh,
  TrendingDown,
  Remove as RemoveIcon,
  Info as InfoIcon
} from '@mui/icons-material';
import { useNavigate, useParams } from 'react-router-dom';
import { format, parseISO } from 'date-fns';
import { toZonedTime } from 'date-fns-tz';
import { ptBR } from 'date-fns/locale';
import axios from 'axios';
import toast from 'react-hot-toast';
import ProjectTimelineTab from './ProjectTimelineTab';
import API_BASE_URL from '../config/api';

// Helper para formatar datas no horário de Brasília (UTC-3)
const formatBrazilDate = (dateString, formatStr = "dd/MM/yyyy HH:mm") => {
  if (!dateString) return 'Data não disponível';
  try {
    const date = parseISO(dateString);
    // Converte para timezone de Brasília (America/Sao_Paulo)
    const brazilDate = toZonedTime(date, 'America/Sao_Paulo');
    return format(brazilDate, formatStr, { locale: ptBR });
  } catch (error) {
    console.error('Error formatting date:', error);
    return 'Data inválida';
  }
};

const ProjectDetails = () => {
  const navigate = useNavigate();
  const { projectId } = useParams();
  const [tabValue, setTabValue] = useState(0);
  const [project, setProject] = useState(null);
  const [timeline, setTimeline] = useState(null);
  const [images, setImages] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedImage, setSelectedImage] = useState(null);
  const [imageDialogOpen, setImageDialogOpen] = useState(false);

  // Buscar dados do projeto
  const fetchProjectData = useCallback(async () => {
    try {
      setLoading(true);

      // Busca informações do projeto
      try {
        const projectRes = await axios.get(`${API_BASE_URL}/projects/${projectId}`);
        setProject(projectRes.data);
      } catch (error) {
        console.error('Erro ao buscar projeto:', error);
        toast.error('Erro ao carregar informações da obra');
        return;
      }

      // Busca timeline do projeto (não bloqueia se falhar)
      try {
        const timelineRes = await axios.get(`${API_BASE_URL}/timeline/summary`, {
          params: { project_id: projectId }
        });
        setTimeline(timelineRes.data);
      } catch (error) {
        console.warn('Timeline não disponível:', error);
        setTimeline({ total_images: 0, total_months: 0, periods: [] });
      }

      // Busca imagens do projeto com análises
      try {
        const imagesRes = await axios.get(`${API_BASE_URL}/projects/${projectId}/images`, {
          params: { limit: 50 }
        });
        setImages(imagesRes.data.images || []);
      } catch (error) {
        console.warn('Imagens não disponíveis:', error);
        setImages([]);
      }

    } catch (error) {
      console.error('Erro geral ao buscar dados:', error);
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  useEffect(() => {
    if (projectId) {
      fetchProjectData();
    }
  }, [projectId, fetchProjectData]);

  const handleTabChange = (event, newValue) => {
    setTabValue(newValue);
  };

  const handleImageClick = (image) => {
    setSelectedImage(image);
    setImageDialogOpen(true);
  };

  const handleCloseImageDialog = () => {
    setImageDialogOpen(false);
    setSelectedImage(null);
  };

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="60vh">
        <CircularProgress />
      </Box>
    );
  }

  if (!project) {
    return (
      <Container maxWidth="xl" sx={{ mt: 4 }}>
        <Alert severity="error">Obra não encontrada</Alert>
      </Container>
    );
  }

  return (
    <Container maxWidth="xl" sx={{ mt: 4, mb: 4 }}>
      {/* Header */}
      <Box mb={3}>
        <Button
          startIcon={<ArrowBack />}
          onClick={() => navigate('/projects')}
          sx={{ mb: 2 }}
        >
          Voltar para Obras
        </Button>

        <Box display="flex" justifyContent="space-between" alignItems="start">
          <Box>
            <Typography variant="h4" gutterBottom sx={{ fontWeight: 600 }}>
              {project.name}
            </Typography>
            <Box display="flex" gap={2} alignItems="center" flexWrap="wrap">
              <Box display="flex" alignItems="center" gap={0.5}>
                <LocationOn fontSize="small" color="action" />
                <Typography variant="body2" color="text.secondary">
                  {project.location?.address || 'Endereço não informado'}
                </Typography>
              </Box>
              <Box display="flex" alignItems="center" gap={0.5}>
                <CalendarToday fontSize="small" color="action" />
                <Typography variant="body2" color="text.secondary">
                  Criado em {formatBrazilDate(project.created_at, "dd/MM/yyyy")}
                </Typography>
              </Box>
              <Chip
                label={`${project.overall_progress || 0}% concluído`}
                color="primary"
                icon={<TrendingUp />}
              />
            </Box>
          </Box>
          <Button
            variant="outlined"
            startIcon={<Refresh />}
            onClick={fetchProjectData}
          >
            Atualizar
          </Button>
        </Box>
      </Box>

      {/* Tabs */}
      <Paper sx={{ mb: 3 }}>
        <Tabs value={tabValue} onChange={handleTabChange} variant="fullWidth">
          <Tab icon={<Construction />} label="Informações" />
          <Tab icon={<Timeline />} label="Timeline" />
          <Tab icon={<ImageIcon />} label={`Imagens (${images.length})`} />
          <Tab icon={<Assessment />} label="Relatórios" />
        </Tabs>
      </Paper>

      {/* Tab Panels */}

      {/* Informações */}
      {tabValue === 0 && (
        <Grid container spacing={3}>
          {/* Progresso Duplo: Cronograma e Real */}
          <Grid item xs={12}>
            <Paper sx={{ p: 3 }}>
              {/* Header */}
              <Box display="flex" alignItems="center" mb={3}>
                <Typography variant="h6" sx={{ flex: 1 }}>
                  Progresso da Obra
                </Typography>
                <IconButton size="small" title="O progresso é calculado de duas formas: automaticamente pelas datas do cronograma e manualmente pelas imagens enviadas">
                  <InfoIcon fontSize="small" />
                </IconButton>
              </Box>

              {/* Progresso do Cronograma */}
              <Box mb={3}>
                <Box display="flex" alignItems="center" mb={1}>
                  <Typography variant="body2" color="text.secondary" sx={{ flex: 1 }}>
                    📅 Progresso do Cronograma (Baseado em Datas)
                  </Typography>
                  <Typography variant="h6" fontWeight={700} sx={{ color: '#1976d2' }}>
                    {project.progress_info?.schedule_progress?.toFixed(2) || '0.00'}%
                  </Typography>
                </Box>
                <LinearProgress
                  variant="determinate"
                  value={Math.min(project.progress_info?.schedule_progress || 0, 100)}
                  sx={{
                    height: 12,
                    borderRadius: 6,
                    backgroundColor: '#e3f2fd',
                    '& .MuiLinearProgress-bar': {
                      backgroundColor: '#1976d2',
                      borderRadius: 6
                    }
                  }}
                />
                <Typography variant="caption" color="text.secondary" sx={{ mt: 0.5, display: 'block' }}>
                  {project.progress_info?.has_schedule
                    ? 'Atualiza automaticamente conforme as datas'
                    : '⚠️ Cadastre um cronograma para ativar este progresso'}
                </Typography>
              </Box>

              {/* Progresso Real */}
              <Box mb={3}>
                <Box display="flex" alignItems="center" mb={1}>
                  <Typography variant="body2" color="text.secondary" sx={{ flex: 1 }}>
                    📸 Progresso Real (Baseado em Imagens)
                  </Typography>
                  <Typography variant="h6" fontWeight={700} sx={{ color: '#9c27b0' }}>
                    {project.progress_info?.actual_progress?.toFixed(2) || '0.00'}%
                  </Typography>
                </Box>
                <LinearProgress
                  variant="determinate"
                  value={Math.min(project.progress_info?.actual_progress || 0, 100)}
                  sx={{
                    height: 12,
                    borderRadius: 6,
                    backgroundColor: '#f3e5f5',
                    '& .MuiLinearProgress-bar': {
                      backgroundColor: '#9c27b0',
                      borderRadius: 6
                    }
                  }}
                />
                <Typography variant="caption" color="text.secondary" sx={{ mt: 0.5, display: 'block' }}>
                  {project.progress_info?.has_images
                    ? 'Atualizado com base nas análises de imagens enviadas'
                    : '📷 Envie fotos da obra pelo chat para atualizar o progresso real'}
                </Typography>
              </Box>

              {/* Alert de Variância */}
              {project.progress_info?.has_schedule && (() => {
                const variance = project.progress_info.variance || 0;
                const getVarianceConfig = () => {
                  if (variance < -5) return { severity: 'error', icon: <TrendingDown />, status: 'ATRASADO', message: 'A obra está atrasada em relação ao cronograma planejado' };
                  if (variance > 5) return { severity: 'success', icon: <TrendingUp />, status: 'ADIANTADO', message: 'A obra está adiantada em relação ao cronograma planejado' };
                  return { severity: 'warning', icon: <RemoveIcon />, status: 'NO PRAZO', message: 'A obra está dentro do prazo previsto no cronograma' };
                };
                const config = getVarianceConfig();

                return (
                  <Alert severity={config.severity} icon={config.icon} sx={{ borderRadius: 2 }}>
                    <Box>
                      <Typography variant="body2" fontWeight={600}>
                        Variância: {variance > 0 ? '+' : ''}{variance.toFixed(2)}% ({config.status})
                      </Typography>
                      <Typography variant="caption">
                        {config.message}
                      </Typography>
                      {!project.progress_info?.has_images && (
                        <Typography variant="caption" display="block" sx={{ mt: 0.5 }}>
                          💡 Envie fotos da obra pelo chat para atualizar o progresso real
                        </Typography>
                      )}
                    </Box>
                  </Alert>
                );
              })()}

              {/* Mensagem quando não tem cronograma */}
              {!project.progress_info?.has_schedule && (
                <Alert severity="info" sx={{ borderRadius: 2 }}>
                  <Typography variant="body2">
                    ℹ️ Para acompanhar o progresso esperado da obra, compartilhe o cronograma de atividades pelo chat.
                  </Typography>
                </Alert>
              )}
            </Paper>
          </Grid>

          {/* Informações Básicas */}
          <Grid item xs={12} md={6}>
            <Paper sx={{ p: 3 }}>
              <Typography variant="h6" gutterBottom>
                Informações Básicas
              </Typography>
              <Divider sx={{ mb: 2 }} />
              <List>
                <ListItem>
                  <ListItemText
                    primary="Tipo de Obra"
                    secondary={project.project_type || 'Não informado'}
                  />
                </ListItem>
                <ListItem>
                  <ListItemText
                    primary="Status"
                    secondary={project.status || 'Não informado'}
                  />
                </ListItem>
                <ListItem>
                  <ListItemText
                    primary="Data de Início"
                    secondary={project.start_date ? formatBrazilDate(project.start_date, "dd/MM/yyyy") : 'Não informado'}
                  />
                </ListItem>
                <ListItem>
                  <ListItemText
                    primary="Previsão de Conclusão"
                    secondary={project.end_date ? formatBrazilDate(project.end_date, "dd/MM/yyyy") : 'Não informado'}
                  />
                </ListItem>
              </List>
            </Paper>
          </Grid>

          {/* Estatísticas */}
          <Grid item xs={12} md={6}>
            <Paper sx={{ p: 3 }}>
              <Typography variant="h6" gutterBottom>
                Estatísticas
              </Typography>
              <Divider sx={{ mb: 2 }} />
              <Grid container spacing={2}>
                <Grid item xs={6} sm={4}>
                  <Card sx={{ bgcolor: 'primary.light', color: 'primary.contrastText' }}>
                    <CardContent>
                      <Typography variant="h4" fontWeight={600}>
                        {timeline?.total_images || 0}
                      </Typography>
                      <Typography variant="body2">
                        Imagens
                      </Typography>
                    </CardContent>
                  </Card>
                </Grid>
                <Grid item xs={6} sm={4}>
                  <Card sx={{ bgcolor: 'secondary.light', color: 'secondary.contrastText' }}>
                    <CardContent>
                      <Typography variant="h4" fontWeight={600}>
                        {timeline?.total_months || 0}
                      </Typography>
                      <Typography variant="body2">
                        Meses de Obra
                      </Typography>
                    </CardContent>
                  </Card>
                </Grid>
                {project.progress_info?.has_schedule && (
                  <Grid item xs={12} sm={4}>
                    <Card sx={{
                      bgcolor: project.progress_info.variance < -5 ? 'error.light' :
                               project.progress_info.variance > 5 ? 'success.light' : 'warning.light',
                      color: project.progress_info.variance < -5 ? 'error.contrastText' :
                             project.progress_info.variance > 5 ? 'success.contrastText' : 'warning.contrastText'
                    }}>
                      <CardContent>
                        <Typography variant="h4" fontWeight={600}>
                          {project.progress_info.variance > 0 ? '+' : ''}{project.progress_info.variance?.toFixed(1)}%
                        </Typography>
                        <Typography variant="body2">
                          Variância
                        </Typography>
                      </CardContent>
                    </Card>
                  </Grid>
                )}
              </Grid>
            </Paper>
          </Grid>

          {/* Descrição */}
          {project.description && (
            <Grid item xs={12}>
              <Paper sx={{ p: 3 }}>
                <Typography variant="h6" gutterBottom>
                  Descrição
                </Typography>
                <Divider sx={{ mb: 2 }} />
                <Typography variant="body1">
                  {project.description}
                </Typography>
              </Paper>
            </Grid>
          )}
        </Grid>
      )}

      {/* Timeline */}
      {tabValue === 1 && (
        <ProjectTimelineTab projectId={projectId} />
      )}

      {/* Imagens */}
      {tabValue === 2 && (
        <Box>
          {images.length > 0 ? (
            <Grid container spacing={2}>
              {images.map((image, index) => (
                <Grid item xs={12} sm={6} md={4} lg={3} key={index}>
                  <Card
                    sx={{
                      cursor: 'pointer',
                      transition: 'transform 0.2s',
                      '&:hover': {
                        transform: 'scale(1.05)'
                      }
                    }}
                    onClick={() => handleImageClick(image)}
                  >
                    <CardMedia
                      component="img"
                      image={`${API_BASE_URL}/projects/images/${image.image_id}/file`}
                      alt={`Imagem da obra`}
                      sx={{
                        height: 200,
                        objectFit: 'cover',
                        bgcolor: 'grey.200'
                      }}
                      onError={(e) => {
                        // Fallback para ícone se imagem não carregar
                        console.error('Error loading image:', image.image_id);
                        e.target.style.display = 'none';
                        e.target.nextSibling.style.display = 'flex';
                      }}
                    />
                    <Box
                      sx={{
                        height: 200,
                        bgcolor: 'grey.200',
                        display: 'none',
                        alignItems: 'center',
                        justifyContent: 'center'
                      }}
                    >
                      <ImageIcon sx={{ fontSize: 60, color: 'grey.400' }} />
                    </Box>
                    <CardContent>
                      <Typography variant="body2" noWrap>
                        {formatBrazilDate(image.analyzed_at || image.captured_at, "dd/MM/yyyy HH:mm")}
                      </Typography>
                      {image.phase && (
                        <Chip
                          label={typeof image.phase === 'string' ? image.phase : (image.phase.name || 'N/A')}
                          size="small"
                          sx={{ mt: 1 }}
                        />
                      )}
                    </CardContent>
                  </Card>
                </Grid>
              ))}
            </Grid>
          ) : (
            <Alert severity="info">
              Nenhuma imagem disponível ainda
            </Alert>
          )}
        </Box>
      )}

      {/* Relatórios */}
      {tabValue === 3 && (
        <Paper sx={{ p: 3 }}>
          <Typography variant="h6" gutterBottom>
            Relatórios e Análises
          </Typography>
          <Alert severity="info">
            Em breve: Relatórios detalhados sobre o andamento da obra, análises de produtividade e relatórios customizados.
          </Alert>
        </Paper>
      )}

      {/* Dialog de Imagem */}
      <Dialog
        open={imageDialogOpen}
        onClose={handleCloseImageDialog}
        maxWidth="md"
        fullWidth
      >
        <DialogContent>
          <Box position="relative">
            <IconButton
              sx={{ position: 'absolute', right: 0, top: 0 }}
              onClick={handleCloseImageDialog}
            >
              <CloseIcon />
            </IconButton>
            {selectedImage && (
              <Box>
                <Box
                  component="img"
                  src={`${API_BASE_URL}/projects/images/${selectedImage.image_id}/file`}
                  alt="Preview"
                  sx={{
                    width: '100%',
                    maxHeight: 500,
                    objectFit: 'contain',
                    bgcolor: 'grey.100',
                    mb: 2,
                    borderRadius: 1
                  }}
                  onLoad={(e) => {
                    console.log('✅ Image loaded successfully:', selectedImage.image_id);
                  }}
                  onError={(e) => {
                    const imageUrl = `${API_BASE_URL}/projects/images/${selectedImage.image_id}/file`;
                    console.error('❌ Error loading image:', {
                      image_id: selectedImage.image_id,
                      url: imageUrl,
                      error: e
                    });
                    e.target.style.display = 'none';
                    if (e.target.nextSibling) {
                      e.target.nextSibling.style.display = 'flex';
                    }
                  }}
                />
                <Box
                  sx={{
                    height: 400,
                    bgcolor: 'grey.200',
                    display: 'none',
                    alignItems: 'center',
                    justifyContent: 'center',
                    flexDirection: 'column',
                    mb: 2,
                    borderRadius: 1,
                    gap: 2
                  }}
                >
                  <ImageIcon sx={{ fontSize: 100, color: 'grey.400' }} />
                  <Typography variant="body2" color="text.secondary">
                    Erro ao carregar imagem
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    ID: {selectedImage.image_id}
                  </Typography>
                </Box>

                <Typography variant="h6" gutterBottom>
                  {formatBrazilDate(selectedImage.analyzed_at || selectedImage.captured_at, "dd 'de' MMMM, yyyy 'às' HH:mm")}
                </Typography>

                {selectedImage.analysis && (
                  <Box mt={2}>
                    <Grid container spacing={2}>
                      {selectedImage.analysis.phase && (
                        <Grid item xs={12} sm={6}>
                          <Typography variant="subtitle2" color="text.secondary">Fase</Typography>
                          <Chip
                            label={typeof selectedImage.analysis.phase === 'string' ? selectedImage.analysis.phase : String(selectedImage.analysis.phase)}
                            color="primary"
                            sx={{ mt: 0.5 }}
                          />
                        </Grid>
                      )}

                      {selectedImage.analysis.progress > 0 && (
                        <Grid item xs={12} sm={6}>
                          <Typography variant="subtitle2" color="text.secondary">Progresso</Typography>
                          <Box display="flex" alignItems="center" mt={0.5}>
                            <Box width="100%" mr={1}>
                              <LinearProgress variant="determinate" value={selectedImage.analysis.progress} />
                            </Box>
                            <Typography variant="body2">{selectedImage.analysis.progress}%</Typography>
                          </Box>
                        </Grid>
                      )}

                      {selectedImage.analysis.quality_score > 0 && (
                        <Grid item xs={12} sm={6}>
                          <Typography variant="subtitle2" color="text.secondary">Qualidade</Typography>
                          <Chip
                            label={`${selectedImage.analysis.quality_score}/10`}
                            color={selectedImage.analysis.quality_score >= 7 ? "success" : "warning"}
                            sx={{ mt: 0.5 }}
                          />
                        </Grid>
                      )}

                      {selectedImage.analysis.safety_severity && selectedImage.analysis.safety_severity !== 'unknown' && (
                        <Grid item xs={12} sm={6}>
                          <Typography variant="subtitle2" color="text.secondary">Segurança</Typography>
                          <Chip
                            label={typeof selectedImage.analysis.safety_severity === 'string' ? selectedImage.analysis.safety_severity : String(selectedImage.analysis.safety_severity)}
                            color={selectedImage.analysis.safety_severity === 'high' || selectedImage.analysis.safety_severity === 'critical' ? "error" : "success"}
                            sx={{ mt: 0.5 }}
                          />
                        </Grid>
                      )}
                    </Grid>

                    {selectedImage.analysis.recommendations && selectedImage.analysis.recommendations.length > 0 && (
                      <Box mt={2}>
                        <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                          Recomendações
                        </Typography>
                        <List dense>
                          {selectedImage.analysis.recommendations.map((rec, idx) => {
                            // Handle both string and object formats
                            const text = typeof rec === 'string' ? rec : (rec.text || rec.description || String(rec));
                            return (
                              <ListItem key={idx}>
                                <ListItemText primary={text} />
                              </ListItem>
                            );
                          })}
                        </List>
                      </Box>
                    )}
                  </Box>
                )}

                {selectedImage.components && selectedImage.components.length > 0 && (
                  <Box mt={2}>
                    <Typography variant="subtitle2" gutterBottom>
                      Elementos detectados:
                    </Typography>
                    <Box display="flex" gap={1} flexWrap="wrap">
                      {selectedImage.components.map((comp, idx) => {
                        // Handle both string and object formats
                        const label = typeof comp === 'string' ? comp : (comp.description || comp.type || 'Elemento');
                        const confidence = typeof comp === 'object' && comp.confidence ? ` (${Math.round(comp.confidence * 100)}%)` : '';
                        return (
                          <Chip
                            key={idx}
                            label={label + confidence}
                            size="small"
                            color={typeof comp === 'object' && comp.status === 'detected' ? 'primary' : 'default'}
                          />
                        );
                      })}
                    </Box>
                  </Box>
                )}
              </Box>
            )}
          </Box>
        </DialogContent>
      </Dialog>
    </Container>
  );
};

export default ProjectDetails;
