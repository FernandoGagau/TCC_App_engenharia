import React, { useState, useEffect } from 'react';
import {
  Box,
  Container,
  Grid,
  Card,
  CardContent,
  CardActionArea,
  Typography,
  Chip,
  LinearProgress,
  CircularProgress,
  Alert,
  IconButton,
  Menu,
  MenuItem,
  Button
} from '@mui/material';
import {
  Construction,
  CalendarToday,
  LocationOn,
  MoreVert,
  Add,
  Business,
  Home,
  Factory,
  Engineering
} from '@mui/icons-material';
import { format } from 'date-fns';
import { ptBR } from 'date-fns/locale';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import toast from 'react-hot-toast';
import API_BASE_URL from '../config/api';

const ProjectList = () => {
  const navigate = useNavigate();
  const [projects, setProjects] = useState([]);
  const [loading, setLoading] = useState(true);
  const [anchorEl, setAnchorEl] = useState(null);
  const [selectedProject, setSelectedProject] = useState(null);

  // Buscar projetos
  const fetchProjects = async () => {
    try {
      setLoading(true);
      const response = await axios.get(`${API_BASE_URL}/projects`);
      setProjects(response.data.projects || []);
    } catch (error) {
      console.error('Erro ao buscar projetos:', error);
      toast.error('Erro ao carregar obras');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchProjects();
  }, []);

  const handleMenuOpen = (event, project) => {
    event.stopPropagation();
    setAnchorEl(event.currentTarget);
    setSelectedProject(project);
  };

  const handleMenuClose = () => {
    setAnchorEl(null);
    setSelectedProject(null);
  };

  const handleDeleteProject = async () => {
    if (!selectedProject) return;

    const confirmDelete = window.confirm(
      `Tem certeza que deseja excluir a obra "${selectedProject.name}"?\n\nEsta ação irá deletar:\n- O registro da obra\n- Todo o histórico de chat\n- Todas as imagens e análises\n\nEsta ação não pode ser desfeita.`
    );

    if (!confirmDelete) {
      handleMenuClose();
      return;
    }

    try {
      await axios.delete(`${API_BASE_URL}/projects/${selectedProject.project_id}`);
      toast.success('Obra deletada com sucesso');
      handleMenuClose();
      fetchProjects(); // Atualiza lista
    } catch (error) {
      console.error('Erro ao deletar obra:', error);
      toast.error('Erro ao deletar obra');
    }
  };

  const handleProjectClick = (projectId) => {
    navigate(`/project/${projectId}`);
  };

  const handleCreateProject = () => {
    navigate('/chat');
  };

  const getProjectTypeIcon = (type) => {
    const icons = {
      residential: <Home />,
      commercial: <Business />,
      industrial: <Factory />,
      reform: <Engineering />,
      infrastructure: <Construction />
    };
    return icons[type] || <Construction />;
  };

  const getProjectTypeLabel = (type) => {
    const labels = {
      residential: 'Residencial',
      commercial: 'Comercial',
      industrial: 'Industrial',
      reform: 'Reforma',
      infrastructure: 'Infraestrutura'
    };
    return labels[type] || type;
  };

  const getStatusColor = (status) => {
    const colors = {
      planning: 'default',
      in_progress: 'primary',
      on_hold: 'warning',
      completed: 'success',
      cancelled: 'error'
    };
    return colors[status] || 'default';
  };

  const getStatusLabel = (status) => {
    const labels = {
      planning: 'Planejamento',
      in_progress: 'Em Andamento',
      on_hold: 'Pausado',
      completed: 'Concluído',
      cancelled: 'Cancelado'
    };
    return labels[status] || status;
  };

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="60vh">
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Container maxWidth="xl" sx={{ mt: 4, mb: 4 }}>
      {/* Header */}
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={4}>
        <Box>
          <Typography variant="h4" gutterBottom sx={{ fontWeight: 600 }}>
            Obras Cadastradas
          </Typography>
          <Typography variant="body2" color="text.secondary">
            {projects.length} {projects.length === 1 ? 'obra cadastrada' : 'obras cadastradas'}
          </Typography>
        </Box>
        <Button
          variant="contained"
          startIcon={<Add />}
          onClick={handleCreateProject}
          size="large"
        >
          Nova Obra
        </Button>
      </Box>

      {/* Projects Grid */}
      {projects.length === 0 ? (
        <Alert severity="info" sx={{ mt: 4 }}>
          Nenhuma obra cadastrada. Clique em "Nova Obra" para começar.
        </Alert>
      ) : (
        <Grid container spacing={3}>
          {projects.map((project) => (
            <Grid item xs={12} sm={6} md={4} key={project.project_id}>
              <Card
                sx={{
                  height: '100%',
                  position: 'relative',
                  transition: 'all 0.3s',
                  '&:hover': {
                    transform: 'translateY(-4px)',
                    boxShadow: 6
                  }
                }}
              >
                {/* Menu button - outside CardActionArea */}
                <IconButton
                  size="small"
                  onClick={(e) => handleMenuOpen(e, project)}
                  sx={{
                    position: 'absolute',
                    top: 8,
                    right: 8,
                    zIndex: 1,
                    bgcolor: 'background.paper',
                    '&:hover': {
                      bgcolor: 'action.hover'
                    }
                  }}
                >
                  <MoreVert />
                </IconButton>

                <CardActionArea onClick={() => handleProjectClick(project.project_id)}>
                  <CardContent>
                    {/* Header com ícone */}
                    <Box display="flex" justifyContent="flex-start" alignItems="start" mb={2}>
                      <Box
                        sx={{
                          backgroundColor: 'primary.light',
                          borderRadius: '12px',
                          p: 1.5,
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center'
                        }}
                      >
                        {getProjectTypeIcon(project.project_type)}
                      </Box>
                    </Box>

                    {/* Nome do projeto */}
                    <Typography variant="h6" gutterBottom sx={{ fontWeight: 600, mb: 1 }}>
                      {project.name}
                    </Typography>

                    {/* Tipo e Status */}
                    <Box display="flex" gap={1} mb={2}>
                      <Chip
                        label={getProjectTypeLabel(project.project_type)}
                        size="small"
                        variant="outlined"
                      />
                      <Chip
                        label={getStatusLabel(project.status)}
                        size="small"
                        color={getStatusColor(project.status)}
                      />
                    </Box>

                    {/* Localização */}
                    <Box display="flex" alignItems="center" gap={1} mb={1}>
                      <LocationOn fontSize="small" color="action" />
                      <Typography variant="body2" color="text.secondary" noWrap>
                        {project.location?.address || 'Endereço não informado'}
                      </Typography>
                    </Box>

                    {/* Data de criação */}
                    <Box display="flex" alignItems="center" gap={1} mb={2}>
                      <CalendarToday fontSize="small" color="action" />
                      <Typography variant="body2" color="text.secondary">
                        {project.created_at ? format(new Date(project.created_at), "dd 'de' MMMM, yyyy", { locale: ptBR }) : 'Data não disponível'}
                      </Typography>
                    </Box>

                    {/* Progresso */}
                    <Box>
                      <Box display="flex" justifyContent="space-between" alignItems="center" mb={0.5}>
                        <Typography variant="body2" color="text.secondary">
                          Progresso
                        </Typography>
                        <Typography variant="body2" fontWeight={600} color="primary">
                          {project.overall_progress || 0}%
                        </Typography>
                      </Box>
                      <LinearProgress
                        variant="determinate"
                        value={project.overall_progress || 0}
                        sx={{ height: 8, borderRadius: 4 }}
                      />
                    </Box>
                  </CardContent>
                </CardActionArea>
              </Card>
            </Grid>
          ))}
        </Grid>
      )}

      {/* Menu de ações */}
      <Menu
        anchorEl={anchorEl}
        open={Boolean(anchorEl)}
        onClose={handleMenuClose}
      >
        <MenuItem onClick={() => {
          if (selectedProject) {
            navigate(`/project/${selectedProject.project_id}`);
          }
          handleMenuClose();
        }}>
          Ver Detalhes
        </MenuItem>
        <MenuItem onClick={handleMenuClose}>
          Editar Obra
        </MenuItem>
        <MenuItem onClick={handleDeleteProject} sx={{ color: 'error.main' }}>
          Excluir Obra
        </MenuItem>
      </Menu>
    </Container>
  );
};

export default ProjectList;
