import React, { useState, useEffect } from 'react';
import {
  Box,
  Grid,
  Paper,
  Typography,
  Card,
  CardContent,
  LinearProgress,
  Chip,
  IconButton,
  Tooltip,
  Alert,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  Divider,
  CircularProgress,
} from '@mui/material';
import {
  AccountBalance as TokenIcon,
  Chat as ChatIcon,
  Timeline as TimelineIcon,
  Refresh as RefreshIcon,
  Warning as WarningIcon,
  CheckCircle as SuccessIcon,
  Info as InfoIcon,
  AttachMoney as MoneyIcon,
} from '@mui/icons-material';
import { motion } from 'framer-motion';
import axios from 'axios';
import API_BASE_URL from '../config/api';

const Dashboard = () => {
  const [dashboardData, setDashboardData] = useState(null);
  const [costData, setCostData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [lastUpdate, setLastUpdate] = useState(new Date());

  const fetchDashboardData = async () => {
    try {
      setLoading(true);
      const [overviewResponse, costResponse] = await Promise.all([
        axios.get(`${API_BASE_URL}/dashboard/overview`),
        axios.get(`${API_BASE_URL}/dashboard/costs`)
      ]);

      setDashboardData(overviewResponse.data);
      setCostData(costResponse.data);
      setLastUpdate(new Date());
      setError(null);
    } catch (err) {
      console.error('Erro ao carregar dashboard:', err);
      setError('Erro ao carregar dados do dashboard');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDashboardData();

    // Atualiza a cada 30 segundos
    const interval = setInterval(fetchDashboardData, 30000);
    return () => clearInterval(interval);
  }, []);

  const StatCard = ({ title, value, subtitle, icon, color = 'primary', progress }) => (
    <motion.div
      whileHover={{ scale: 1.02 }}
      transition={{ type: "spring", stiffness: 300 }}
    >
      <Card sx={{ height: '100%' }}>
        <CardContent>
          <Box display="flex" justifyContent="space-between" alignItems="flex-start">
            <Box>
              <Typography color="textSecondary" variant="subtitle2" gutterBottom>
                {title}
              </Typography>
              <Typography variant="h4" component="div" color={color}>
                {value}
              </Typography>
              {subtitle && (
                <Typography color="textSecondary" variant="body2">
                  {subtitle}
                </Typography>
              )}
            </Box>
            <Box color={`${color}.main`}>
              {icon}
            </Box>
          </Box>
          {progress !== undefined && (
            <Box mt={2}>
              <LinearProgress
                variant="determinate"
                value={progress}
                color={color}
                sx={{ height: 8, borderRadius: 4 }}
              />
              <Typography variant="caption" color="textSecondary" sx={{ mt: 0.5 }}>
                {progress.toFixed(1)}%
              </Typography>
            </Box>
          )}
        </CardContent>
      </Card>
    </motion.div>
  );

  const formatCurrency = (value) => {
    return new Intl.NumberFormat('pt-BR', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 4
    }).format(value);
  };

  const formatNumber = (value) => {
    return new Intl.NumberFormat('pt-BR').format(value);
  };

  const getAlertSeverity = (type) => {
    switch (type) {
      case 'warning': return 'warning';
      case 'error': return 'error';
      case 'success': return 'success';
      default: return 'info';
    }
  };

  const getAlertIcon = (type) => {
    switch (type) {
      case 'warning': return <WarningIcon />;
      case 'error': return <WarningIcon />;
      case 'success': return <SuccessIcon />;
      default: return <InfoIcon />;
    }
  };

  const translateStatus = (status) => {
    const translations = {
      'active': 'ativo',
      'inactive': 'inativo',
      'completed': 'concluído',
      'pending': 'pendente'
    };
    return translations[status] || status;
  };

  if (loading && !dashboardData) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
        <CircularProgress size={60} />
      </Box>
    );
  }

  if (error) {
    return (
      <Alert severity="error" sx={{ m: 2 }}>
        {error}
        <IconButton onClick={fetchDashboardData} size="small" sx={{ ml: 1 }}>
          <RefreshIcon />
        </IconButton>
      </Alert>
    );
  }

  return (
    <Box p={3}>
      {/* Cabeçalho */}
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Typography variant="h4" component="h1" gutterBottom>
          Painel de Análise
        </Typography>
        <Box display="flex" alignItems="center" gap={1}>
          <Typography variant="body2" color="textSecondary">
            Última atualização: {lastUpdate.toLocaleTimeString()}
          </Typography>
          <Tooltip title="Atualizar dados">
            <IconButton onClick={fetchDashboardData} disabled={loading}>
              <RefreshIcon />
            </IconButton>
          </Tooltip>
        </Box>
      </Box>

      {/* Alertas */}
      {dashboardData?.alerts && dashboardData.alerts.length > 0 && (
        <Box mb={3}>
          {dashboardData.alerts.map((alert, index) => (
            <Alert
              key={index}
              severity={getAlertSeverity(alert.type)}
              icon={getAlertIcon(alert.type)}
              sx={{ mb: 1 }}
            >
              {alert.message}
            </Alert>
          ))}
        </Box>
      )}

      {/* Cards principais */}
      <Grid container spacing={3} mb={3}>
        <Grid item xs={12} sm={6} md={3}>
          <StatCard
            title="Sessões Ativas"
            value={dashboardData?.active_sessions || 0}
            subtitle={`${dashboardData?.chat_statistics?.total_sessions || 0} total`}
            icon={<ChatIcon fontSize="large" />}
            color="primary"
          />
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <StatCard
            title="Total de Tokens"
            value={formatNumber(dashboardData?.token_statistics?.total_tokens || 0)}
            subtitle={`${dashboardData?.token_statistics?.total_requests || 0} requisições`}
            icon={<TokenIcon fontSize="large" />}
            color="secondary"
          />
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <StatCard
            title="Custo Total"
            value={formatCurrency(dashboardData?.token_statistics?.total_cost || 0)}
            subtitle="Últimos 7 dias"
            icon={<MoneyIcon fontSize="large" />}
            color="success"
          />
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <StatCard
            title="Mensagens"
            value={formatNumber(dashboardData?.chat_statistics?.total_messages || 0)}
            subtitle="Total processadas"
            icon={<TimelineIcon fontSize="large" />}
            color="info"
          />
        </Grid>
      </Grid>

      <Grid container spacing={3}>
        {/* Sessões Recentes */}
        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 3, height: '100%' }}>
            <Typography variant="h6" gutterBottom>
              Sessões Recentes
            </Typography>
            <List>
              {dashboardData?.recent_sessions?.map((session, index) => (
                <React.Fragment key={session.id}>
                  <ListItem>
                    <ListItemIcon>
                      <ChatIcon color={session.status === 'active' ? 'primary' : 'disabled'} />
                    </ListItemIcon>
                    <ListItemText
                      primary={session.project_name}
                      secondary={
                        <>
                          <Typography variant="body2" color="textSecondary" component="span" display="block">
                            {session.message_count} mensagens • {formatNumber(session.tokens)} tokens
                          </Typography>
                          <Typography variant="caption" color="textSecondary" component="span" display="block">
                            {new Date(session.last_activity).toLocaleString()}
                          </Typography>
                        </>
                      }
                    />
                    <Box textAlign="right">
                      <Chip
                        label={translateStatus(session.status)}
                        size="small"
                        color={session.status === 'active' ? 'primary' : 'default'}
                      />
                      <Typography variant="caption" display="block" color="textSecondary">
                        {formatCurrency(session.cost)}
                      </Typography>
                    </Box>
                  </ListItem>
                  {index < (dashboardData?.recent_sessions?.length || 0) - 1 && <Divider />}
                </React.Fragment>
              )) || (
                <ListItem>
                  <ListItemText
                    primary="Nenhuma sessão encontrada"
                    secondary="Inicie uma nova conversa para ver dados aqui"
                  />
                </ListItem>
              )}
            </List>
          </Paper>
        </Grid>

        {/* Análise de Custos */}
        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 3, height: '100%' }}>
            <Typography variant="h6" gutterBottom>
              Análise de Custos
            </Typography>

            {costData ? (
              <Box>
                <Box mb={2}>
                  <Typography variant="subtitle2" color="textSecondary">
                    Projeção Mensal
                  </Typography>
                  <Typography variant="h5" color="success.main">
                    {formatCurrency(costData.projections?.monthly_projection || 0)}
                  </Typography>
                </Box>

                <Box mb={2}>
                  <Typography variant="subtitle2" color="textSecondary">
                    Custo por Token
                  </Typography>
                  <Typography variant="body1">
                    ${(costData.efficiency?.cost_per_token || 0).toFixed(6)}
                  </Typography>
                </Box>

                <Box mb={2}>
                  <Typography variant="subtitle2" color="textSecondary">
                    Modelos Utilizados
                  </Typography>
                  {costData.models_breakdown && Object.entries(costData.models_breakdown).map(([model, data]) => (
                    <Box key={model} display="flex" justifyContent="space-between" alignItems="center" py={0.5}>
                      <Typography variant="body2" noWrap sx={{ maxWidth: '60%' }}>
                        {model.split('/').pop()}
                      </Typography>
                      <Box textAlign="right">
                        <Typography variant="body2">
                          {formatCurrency(data.total_cost)}
                        </Typography>
                        <Typography variant="caption" color="textSecondary">
                          {data.requests} req
                        </Typography>
                      </Box>
                    </Box>
                  ))}
                </Box>
              </Box>
            ) : (
              <Box display="flex" justifyContent="center" alignItems="center" height="200px">
                <Typography color="textSecondary">
                  Carregando dados de custo...
                </Typography>
              </Box>
            )}
          </Paper>
        </Grid>
      </Grid>

      {/* Status de carregamento */}
      {loading && (
        <Box position="fixed" top={16} right={16} zIndex={1000}>
          <Paper elevation={4} sx={{ p: 1, display: 'flex', alignItems: 'center', gap: 1 }}>
            <CircularProgress size={16} />
            <Typography variant="caption">Atualizando...</Typography>
          </Paper>
        </Box>
      )}
    </Box>
  );
};

export default Dashboard;
