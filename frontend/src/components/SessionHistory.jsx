import React, { useState, useEffect, useCallback } from 'react';
import {
  Box,
  Paper,
  List,
  ListItem,
  ListItemButton,
  ListItemText,
  ListItemIcon,
  ListItemSecondaryAction,
  Typography,
  Chip,
  IconButton,
  TextField,
  InputAdornment,
  Alert,
  CircularProgress,
  Fab,
  Tooltip,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Card,
  CardContent,
  Grid,
} from '@mui/material';
import {
  Chat as ChatIcon,
  Search as SearchIcon,
  Archive as ArchiveIcon,
  Refresh as RefreshIcon,
  Add as AddIcon,
  AccessTime as TimeIcon,
  Token as TokenIcon,
  AttachMoney as MoneyIcon,
  Message as MessageIcon,
  CheckCircle as ActiveIcon,
  CheckCircle,
  Cancel,
  History as HistoryIcon,
} from '@mui/icons-material';
import { motion, AnimatePresence } from 'framer-motion';
import axios from 'axios';
import { useNavigate } from 'react-router-dom';
import { format, formatDistanceToNow } from 'date-fns';
import { ptBR } from 'date-fns/locale';
import toast from 'react-hot-toast';
import API_BASE_URL from '../config/api';

const SessionHistory = ({ onSelectSession }) => {
  const [sessions, setSessions] = useState([]);
  const [selectedSession, setSelectedSession] = useState(null);
  const [sessionMessages, setSessionMessages] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [filterStatus, setFilterStatus] = useState('all');
  const [dialogOpen, setDialogOpen] = useState(false);
  const [messageSearchResults, setMessageSearchResults] = useState([]);
  const [searchingMessages, setSearchingMessages] = useState(false);
  const navigate = useNavigate();

  // Busca sessões
  const fetchSessions = useCallback(async () => {
    try {
      setLoading(true);
      const params = {};
      if (filterStatus !== 'all') params.status = filterStatus;

      const response = await axios.get(`${API_BASE_URL}/chat/sessions`, { params });
      setSessions(response.data.sessions || []);
    } catch (error) {
      console.error('Erro ao buscar sessões:', error);
      toast.error('Erro ao carregar histórico');
    } finally {
      setLoading(false);
    }
  }, [filterStatus]);

  // Busca detalhes de uma sessão
  const fetchSessionDetails = async (sessionId) => {
    try {
      const response = await axios.get(`${API_BASE_URL}/chat/sessions/${sessionId}`);
      setSelectedSession(response.data.session);
      setSessionMessages(response.data.messages || []);
      setDialogOpen(true);
    } catch (error) {
      console.error('Erro ao buscar detalhes da sessão:', error);
      toast.error('Erro ao carregar sessão');
    }
  };

  // Busca mensagens por conteúdo
  const searchMessages = async () => {
    if (!searchTerm.trim()) return;

    try {
      setSearchingMessages(true);
      const response = await axios.get(`${API_BASE_URL}/chat/search`, {
        params: { query: searchTerm }
      });
      setMessageSearchResults(response.data.results || []);

      if (response.data.results.length === 0) {
        toast.info('Nenhuma mensagem encontrada');
      } else {
        toast.success(`${response.data.results.length} mensagens encontradas`);
      }
    } catch (error) {
      console.error('Erro ao buscar mensagens:', error);
      toast.error('Erro na busca');
    } finally {
      setSearchingMessages(false);
    }
  };

  // Arquiva sessão
  const archiveSession = async (sessionId) => {
    try {
      await axios.post(`${API_BASE_URL}/chat/sessions/${sessionId}/status`, null, {
        params: { status: 'archived' }
      });
      toast.success('Sessão arquivada');
      fetchSessions();
    } catch (error) {
      console.error('Erro ao arquivar sessão:', error);
      toast.error('Erro ao arquivar');
    }
  };

  // Continua uma sessão existente
  const continueSession = (session) => {
    const sessionId = session?.session_id || session?.id;
    if (!sessionId) {
      console.error('ID da sessão não encontrado', session);
      toast.error('Não foi possível continuar a sessão');
      return;
    }

    toast.success('Continuando sessão...');

    if (onSelectSession) {
      // Se tem callback, usa ele (modal/dialog mode)
      onSelectSession({ ...session, session_id: sessionId });
    } else {
      // Caso contrário, navega para o chat com o sessionId
      navigate('/chat', { state: { sessionId } });
    }
  };

  useEffect(() => {
    fetchSessions();
  }, [fetchSessions]);

  const formatDate = (dateString) => {
    const date = new Date(dateString);
    return format(date, 'dd/MM/yyyy HH:mm', { locale: ptBR });
  };

  const formatRelativeTime = (dateString) => {
    const date = new Date(dateString);
    return formatDistanceToNow(date, { locale: ptBR, addSuffix: true });
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'active': return 'primary';
      case 'completed': return 'success';
      case 'archived': return 'default';
      default: return 'default';
    }
  };

  const getStatusIcon = (status) => {
    switch (status) {
      case 'active': return <ActiveIcon />;
      case 'completed': return <CheckCircle />;
      case 'archived': return <ArchiveIcon />;
      default: return <ChatIcon />;
    }
  };

  // Filtra sessões baseado na busca
  const filteredSessions = sessions.filter(session =>
    (session.project_name || session.session_id || 'Sem nome')
      .toLowerCase()
      .includes(searchTerm.toLowerCase())
  );

  return (
    <Box sx={{ height: '100vh', display: 'flex', flexDirection: 'column' }}>
      {/* Header */}
      <Paper elevation={2} sx={{ p: 2, mb: 2 }}>
        <Typography variant="h5" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <HistoryIcon /> Histórico de Conversas
        </Typography>

        <Grid container spacing={2} sx={{ mt: 1 }}>
          <Grid item xs={12} md={6}>
            <TextField
              fullWidth
              size="small"
              placeholder="Buscar sessões..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              InputProps={{
                startAdornment: (
                  <InputAdornment position="start">
                    <SearchIcon />
                  </InputAdornment>
                ),
                endAdornment: searchTerm && (
                  <InputAdornment position="end">
                    <IconButton size="small" onClick={() => setSearchTerm('')}>
                      <Cancel />
                    </IconButton>
                  </InputAdornment>
                )
              }}
            />
          </Grid>

          <Grid item xs={12} md={4}>
            <Box sx={{ display: 'flex', gap: 1 }}>
              <Chip
                label="Todas"
                color={filterStatus === 'all' ? 'primary' : 'default'}
                onClick={() => setFilterStatus('all')}
              />
              <Chip
                label="Ativas"
                color={filterStatus === 'active' ? 'primary' : 'default'}
                onClick={() => setFilterStatus('active')}
              />
              <Chip
                label="Arquivadas"
                color={filterStatus === 'archived' ? 'primary' : 'default'}
                onClick={() => setFilterStatus('archived')}
              />
            </Box>
          </Grid>

          <Grid item xs={12} md={2}>
            <Tooltip title="Atualizar">
              <IconButton onClick={fetchSessions} disabled={loading}>
                <RefreshIcon />
              </IconButton>
            </Tooltip>
          </Grid>
        </Grid>

        {/* Busca em mensagens */}
        <Box sx={{ mt: 2, display: 'flex', gap: 1 }}>
          <TextField
            size="small"
            placeholder="Buscar em todas as mensagens..."
            sx={{ flex: 1 }}
            onKeyPress={(e) => e.key === 'Enter' && searchMessages()}
          />
          <Button
            variant="contained"
            onClick={searchMessages}
            disabled={searchingMessages}
            startIcon={searchingMessages ? <CircularProgress size={16} /> : <SearchIcon />}
          >
            Buscar Mensagens
          </Button>
        </Box>
      </Paper>

      {/* Lista de Sessões */}
      {loading ? (
        <Box display="flex" justifyContent="center" p={4}>
          <CircularProgress size={60} />
        </Box>
      ) : filteredSessions.length === 0 ? (
        <Alert severity="info" sx={{ m: 2 }}>
          Nenhuma sessão encontrada
        </Alert>
      ) : (
        <Paper sx={{ flex: 1, overflow: 'auto', p: 2 }}>
          <List>
            <AnimatePresence>
              {filteredSessions.map((session, index) => (
                <motion.div
                  key={session.session_id}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -20 }}
                  transition={{ delay: index * 0.05 }}
                >
                  <ListItem
                    sx={{
                      mb: 1,
                      borderRadius: 2,
                      bgcolor: 'background.paper',
                      border: '1px solid',
                      borderColor: 'divider',
                      '&:hover': {
                        bgcolor: 'action.hover',
                      }
                    }}
                  >
                    <ListItemButton onClick={() => fetchSessionDetails(session.session_id)}>
                      <ListItemIcon>
                        {getStatusIcon(session.status)}
                      </ListItemIcon>
                      <ListItemText
                        primary={
                          <Box display="flex" alignItems="center" gap={1} component="span">
                            <Typography variant="subtitle1" fontWeight="medium" component="span">
                              {session.project_name || session.session_id?.substring(0, 8) || 'Sessão sem nome'}
                            </Typography>
                            <Chip
                              size="small"
                              label={session.status}
                              color={getStatusColor(session.status)}
                            />
                          </Box>
                        }
                        secondary={
                          <>
                            <Typography variant="body2" color="text.secondary" component="span" display="block">
                              <MessageIcon sx={{ fontSize: 14, mr: 0.5, verticalAlign: 'middle' }} />
                              {session.message_count || 0} mensagens
                              {session.total_tokens && (
                                <>
                                  {' • '}
                                  <TokenIcon sx={{ fontSize: 14, ml: 1, mr: 0.5, verticalAlign: 'middle' }} />
                                  {session.total_tokens.toLocaleString()} tokens
                                </>
                              )}
                              {session.total_cost && (
                                <>
                                  {' • '}
                                  <MoneyIcon sx={{ fontSize: 14, ml: 1, mr: 0.5, verticalAlign: 'middle' }} />
                                  ${session.total_cost.toFixed(4)}
                                </>
                              )}
                            </Typography>
                            <Typography variant="caption" color="text.secondary" component="span" display="block">
                              <TimeIcon sx={{ fontSize: 14, mr: 0.5, verticalAlign: 'middle' }} />
                              {formatRelativeTime(session.last_activity || session.updated_at)}
                              {' • '}
                              {formatDate(session.started_at || session.created_at)}
                            </Typography>
                          </>
                        }
                      />
                      <ListItemSecondaryAction>
                        <Box sx={{ display: 'flex', gap: 0.5 }}>
                          {session.status === 'active' && (
                            <Tooltip title="Continuar conversa">
                              <IconButton
                                size="small"
                                color="primary"
                                onClick={(e) => {
                                  e.stopPropagation();
                                  continueSession(session);
                                }}
                              >
                                <ChatIcon />
                              </IconButton>
                            </Tooltip>
                          )}
                          {session.status !== 'archived' && (
                            <Tooltip title="Arquivar">
                              <IconButton
                                size="small"
                                onClick={(e) => {
                                  e.stopPropagation();
                                  archiveSession(session.session_id);
                                }}
                              >
                                <ArchiveIcon />
                              </IconButton>
                            </Tooltip>
                          )}
                        </Box>
                      </ListItemSecondaryAction>
                    </ListItemButton>
                  </ListItem>
                </motion.div>
              ))}
            </AnimatePresence>
          </List>
        </Paper>
      )}

      {/* Resultados da busca em mensagens */}
      {messageSearchResults.length > 0 && (
        <Paper sx={{ mt: 2, p: 2, maxHeight: 300, overflow: 'auto' }}>
          <Typography variant="h6" gutterBottom>
            Mensagens Encontradas
          </Typography>
          <List dense>
            {messageSearchResults.map((msg) => (
              <ListItem key={msg.message_id}>
                <ListItemText
                  primary={msg.content}
                  secondary={
                    <Typography variant="caption">
                      Sessão: {msg.session_id.slice(0, 8)}... • {msg.role} • {formatDate(msg.timestamp)}
                    </Typography>
                  }
                />
              </ListItem>
            ))}
          </List>
        </Paper>
      )}

      {/* Dialog de detalhes da sessão */}
      <Dialog
        open={dialogOpen}
        onClose={() => setDialogOpen(false)}
        maxWidth="md"
        fullWidth
      >
        {selectedSession && (
          <>
            <DialogTitle>
              {selectedSession.project_name}
              <Typography variant="caption" display="block" color="text.secondary">
                {formatDate(selectedSession.started_at)} • {sessionMessages.length} mensagens
              </Typography>
            </DialogTitle>
            <DialogContent dividers>
              <Box sx={{ maxHeight: 400, overflow: 'auto' }}>
                {sessionMessages.map((msg, index) => (
                  <Card key={msg.id} sx={{ mb: 2 }}>
                    <CardContent>
                      <Box display="flex" justifyContent="space-between" mb={1}>
                        <Chip
                          size="small"
                          label={msg.role}
                          color={msg.role === 'user' ? 'primary' : 'secondary'}
                        />
                        <Typography variant="caption" color="text.secondary">
                          {formatDate(msg.timestamp)}
                          {msg.tokens_used > 0 && ` • ${msg.tokens_used} tokens`}
                        </Typography>
                      </Box>
                      <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap' }}>
                        {msg.content}
                      </Typography>
                    </CardContent>
                  </Card>
                ))}
              </Box>
            </DialogContent>
            <DialogActions>
              {selectedSession.status === 'active' && (
                <Button
                  color="primary"
                  variant="contained"
                  onClick={() => {
                    continueSession(selectedSession);
                    setDialogOpen(false);
                  }}
                >
                  Continuar Conversa
                </Button>
              )}
              <Button onClick={() => setDialogOpen(false)}>
                Fechar
              </Button>
            </DialogActions>
          </>
        )}
      </Dialog>

      {/* FAB para nova conversa */}
      <Fab
        color="primary"
        sx={{ position: 'fixed', bottom: 16, right: 16 }}
        onClick={() => window.location.href = '/'}
      >
        <AddIcon />
      </Fab>
    </Box>
  );
};

export default SessionHistory;
