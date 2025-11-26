/**
 * Login Page Component
 * Handles user authentication with JWT
 */

import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import {
  Box,
  Container,
  Paper,
  TextField,
  Button,
  Typography,
  IconButton,
  InputAdornment,
  Alert,
  Checkbox,
  FormControlLabel,
  Divider,
  CircularProgress,
  Link as MuiLink
} from '@mui/material';
import {
  Visibility,
  VisibilityOff,
  Email,
  Lock,
  Construction,
  Engineering
} from '@mui/icons-material';
import { motion, AnimatePresence } from 'framer-motion';
import { useAuth } from '../contexts/AuthContext';

const Login = () => {
  const navigate = useNavigate();
  const { login } = useAuth();

  // Form state
  const [formData, setFormData] = useState({
    email: '',
    password: '',
    rememberMe: false
  });

  // UI state
  const [showPassword, setShowPassword] = useState(false);
  const [errors, setErrors] = useState({});
  const [loading, setLoading] = useState(false);
  const [globalError, setGlobalError] = useState('');

  // Validation
  const validateForm = () => {
    const newErrors = {};

    if (!formData.email) {
      newErrors.email = 'E-mail é obrigatório';
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formData.email)) {
      newErrors.email = 'E-mail inválido';
    }

    if (!formData.password) {
      newErrors.password = 'Senha é obrigatória';
    } else if (formData.password.length < 8) {
      newErrors.password = 'A senha deve ter pelo menos 8 caracteres';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  // Handlers
  const handleChange = (e) => {
    const { name, value, checked } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: name === 'rememberMe' ? checked : value
    }));

    // Clear field error
    if (errors[name]) {
      setErrors(prev => ({
        ...prev,
        [name]: ''
      }));
    }
    setGlobalError('');
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (!validateForm()) {
      return;
    }

    setLoading(true);
    setGlobalError('');

    try {
      await login(formData.email, formData.password, formData.rememberMe);
      navigate('/dashboard');
    } catch (error) {
      console.error('Login error:', error);

      if (error.response?.status === 423) {
        setGlobalError('Conta bloqueada devido a múltiplas tentativas. Tente novamente mais tarde.');
      } else if (error.response?.status === 403) {
        setGlobalError('Sua conta foi desativada. Entre em contato com o suporte.');
      } else if (error.response?.status === 401) {
        setGlobalError('E-mail ou senha inválidos');
      } else {
        setGlobalError('Falha no login. Tente novamente.');
      }
    } finally {
      setLoading(false);
    }
  };

  const handleDemoLogin = () => {
    // Just fill the form with demo credentials, don't auto-submit
    const demoData = {
      email: 'demo@example.com',
      password: 'Demo@123',
      rememberMe: false
    };
    setFormData(demoData);
    setGlobalError('');
  };

  return (
    <Box
      sx={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
        py: 4
      }}
    >
      <Container maxWidth="sm">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
        >
          <Paper
            elevation={10}
            sx={{
              p: 4,
              borderRadius: 2,
              position: 'relative',
              overflow: 'hidden'
            }}
          >
            {/* Header */}
            <Box sx={{ textAlign: 'center', mb: 4 }}>
              <motion.div
                initial={{ scale: 0 }}
                animate={{ scale: 1 }}
                transition={{ delay: 0.2, type: 'spring' }}
              >
                <Box sx={{ display: 'flex', justifyContent: 'center', mb: 2 }}>
                  <Engineering sx={{ fontSize: 48, color: 'primary.main', mr: 1 }} />
                  <Construction sx={{ fontSize: 48, color: 'secondary.main' }} />
                </Box>
              </motion.div>

              <Typography variant="h4" fontWeight="bold" gutterBottom>
                Bem-vindo de Volta
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Entre na Plataforma de Análise de Obras
              </Typography>
            </Box>

            {/* Error Alert */}
            <AnimatePresence>
              {globalError && (
                <motion.div
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: 'auto' }}
                  exit={{ opacity: 0, height: 0 }}
                >
                  <Alert severity="error" sx={{ mb: 2 }}>
                    {globalError}
                  </Alert>
                </motion.div>
              )}
            </AnimatePresence>

            {/* Form */}
            <Box component="form" onSubmit={handleSubmit}>
              <TextField
                fullWidth
                name="email"
                label="E-mail"
                type="email"
                value={formData.email}
                onChange={handleChange}
                error={!!errors.email}
                helperText={errors.email}
                disabled={loading}
                InputProps={{
                  startAdornment: (
                    <InputAdornment position="start">
                      <Email />
                    </InputAdornment>
                  )
                }}
                sx={{ mb: 2 }}
                autoComplete="email"
                autoFocus
              />

              <TextField
                fullWidth
                name="password"
                label="Senha"
                type={showPassword ? 'text' : 'password'}
                value={formData.password}
                onChange={handleChange}
                error={!!errors.password}
                helperText={errors.password}
                disabled={loading}
                InputProps={{
                  startAdornment: (
                    <InputAdornment position="start">
                      <Lock />
                    </InputAdornment>
                  ),
                  endAdornment: (
                    <InputAdornment position="end">
                      <IconButton
                        onClick={() => setShowPassword(!showPassword)}
                        edge="end"
                        disabled={loading}
                      >
                        {showPassword ? <VisibilityOff /> : <Visibility />}
                      </IconButton>
                    </InputAdornment>
                  )
                }}
                sx={{ mb: 1 }}
                autoComplete="current-password"
              />

              {/* Options Row */}
              <Box sx={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                mb: 3
              }}>
                <FormControlLabel
                  control={
                    <Checkbox
                      name="rememberMe"
                      checked={formData.rememberMe}
                      onChange={handleChange}
                      disabled={loading}
                    />
                  }
                  label="Lembrar-me"
                />

                <MuiLink
                  component={Link}
                  to="/reset-password"
                  variant="body2"
                  sx={{ textDecoration: 'none' }}
                >
                  Esqueceu a senha?
                </MuiLink>
              </Box>

              {/* Submit Button */}
              <Button
                fullWidth
                type="submit"
                variant="contained"
                size="large"
                disabled={loading}
                sx={{
                  mb: 2,
                  py: 1.5,
                  position: 'relative'
                }}
              >
                {loading ? (
                  <CircularProgress size={24} color="inherit" />
                ) : (
                  'ENTRAR'
                )}
              </Button>

              {/* Demo Account */}
              <Button
                fullWidth
                variant="outlined"
                onClick={handleDemoLogin}
                disabled={loading}
                sx={{ mb: 2 }}
              >
                PREENCHER CREDENCIAIS DE DEMONSTRAÇÃO
              </Button>

              <Divider sx={{ my: 3 }}>OU</Divider>

              {/* Register Link */}
              <Box sx={{ textAlign: 'center' }}>
                <Typography variant="body2">
                  Não tem uma conta?{' '}
                  <MuiLink
                    component={Link}
                    to="/register"
                    sx={{ fontWeight: 'bold', textDecoration: 'none' }}
                  >
                    Cadastre-se
                  </MuiLink>
                </Typography>
              </Box>
            </Box>

            {/* Decorative Elements */}
            <Box
              sx={{
                position: 'absolute',
                top: -50,
                right: -50,
                width: 100,
                height: 100,
                borderRadius: '50%',
                background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                opacity: 0.1
              }}
            />
            <Box
              sx={{
                position: 'absolute',
                bottom: -30,
                left: -30,
                width: 80,
                height: 80,
                borderRadius: '50%',
                background: 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)',
                opacity: 0.1
              }}
            />
          </Paper>
        </motion.div>
      </Container>
    </Box>
  );
};

export default Login;