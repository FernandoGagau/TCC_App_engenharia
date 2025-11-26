import React, { useState, useEffect, useRef } from 'react';
import {
  Box,
  Paper,
  TextField,
  IconButton,
  Typography,
  Avatar,
  Chip,
  CircularProgress,
  Button,
  Card,
  CardContent,
  LinearProgress,
  Divider,
  Alert,
} from '@mui/material';
import {
  Send as SendIcon,
  AttachFile as AttachFileIcon,
  Construction as ConstructionIcon,
  Person as PersonIcon,
  Image as ImageIcon,
  RestartAlt as RestartIcon,
  Download as DownloadIcon,
} from '@mui/icons-material';
import { motion, AnimatePresence } from 'framer-motion';
import { useDropzone } from 'react-dropzone';
import toast from 'react-hot-toast';
import ReactMarkdown from 'react-markdown';
import axios from 'axios';
import { useLocation, useNavigate } from 'react-router-dom';
import API_BASE_URL from '../config/api';

const ChatInterface = () => {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [sessionId, setSessionId] = useState(null);
  const [sessionState, setSessionState] = useState('initial');
  const [projectData, setProjectData] = useState(null);
  const [attachments, setAttachments] = useState([]);
  const messagesEndRef = useRef(null);
  const location = useLocation();
  const navigate = useNavigate();
  const sessionIdFromState = location.state?.sessionId;

  const loadExistingSession = async (existingSessionId) => {
    if (!existingSessionId) return;

    setLoading(true);
    try {
      const response = await axios.get(`${API_BASE_URL}/chat/sessions/${existingSessionId}`);
      const sessionInfo = response.data.session || {};
      const historyMessages = (response.data.messages || [])
        .sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp))
        .map((msg) => ({
        role: msg.role,
        content: msg.content,
        timestamp: msg.timestamp,
        attachments: msg.attachments || [],
        tokens_used: msg.tokens_used,
      }));

      setSessionId(sessionInfo.id || existingSessionId);
      setSessionState(sessionInfo.status || 'active');
      setProjectData(sessionInfo.metadata || null);
      setMessages(historyMessages);
      setAttachments([]);

      toast.success('Sessão carregada!');

      // Limpa estado de navegação para evitar recarregamentos desnecessários
      navigate('.', { replace: true, state: {} });
    } catch (error) {
      console.error('Erro ao carregar sessão existente:', error);
      toast.error('Não foi possível carregar a sessão selecionada');
    } finally {
      setLoading(false);
    }
  };

  // Inicializa a sessão conforme origem (apenas para sessões existentes)
  useEffect(() => {
    if (sessionIdFromState) {
      loadExistingSession(sessionIdFromState);
    }
    // Note: Não criamos sessão automaticamente - ela será criada apenas quando o usuário enviar a primeira mensagem
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sessionIdFromState]);

  // Auto-scroll to bottom
  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  // Note: startNewSession function removed - sessions are now created automatically on first message

  const sendMessage = async () => {
    if (!input.trim() && attachments.length === 0) return;
    // Note: sessionId pode ser null na primeira mensagem - será criado automaticamente pelo backend

    const userMessage = {
      role: 'user',
      content: input,
      timestamp: new Date().toISOString(),
      attachments: attachments.map(a => ({ name: a.name, type: a.type })),
    };

    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setLoading(true);

    try {
      // Convert attachments to base64
      const attachmentsWithData = await Promise.all(
        attachments.map(async (file) => {
          return new Promise((resolve) => {
            const reader = new FileReader();
            reader.onload = (e) => {
              resolve({
                type: file.type,
                filename: file.name,
                data: e.target.result.split(',')[1], // Remove "data:image/jpeg;base64," prefix
                size: file.size
              });
            };
            reader.readAsDataURL(file);
          });
        })
      );

      // Prepare request data
      const requestData = {
        session_id: sessionId,
        message: input || 'Enviando arquivo',
        attachments: attachmentsWithData,
      };

      const fullUrl = `${API_BASE_URL}/chat/message`;
      console.log('🔍 Sending POST to:', fullUrl);
      console.log('🔍 Request data:', { ...requestData, attachments: requestData.attachments?.length || 0 });

      const response = await axios.post(fullUrl, requestData);

      // Update sessionId if this was the first message (session created automatically)
      if (!sessionId && response.data.session_id) {
        setSessionId(response.data.session_id);
        setSessionState(response.data.state || 'active');
      }

      // Add assistant response
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: response.data.response,
        timestamp: new Date().toISOString(),
        token_usage: response.data.token_usage,
      }]);

      // Show token usage info if available
      if (response.data.token_usage) {
        console.log('Token usage:', response.data.token_usage);
      }

      // Show warnings if any
      if (response.data.warnings && response.data.warnings.length > 0) {
        response.data.warnings.forEach(warning => {
          if (warning) toast.warning(warning);
        });
      }

      // Clear attachments after sending
      setAttachments([]);

      // Show action hints
      if (response.data.next_action === 'upload_photo') {
        toast('📷 Envie uma foto para continuar', { icon: '📸' });
      }

    } catch (error) {
      console.error('Error sending message:', error);
      toast.error('Erro ao enviar mensagem');
      
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: 'Desculpe, ocorreu um erro. Por favor, tente novamente.',
        timestamp: new Date().toISOString(),
        isError: true,
      }]);
    } finally {
      setLoading(false);
    }
  };


  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop: (acceptedFiles) => {
      setAttachments(prev => [...prev, ...acceptedFiles]);
      toast.success(`${acceptedFiles.length} arquivo(s) anexado(s)`);
    },
    accept: {
      'image/*': ['.png', '.jpg', '.jpeg'],
      'application/pdf': ['.pdf'],
    },
    maxSize: 50 * 1024 * 1024, // 50MB
  });

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  const resetSession = async () => {
    try {
      if (sessionId) {
        await axios.post(`${API_BASE_URL}/chat/session/${sessionId}/reset`);
      }

      // Reset local state (session will be recreated on next message)
      setSessionId(null);
      setSessionState('initial');
      setMessages([]);
      setProjectData(null);
      setAttachments([]);

      toast.success('Sessão reiniciada');
    } catch (error) {
      console.error('Error resetting session:', error);
      toast.error('Erro ao reiniciar sessão');
    }
  };

  const downloadProject = () => {
    if (!projectData) return;
    
    const dataStr = JSON.stringify(projectData, null, 2);
    const dataUri = 'data:application/json;charset=utf-8,'+ encodeURIComponent(dataStr);
    
    const exportFileDefaultName = `obra_${projectData.info?.project_name?.replace(' ', '_')}_${new Date().toISOString().split('T')[0]}.json`;
    
    const linkElement = document.createElement('a');
    linkElement.setAttribute('href', dataUri);
    linkElement.setAttribute('download', exportFileDefaultName);
    linkElement.click();
    
    toast.success('Projeto baixado!');
  };

  return (
    <Box sx={{ height: '100vh', display: 'flex', flexDirection: 'column', bgcolor: 'background.default' }}>
      {/* Header */}
      <Paper elevation={2} sx={{ p: 2, borderRadius: 0 }}>
        <Box display="flex" alignItems="center" justifyContent="space-between">
          <Box display="flex" alignItems="center" gap={2}>
            <ConstructionIcon color="primary" sx={{ fontSize: 32 }} />
            <Box>
              <Typography variant="h6" fontWeight="bold">
                Agente de Análise de Obras
              </Typography>
              <Typography variant="caption" color="text.secondary">
                Documentação inteligente com IA • LangChain • Nano Banana
              </Typography>
            </Box>
          </Box>
          
          <Box display="flex" gap={1}>
            {projectData && (
              <Button
                startIcon={<DownloadIcon />}
                onClick={downloadProject}
                variant="outlined"
                size="small"
              >
                Baixar JSON
              </Button>
            )}
            <Button
              startIcon={<RestartIcon />}
              onClick={resetSession}
              variant="outlined"
              color="warning"
              size="small"
            >
              Reiniciar
            </Button>
          </Box>
        </Box>
        
        {/* Session Status */}
        <Box mt={2} display="flex" gap={1} alignItems="center">
          <Chip
            label={`Sessão: ${sessionId?.substring(0, 8) || 'Não iniciada'}`}
            size="small"
            color="primary"
            variant="outlined"
          />
          <Chip
            label={`Estado: ${sessionState}`}
            size="small"
            color={sessionState === 'completed' ? 'success' : 'default'}
          />
          {projectData && (
            <Chip
              label={`Progresso: ${projectData.overall_progress?.total_progress_percentage || 0}%`}
              size="small"
              color="secondary"
            />
          )}
        </Box>
      </Paper>

      {/* Progress Indicator */}
      {sessionState === 'interviewing' && (
        <LinearProgress
          variant="determinate"
          value={(messages.filter(m => m.role === 'user').length / 9) * 100}
          sx={{ height: 6 }}
        />
      )}

      {/* Messages Area */}
      <Box sx={{ flex: 1, overflowY: 'auto', p: 2 }}>
        <AnimatePresence>
          {messages.map((message, index) => (
            <motion.div
              key={index}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.3 }}
            >
              <Box
                sx={{
                  display: 'flex',
                  justifyContent: message.role === 'user' ? 'flex-end' : 'flex-start',
                  mb: 2,
                }}
              >
                <Box
                  sx={{
                    display: 'flex',
                    gap: 1,
                    maxWidth: '70%',
                    flexDirection: message.role === 'user' ? 'row-reverse' : 'row',
                  }}
                >
                  <Avatar
                    sx={{
                      bgcolor: message.role === 'user' ? 'primary.main' : 'secondary.main',
                      width: 36,
                      height: 36,
                    }}
                  >
                    {message.role === 'user' ? <PersonIcon /> : <ConstructionIcon />}
                  </Avatar>
                  
                  <Paper
                    elevation={1}
                    sx={{
                      p: 2,
                      bgcolor: message.role === 'user' ? 'primary.light' : 'background.paper',
                      color: message.role === 'user' ? 'primary.contrastText' : 'text.primary',
                      borderRadius: 2,
                      ...(message.isError && { borderColor: 'error.main', borderWidth: 1, borderStyle: 'solid' }),
                    }}
                  >
                    {message.attachments && message.attachments.length > 0 && (
                      <Box mb={1}>
                        {message.attachments.map((att, i) => (
                          <Chip
                            key={i}
                            icon={<ImageIcon />}
                            label={att.name}
                            size="small"
                            sx={{ mr: 0.5 }}
                          />
                        ))}
                      </Box>
                    )}
                    
                    <ReactMarkdown>{message.content}</ReactMarkdown>
                    
                    {message.data && (
                      <Box mt={2}>
                        <Divider sx={{ my: 1 }} />
                        <Typography variant="caption" display="block" gutterBottom>
                          📊 Dados do Projeto
                        </Typography>
                        <Card variant="outlined">
                          <CardContent>
                            <Typography variant="body2">
                              ID: {message.data.project_id}
                            </Typography>
                          </CardContent>
                        </Card>
                      </Box>
                    )}
                    
                    <Typography variant="caption" display="block" mt={1} sx={{ opacity: 0.7 }}>
                      {new Date(message.timestamp).toLocaleTimeString('pt-BR')}
                    </Typography>
                  </Paper>
                </Box>
              </Box>
            </motion.div>
          ))}
        </AnimatePresence>
        
        {loading && (
          <Box display="flex" justifyContent="flex-start" mb={2}>
            <Box display="flex" gap={1} alignItems="center">
              <Avatar sx={{ bgcolor: 'secondary.main', width: 36, height: 36 }}>
                <ConstructionIcon />
              </Avatar>
              <Paper elevation={1} sx={{ p: 2, display: 'flex', alignItems: 'center', gap: 1 }}>
                <CircularProgress size={20} />
                <Typography>Analisando...</Typography>
              </Paper>
            </Box>
          </Box>
        )}
        
        <div ref={messagesEndRef} />
      </Box>

      {/* Input Area */}
      <Paper elevation={3} sx={{ p: 2, borderRadius: 0 }}>
        {/* Attachments */}
        {attachments.length > 0 && (
          <Box mb={2} display="flex" gap={1} flexWrap="wrap">
            {attachments.map((file, index) => (
              <Chip
                key={index}
                label={file.name}
                onDelete={() => setAttachments(prev => prev.filter((_, i) => i !== index))}
                icon={<ImageIcon />}
                color="primary"
                variant="outlined"
              />
            ))}
          </Box>
        )}
        
        {/* Dropzone */}
        <Box
          {...getRootProps()}
          sx={{
            border: isDragActive ? '2px dashed #1976d2' : '2px dashed transparent',
            borderRadius: 1,
            p: isDragActive ? 1 : 0,
            mb: 1,
            bgcolor: isDragActive ? 'action.hover' : 'transparent',
            transition: 'all 0.3s',
          }}
        >
          <input {...getInputProps()} />
          {isDragActive && (
            <Typography variant="body2" color="primary" align="center">
              Solte os arquivos aqui...
            </Typography>
          )}
        </Box>
        
        {/* Input Field */}
        <Box display="flex" gap={1}>
          <IconButton
            color="primary"
            component="label"
            disabled={loading}
          >
            <AttachFileIcon />
            <input
              type="file"
              hidden
              multiple
              accept="image/*,.pdf"
              onChange={(e) => setAttachments(prev => [...prev, ...Array.from(e.target.files)])}
            />
          </IconButton>
          
          <TextField
            fullWidth
            variant="outlined"
            placeholder="Digite sua mensagem..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyPress={handleKeyPress}
            disabled={loading}
            multiline
            maxRows={4}
            sx={{
              '& .MuiOutlinedInput-root': {
                borderRadius: 3,
              },
            }}
          />
          
          <IconButton
            color="primary"
            onClick={sendMessage}
            disabled={loading || (!input.trim() && attachments.length === 0)}
            sx={{
              bgcolor: 'primary.main',
              color: 'white',
              '&:hover': {
                bgcolor: 'primary.dark',
              },
              '&:disabled': {
                bgcolor: 'action.disabledBackground',
              },
            }}
          >
            <SendIcon />
          </IconButton>
        </Box>
        
        {/* Hints */}
        {sessionState === 'interviewing' && (
          <Alert severity="info" sx={{ mt: 2 }}>
            💡 Responda às perguntas para documentar sua obra. Envie fotos quando solicitado.
          </Alert>
        )}
      </Paper>
    </Box>
  );
};

export default ChatInterface;
