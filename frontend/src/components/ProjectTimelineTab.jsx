import React, { useState, useEffect } from 'react';
import {
  Box,
  Paper,
  Typography,
  Grid,
  Chip,
  LinearProgress,
  Alert,
  CircularProgress,
  Divider,
  Card,
  CardContent
} from '@mui/material';
import {
  Timeline,
  TimelineItem,
  TimelineSeparator,
  TimelineDot,
  TimelineConnector,
  TimelineContent,
  TimelineOppositeContent,
} from '@mui/lab';
import {
  CheckCircle,
  RadioButtonUnchecked,
  AccessTime,
  Warning,
  TodayOutlined
} from '@mui/icons-material';
import { format, parseISO, differenceInDays, isAfter, isBefore, isToday } from 'date-fns';
import { ptBR } from 'date-fns/locale';
import axios from 'axios';
import toast from 'react-hot-toast';
import API_BASE_URL from '../config/api';

const ProjectTimelineTab = ({ projectId }) => {
  const [schedule, setSchedule] = useState(null);
  const [loading, setLoading] = useState(true);

  const fetchSchedule = React.useCallback(async () => {
    try {
      setLoading(true);
      const response = await axios.get(`${API_BASE_URL}/projects/${projectId}/schedule`);
      setSchedule(response.data.schedule);
    } catch (error) {
      console.error('Erro ao buscar cronograma:', error);
      // Não mostra erro se for apenas cronograma não encontrado
      if (error.response?.status !== 404) {
        toast.error('Erro ao carregar cronograma');
      }
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  useEffect(() => {
    fetchSchedule();
  }, [fetchSchedule]);

  const getMilestoneIcon = (status) => {
    switch (status) {
      case 'completed':
        return <CheckCircle />;
      case 'in_progress':
        return <AccessTime />;
      case 'delayed':
        return <Warning />;
      default:
        return <RadioButtonUnchecked />;
    }
  };

  const getMilestoneColor = (status) => {
    switch (status) {
      case 'completed':
        return 'success';
      case 'in_progress':
        return 'primary';
      case 'delayed':
        return 'error';
      default:
        return 'grey';
    }
  };

  const getStatusLabel = (status) => {
    const labels = {
      pending: 'Pendente',
      in_progress: 'Em Andamento',
      completed: 'Concluído',
      delayed: 'Atrasado',
      cancelled: 'Cancelado'
    };
    return labels[status] || status;
  };

  const getPhaseLabel = (phase) => {
    const labels = {
      foundation: 'Fundação',
      structure: 'Estrutura',
      masonry: 'Alvenaria',
      roofing: 'Cobertura',
      electrical: 'Elétrica',
      plumbing: 'Hidráulica',
      finishing: 'Acabamento',
      painting: 'Pintura',
      cleanup: 'Limpeza'
    };
    return labels[phase] || phase;
  };

  const formatDate = (dateString) => {
    if (!dateString) return '';
    return format(parseISO(dateString), "dd 'de' MMM 'de' yyyy", { locale: ptBR });
  };

  const isMilestoneToday = (milestone) => {
    const now = new Date();
    const start = parseISO(milestone.planned_start);
    const end = parseISO(milestone.planned_end);
    return (isBefore(now, end) || isToday(end)) && (isAfter(now, start) || isToday(start));
  };

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
        <CircularProgress />
      </Box>
    );
  }

  if (!schedule) {
    return (
      <Paper sx={{ p: 3 }}>
        <Alert severity="info">
          Nenhum cronograma cadastrado ainda. O cronograma será criado quando você enviar informações sobre as etapas da obra no chat.
        </Alert>
      </Paper>
    );
  }

  const today = new Date();
  const projectStart = parseISO(schedule.project_start);
  const projectEnd = parseISO(schedule.project_end);
  const daysElapsed = differenceInDays(today, projectStart);
  const totalDays = differenceInDays(projectEnd, projectStart);
  const timeProgress = Math.min(100, Math.max(0, (daysElapsed / totalDays) * 100));

  return (
    <Box>
      {/* Cabeçalho com Resumo */}
      <Paper sx={{ p: 3, mb: 3 }}>
        <Typography variant="h6" gutterBottom>
          {schedule.name}
        </Typography>
        {schedule.description && (
          <Typography variant="body2" color="text.secondary" mb={2}>
            {schedule.description}
          </Typography>
        )}

        <Divider sx={{ my: 2 }} />

        <Grid container spacing={3}>
          <Grid item xs={12} md={3}>
            <Typography variant="subtitle2" color="text.secondary">
              Início do Projeto
            </Typography>
            <Typography variant="body1" fontWeight={600}>
              {formatDate(schedule.project_start)}
            </Typography>
          </Grid>
          <Grid item xs={12} md={3}>
            <Typography variant="subtitle2" color="text.secondary">
              Previsão de Término
            </Typography>
            <Typography variant="body1" fontWeight={600}>
              {formatDate(schedule.project_end)}
            </Typography>
          </Grid>
          <Grid item xs={12} md={3}>
            <Typography variant="subtitle2" color="text.secondary">
              Dias Decorridos
            </Typography>
            <Typography variant="body1" fontWeight={600} color="primary.main">
              {schedule.days_elapsed} de {totalDays} dias
            </Typography>
          </Grid>
          <Grid item xs={12} md={3}>
            <Typography variant="subtitle2" color="text.secondary">
              Dias Restantes
            </Typography>
            <Typography
              variant="body1"
              fontWeight={600}
              color={schedule.days_remaining < 0 ? 'error.main' : 'success.main'}
            >
              {schedule.days_remaining} dias
            </Typography>
          </Grid>
        </Grid>

        {/* Barra de Progresso Temporal */}
        <Box sx={{ mt: 3 }}>
          <Box display="flex" justifyContent="space-between" alignItems="center" mb={1}>
            <Typography variant="subtitle2" color="text.secondary">
              Progresso Temporal
            </Typography>
            <Chip
              icon={<TodayOutlined />}
              label="Hoje"
              size="small"
              color="primary"
              variant="outlined"
            />
          </Box>
          <LinearProgress
            variant="determinate"
            value={timeProgress}
            sx={{
              height: 12,
              borderRadius: 6,
              bgcolor: 'grey.200',
              '& .MuiLinearProgress-bar': {
                borderRadius: 6
              }
            }}
          />
          <Typography variant="caption" color="text.secondary" mt={0.5}>
            {timeProgress.toFixed(1)}% do tempo decorrido
          </Typography>
        </Box>

        {/* Progresso das Etapas */}
        <Box sx={{ mt: 2 }}>
          <Typography variant="subtitle2" color="text.secondary" mb={1}>
            Progresso Geral das Etapas
          </Typography>
          <LinearProgress
            variant="determinate"
            value={schedule.overall_progress}
            color="success"
            sx={{ height: 12, borderRadius: 6 }}
          />
          <Typography variant="caption" color="text.secondary" mt={0.5}>
            {schedule.overall_progress.toFixed(1)}% concluído
          </Typography>
        </Box>
      </Paper>

      {/* Timeline de Marcos */}
      <Paper sx={{ p: 3 }}>
        <Typography variant="h6" gutterBottom mb={3}>
          Cronograma de Etapas
        </Typography>

        <Timeline position="alternate">
          {schedule.milestones.map((milestone, index) => {
            const isCurrentMilestone = isMilestoneToday(milestone);

            return (
              <TimelineItem key={milestone.milestone_id}>
                <TimelineOppositeContent color="textSecondary">
                  <Typography variant="body2" fontWeight={600}>
                    {formatDate(milestone.planned_start)}
                  </Typography>
                  <Typography variant="caption">
                    até {formatDate(milestone.planned_end)}
                  </Typography>
                  {milestone.actual_start && (
                    <Typography variant="caption" display="block" color="success.main" mt={1}>
                      Iniciado: {formatDate(milestone.actual_start)}
                    </Typography>
                  )}
                  {milestone.actual_end && (
                    <Typography variant="caption" display="block" color="success.main">
                      Concluído: {formatDate(milestone.actual_end)}
                    </Typography>
                  )}
                </TimelineOppositeContent>

                <TimelineSeparator>
                  <TimelineDot
                    color={getMilestoneColor(milestone.status)}
                    variant={isCurrentMilestone ? 'filled' : 'outlined'}
                    sx={isCurrentMilestone ? {
                      width: 48,
                      height: 48,
                      animation: 'pulse 2s infinite',
                      '@keyframes pulse': {
                        '0%, 100%': {
                          transform: 'scale(1)',
                          opacity: 1
                        },
                        '50%': {
                          transform: 'scale(1.1)',
                          opacity: 0.8
                        }
                      }
                    } : {}}
                  >
                    {getMilestoneIcon(milestone.status)}
                  </TimelineDot>
                  {index < schedule.milestones.length - 1 && <TimelineConnector />}
                </TimelineSeparator>

                <TimelineContent>
                  <Card
                    sx={{
                      bgcolor: isCurrentMilestone ? 'primary.50' : 'background.paper',
                      border: isCurrentMilestone ? 2 : 1,
                      borderColor: isCurrentMilestone ? 'primary.main' : 'divider'
                    }}
                  >
                    <CardContent>
                      {isCurrentMilestone && (
                        <Chip
                          icon={<TodayOutlined />}
                          label="ESTAMOS AQUI"
                          color="primary"
                          size="small"
                          sx={{ mb: 1 }}
                        />
                      )}
                      <Typography variant="h6" component="h3" gutterBottom>
                        {milestone.name}
                      </Typography>
                      {milestone.description && (
                        <Typography variant="body2" color="text.secondary" mb={1}>
                          {milestone.description}
                        </Typography>
                      )}
                      <Box display="flex" gap={1} flexWrap="wrap" mb={2}>
                        <Chip
                          label={getPhaseLabel(milestone.phase)}
                          size="small"
                          variant="outlined"
                        />
                        <Chip
                          label={getStatusLabel(milestone.status)}
                          size="small"
                          color={getMilestoneColor(milestone.status)}
                        />
                      </Box>
                      <Box>
                        <Typography variant="caption" color="text.secondary">
                          Progresso
                        </Typography>
                        <LinearProgress
                          variant="determinate"
                          value={milestone.progress_percentage}
                          color={getMilestoneColor(milestone.status)}
                          sx={{ height: 6, borderRadius: 3, mt: 0.5 }}
                        />
                        <Typography variant="caption" color="text.secondary">
                          {milestone.progress_percentage}%
                        </Typography>
                      </Box>
                      {milestone.notes && (
                        <Typography variant="caption" color="text.secondary" display="block" mt={1}>
                          📝 {milestone.notes}
                        </Typography>
                      )}
                    </CardContent>
                  </Card>
                </TimelineContent>
              </TimelineItem>
            );
          })}
        </Timeline>
      </Paper>
    </Box>
  );
};

export default ProjectTimelineTab;
