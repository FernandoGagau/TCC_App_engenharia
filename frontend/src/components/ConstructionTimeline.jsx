import React, { useState, useEffect } from 'react';
import {
  Box,
  Paper,
  Typography,
  Grid,
  Card,
  CardContent,
  CardMedia,
  Button,
  Chip,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  IconButton,
  LinearProgress,
  Alert,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Tabs,
  Tab,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  Divider,
  CircularProgress,
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
  Image as ImageIcon,
  CalendarMonth,
  Construction,
  Assessment,
  CompareArrows,
  TrendingUp,
  PhotoCamera,
  Schedule,
  Folder,
  Close as CloseIcon,
  Download,
  Analytics,
} from '@mui/icons-material';
import axios from 'axios';
import { format, parseISO } from 'date-fns';
import { ptBR } from 'date-fns/locale';
import toast from 'react-hot-toast';
import API_BASE_URL from '../config/api';

const ConstructionTimeline = () => {
  const [timelineSummary, setTimelineSummary] = useState(null);
  const [selectedMonth, setSelectedMonth] = useState('');
  const [monthImages, setMonthImages] = useState([]);
  const [progressData, setProgressData] = useState(null);
  const [comparison, setComparison] = useState(null);
  const [loading, setLoading] = useState(true);
  const [selectedImage, setSelectedImage] = useState(null);
  const [tabValue, setTabValue] = useState(0);
  const [compareMonth1, setCompareMonth1] = useState('');
  const [compareMonth2, setCompareMonth2] = useState('');

  // Busca resumo da timeline
  const fetchTimelineSummary = async () => {
    try {
      setLoading(true);
      const response = await axios.get(`${API_BASE_URL}/timeline/summary`);
      setTimelineSummary(response.data);

      // Define primeiro mês como selecionado
      if (response.data.periods && response.data.periods.length > 0) {
        setSelectedMonth(response.data.periods[0].month);
      }
    } catch (error) {
      console.error('Erro ao buscar timeline:', error);
      toast.error('Erro ao carregar timeline');
    } finally {
      setLoading(false);
    }
  };

  // Busca imagens de um mês
  const fetchMonthImages = async (month) => {
    if (!month) return;

    try {
      const response = await axios.get(`${API_BASE_URL}/timeline/images/${month}`);
      setMonthImages(response.data.images || []);
    } catch (error) {
      console.error('Erro ao buscar imagens:', error);
      toast.error('Erro ao carregar imagens');
    }
  };

  // Busca análise de progresso
  const fetchProgress = async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/timeline/progress`);
      setProgressData(response.data);
    } catch (error) {
      console.error('Erro ao buscar progresso:', error);
    }
  };

  // Compara períodos
  const comparePeriods = async () => {
    if (!compareMonth1 || !compareMonth2) {
      toast.error('Selecione dois períodos para comparar');
      return;
    }

    try {
      const response = await axios.get(`${API_BASE_URL}/timeline/compare`, {
        params: {
          period1: compareMonth1,
          period2: compareMonth2
        }
      });
      setComparison(response.data);
      toast.success('Comparação realizada');
    } catch (error) {
      console.error('Erro ao comparar:', error);
      toast.error('Erro ao comparar períodos');
    }
  };

  useEffect(() => {
    fetchTimelineSummary();
    fetchProgress();
  }, []);

  useEffect(() => {
    if (selectedMonth) {
      fetchMonthImages(selectedMonth);
    }
  }, [selectedMonth]);

  const formatDate = (dateString) => {
    if (!dateString) return '';
    const date = parseISO(dateString);
    return format(date, "dd 'de' MMMM 'de' yyyy", { locale: ptBR });
  };

  const getProgressColor = (percentage) => {
    if (percentage < 30) return 'error';
    if (percentage < 60) return 'warning';
    if (percentage < 90) return 'info';
    return 'success';
  };

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
        <CircularProgress size={60} />
      </Box>
    );
  }

  return (
    <Box sx={{ p: 3 }}>
      {/* Cabeçalho */}
      <Paper elevation={2} sx={{ p: 3, mb: 3 }}>
        <Typography variant="h4" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <Construction color="primary" />
          Timeline da Obra
        </Typography>

        {timelineSummary && (
          <Grid container spacing={2} sx={{ mt: 1 }}>
            <Grid item xs={6} md={3}>
              <Typography variant="subtitle2" color="textSecondary">
                Total de Imagens
              </Typography>
              <Typography variant="h6">
                {timelineSummary.total_images}
              </Typography>
            </Grid>
            <Grid item xs={6} md={3}>
              <Typography variant="subtitle2" color="textSecondary">
                Meses Documentados
              </Typography>
              <Typography variant="h6">
                {timelineSummary.total_months}
              </Typography>
            </Grid>
            <Grid item xs={6} md={3}>
              <Typography variant="subtitle2" color="textSecondary">
                Projeto
              </Typography>
              <Typography variant="h6">
                {timelineSummary.project}
              </Typography>
            </Grid>
            <Grid item xs={6} md={3}>
              <Typography variant="subtitle2" color="textSecondary">
                Duração Total
              </Typography>
              <Typography variant="h6">
                {progressData?.total_duration_days || 0} dias
              </Typography>
            </Grid>
          </Grid>
        )}
      </Paper>

      {/* Tabs de navegação */}
      <Paper sx={{ mb: 3 }}>
        <Tabs value={tabValue} onChange={(e, v) => setTabValue(v)}>
          <Tab icon={<CalendarMonth />} label="Timeline" />
          <Tab icon={<ImageIcon />} label="Galeria" />
          <Tab icon={<TrendingUp />} label="Progresso" />
          <Tab icon={<CompareArrows />} label="Comparar" />
        </Tabs>
      </Paper>

      {/* Conteúdo das Tabs */}
      {tabValue === 0 && (
        <Paper sx={{ p: 3 }}>
          <Typography variant="h6" gutterBottom>
            Linha do Tempo
          </Typography>
          <Timeline position="alternate">
            {timelineSummary?.periods?.map((period, index) => (
              <TimelineItem key={period.month}>
                <TimelineOppositeContent color="textSecondary">
                  <Typography variant="body2">
                    {period.image_count} fotos
                  </Typography>
                  <Typography variant="caption">
                    {period.dates_count} dias documentados
                  </Typography>
                </TimelineOppositeContent>
                <TimelineSeparator>
                  <TimelineDot color={index === 0 ? 'primary' : 'grey'}>
                    <Folder />
                  </TimelineDot>
                  {index < timelineSummary.periods.length - 1 && <TimelineConnector />}
                </TimelineSeparator>
                <TimelineContent>
                  <Card
                    sx={{
                      cursor: 'pointer',
                      '&:hover': { bgcolor: 'action.hover' }
                    }}
                    onClick={() => {
                      setSelectedMonth(period.month);
                      setTabValue(1); // Vai para galeria
                    }}
                  >
                    <CardContent>
                      <Typography variant="h6" component="h3">
                        {period.month}
                      </Typography>
                      <Typography variant="body2" color="textSecondary">
                        {formatDate(period.start_date)}
                        {period.end_date && period.start_date !== period.end_date &&
                          ` - ${formatDate(period.end_date)}`}
                      </Typography>
                    </CardContent>
                  </Card>
                </TimelineContent>
              </TimelineItem>
            ))}
          </Timeline>
        </Paper>
      )}

      {tabValue === 1 && (
        <Box>
          {/* Seletor de Mês */}
          <Paper sx={{ p: 2, mb: 2 }}>
            <FormControl fullWidth>
              <InputLabel>Selecione o Mês</InputLabel>
              <Select
                value={selectedMonth}
                onChange={(e) => setSelectedMonth(e.target.value)}
                label="Selecione o Mês"
              >
                {timelineSummary?.periods?.map((period) => (
                  <MenuItem key={period.month} value={period.month}>
                    {period.month} ({period.image_count} imagens)
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
          </Paper>

          {/* Galeria de Imagens */}
          <Grid container spacing={2}>
            {monthImages.map((image, index) => (
              <Grid item xs={12} sm={6} md={4} key={index}>
                <Card>
                  <CardMedia
                    component="img"
                    height="200"
                    image={`${API_BASE_URL}/static/${image.filename}`}
                    alt={`Obra - ${image.day}`}
                    sx={{ cursor: 'pointer' }}
                    onClick={() => setSelectedImage(image)}
                  />
                  <CardContent>
                    <Typography variant="body2">
                      {image.day}
                    </Typography>
                    <Typography variant="caption" color="textSecondary">
                      {image.month}
                    </Typography>
                  </CardContent>
                </Card>
              </Grid>
            ))}
          </Grid>

          {monthImages.length === 0 && (
            <Alert severity="info">
              Nenhuma imagem encontrada para {selectedMonth}
            </Alert>
          )}
        </Box>
      )}

      {tabValue === 2 && progressData && (
        <Grid container spacing={3}>
          <Grid item xs={12} md={8}>
            <Paper sx={{ p: 3 }}>
              <Typography variant="h6" gutterBottom>
                Análise de Progresso
              </Typography>

              <Box sx={{ mb: 3 }}>
                <Typography variant="subtitle2" color="textSecondary">
                  Período Total
                </Typography>
                <Typography variant="body1">
                  {formatDate(progressData.project_start)} - {formatDate(progressData.project_end)}
                </Typography>
                <Typography variant="h5" sx={{ mt: 1 }}>
                  {progressData.total_duration_days} dias
                </Typography>
              </Box>

              <Divider sx={{ my: 2 }} />

              <Typography variant="subtitle1" gutterBottom>
                Progresso Mensal
              </Typography>
              {progressData.monthly_progress?.map((month) => (
                <Box key={month.month} sx={{ mb: 2 }}>
                  <Box display="flex" justifyContent="space-between" alignItems="center">
                    <Typography variant="body2">
                      {month.month}
                    </Typography>
                    <Chip
                      size="small"
                      label={`${month.image_count} fotos`}
                      color="primary"
                    />
                  </Box>
                  <LinearProgress
                    variant="determinate"
                    value={month.documentation_frequency}
                    color={getProgressColor(month.documentation_frequency)}
                    sx={{ mt: 1, height: 8, borderRadius: 4 }}
                  />
                  <Typography variant="caption" color="textSecondary">
                    {month.documentation_frequency}% dos dias documentados
                  </Typography>
                </Box>
              ))}
            </Paper>
          </Grid>

          <Grid item xs={12} md={4}>
            <Paper sx={{ p: 3 }}>
              <Typography variant="h6" gutterBottom>
                Estatísticas
              </Typography>
              <List dense>
                <ListItem>
                  <ListItemIcon>
                    <PhotoCamera />
                  </ListItemIcon>
                  <ListItemText
                    primary="Total de Imagens"
                    secondary={progressData.total_images}
                  />
                </ListItem>
                <ListItem>
                  <ListItemIcon>
                    <Schedule />
                  </ListItemIcon>
                  <ListItemText
                    primary="Média por Dia"
                    secondary={`${progressData.average_images_per_day} imagens`}
                  />
                </ListItem>
                <ListItem>
                  <ListItemIcon>
                    <Analytics />
                  </ListItemIcon>
                  <ListItemText
                    primary="Períodos Analisados"
                    secondary={progressData.periods_analyzed}
                  />
                </ListItem>
              </List>
            </Paper>
          </Grid>
        </Grid>
      )}

      {tabValue === 3 && (
        <Paper sx={{ p: 3 }}>
          <Typography variant="h6" gutterBottom>
            Comparar Períodos
          </Typography>

          <Grid container spacing={2} sx={{ mb: 3 }}>
            <Grid item xs={12} md={5}>
              <FormControl fullWidth>
                <InputLabel>Primeiro Período</InputLabel>
                <Select
                  value={compareMonth1}
                  onChange={(e) => setCompareMonth1(e.target.value)}
                  label="Primeiro Período"
                >
                  {timelineSummary?.periods?.map((period) => (
                    <MenuItem key={period.month} value={period.month}>
                      {period.month}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Grid>

            <Grid item xs={12} md={2} display="flex" justifyContent="center" alignItems="center">
              <CompareArrows />
            </Grid>

            <Grid item xs={12} md={5}>
              <FormControl fullWidth>
                <InputLabel>Segundo Período</InputLabel>
                <Select
                  value={compareMonth2}
                  onChange={(e) => setCompareMonth2(e.target.value)}
                  label="Segundo Período"
                >
                  {timelineSummary?.periods?.map((period) => (
                    <MenuItem key={period.month} value={period.month}>
                      {period.month}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Grid>
          </Grid>

          <Button
            variant="contained"
            onClick={comparePeriods}
            disabled={!compareMonth1 || !compareMonth2}
            startIcon={<Assessment />}
          >
            Comparar Períodos
          </Button>

          {comparison && (
            <Grid container spacing={2} sx={{ mt: 3 }}>
              <Grid item xs={12} md={6}>
                <Card>
                  <CardContent>
                    <Typography variant="h6" gutterBottom>
                      {comparison.period1.month}
                    </Typography>
                    <List dense>
                      <ListItem>
                        <ListItemText
                          primary="Imagens"
                          secondary={comparison.period1.image_count}
                        />
                      </ListItem>
                      <ListItem>
                        <ListItemText
                          primary="Datas Documentadas"
                          secondary={comparison.period1.dates.length}
                        />
                      </ListItem>
                      <ListItem>
                        <ListItemText
                          primary="Período"
                          secondary={`${formatDate(comparison.period1.start_date)} - ${formatDate(comparison.period1.end_date)}`}
                        />
                      </ListItem>
                    </List>
                  </CardContent>
                </Card>
              </Grid>

              <Grid item xs={12} md={6}>
                <Card>
                  <CardContent>
                    <Typography variant="h6" gutterBottom>
                      {comparison.period2.month}
                    </Typography>
                    <List dense>
                      <ListItem>
                        <ListItemText
                          primary="Imagens"
                          secondary={comparison.period2.image_count}
                        />
                      </ListItem>
                      <ListItem>
                        <ListItemText
                          primary="Datas Documentadas"
                          secondary={comparison.period2.dates.length}
                        />
                      </ListItem>
                      <ListItem>
                        <ListItemText
                          primary="Período"
                          secondary={`${formatDate(comparison.period2.start_date)} - ${formatDate(comparison.period2.end_date)}`}
                        />
                      </ListItem>
                    </List>
                  </CardContent>
                </Card>
              </Grid>

              <Grid item xs={12}>
                <Alert severity="info">
                  <Typography variant="subtitle2">Análise Comparativa</Typography>
                  <Typography variant="body2">
                    • Diferença de tempo: {comparison.time_difference_days} dias
                  </Typography>
                  <Typography variant="body2">
                    • Diferença de imagens: {comparison.image_count_difference > 0 ? '+' : ''}{comparison.image_count_difference}
                  </Typography>
                </Alert>
              </Grid>
            </Grid>
          )}
        </Paper>
      )}

      {/* Dialog de Imagem Ampliada */}
      <Dialog
        open={!!selectedImage}
        onClose={() => setSelectedImage(null)}
        maxWidth="lg"
        fullWidth
      >
        {selectedImage && (
          <>
            <DialogTitle>
              <Box display="flex" justifyContent="space-between" alignItems="center">
                <Typography>
                  {selectedImage.day} - {selectedImage.month}
                </Typography>
                <IconButton onClick={() => setSelectedImage(null)}>
                  <CloseIcon />
                </IconButton>
              </Box>
            </DialogTitle>
            <DialogContent>
              <img
                src={`${API_BASE_URL}/static/${selectedImage.filename}`}
                alt="Imagem ampliada"
                style={{ width: '100%', height: 'auto' }}
              />
            </DialogContent>
            <DialogActions>
              <Button startIcon={<Download />}>
                Download
              </Button>
              <Button onClick={() => setSelectedImage(null)}>
                Fechar
              </Button>
            </DialogActions>
          </>
        )}
      </Dialog>
    </Box>
  );
};

export default ConstructionTimeline;
