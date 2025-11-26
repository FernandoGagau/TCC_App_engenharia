/**
 * Register Page Component
 * Handles new user registration with validation
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
  Divider,
  CircularProgress,
  Link as MuiLink,
  LinearProgress,
  Stepper,
  Step,
  StepLabel,
  Chip
} from '@mui/material';
import {
  Visibility,
  VisibilityOff,
  Email,
  Lock,
  Person,
  Construction,
  Engineering,
  CheckCircle,
  Cancel
} from '@mui/icons-material';
import { motion, AnimatePresence } from 'framer-motion';
import { useAuth } from '../contexts/AuthContext';

const PasswordStrengthIndicator = ({ password }) => {
  const getStrength = () => {
    if (!password) return 0;

    let strength = 0;

    // Length
    if (password.length >= 8) strength += 20;
    if (password.length >= 12) strength += 10;

    // Uppercase
    if (/[A-Z]/.test(password)) strength += 20;

    // Lowercase
    if (/[a-z]/.test(password)) strength += 20;

    // Numbers
    if (/\d/.test(password)) strength += 20;

    // Special characters
    if (/[!@#$%^&*(),.?":{}|<>]/.test(password)) strength += 10;

    return Math.min(strength, 100);
  };

  const strength = getStrength();

  const getColor = () => {
    if (strength < 30) return 'error';
    if (strength < 60) return 'warning';
    if (strength < 80) return 'info';
    return 'success';
  };

  const getLabel = () => {
    if (strength < 30) return 'Fraca';
    if (strength < 60) return 'Razoável';
    if (strength < 80) return 'Boa';
    return 'Forte';
  };

  if (!password) return null;

  return (
    <Box sx={{ mt: 1, mb: 2 }}>
      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 0.5 }}>
        <Typography variant="caption" color="text.secondary">
          Força da Senha
        </Typography>
        <Chip
          label={getLabel()}
          color={getColor()}
          size="small"
        />
      </Box>
      <LinearProgress
        variant="determinate"
        value={strength}
        color={getColor()}
        sx={{ height: 6, borderRadius: 3 }}
      />
    </Box>
  );
};

const PasswordRequirements = ({ password }) => {
  const requirements = [
    { label: 'Pelo menos 8 caracteres', test: password.length >= 8 },
    { label: 'Uma letra maiúscula', test: /[A-Z]/.test(password) },
    { label: 'Uma letra minúscula', test: /[a-z]/.test(password) },
    { label: 'Um número', test: /\d/.test(password) },
    { label: 'Um caractere especial', test: /[!@#$%^&*(),.?":{}|<>]/.test(password) }
  ];

  if (!password) return null;

  return (
    <Box sx={{ mt: 1, mb: 2 }}>
      {requirements.map((req, index) => (
        <Box
          key={index}
          sx={{
            display: 'flex',
            alignItems: 'center',
            gap: 1,
            mb: 0.5
          }}
        >
          {req.test ? (
            <CheckCircle fontSize="small" color="success" />
          ) : (
            <Cancel fontSize="small" color="disabled" />
          )}
          <Typography
            variant="caption"
            color={req.test ? 'text.primary' : 'text.secondary'}
          >
            {req.label}
          </Typography>
        </Box>
      ))}
    </Box>
  );
};

const Register = () => {
  const navigate = useNavigate();
  const { register } = useAuth();

  // Form state
  const [formData, setFormData] = useState({
    email: '',
    username: '',
    fullName: '',
    password: '',
    confirmPassword: ''
  });

  // UI state
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [errors, setErrors] = useState({});
  const [loading, setLoading] = useState(false);
  const [globalError, setGlobalError] = useState('');
  const [successMessage, setSuccessMessage] = useState('');
  const [activeStep] = useState(0);

  // Validation
  const validateForm = () => {
    const newErrors = {};

    // Email validation
    if (!formData.email) {
      newErrors.email = 'E-mail é obrigatório';
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formData.email)) {
      newErrors.email = 'Formato de e-mail inválido';
    }

    // Username validation
    if (!formData.username) {
      newErrors.username = 'Nome de usuário é obrigatório';
    } else if (formData.username.length < 3) {
      newErrors.username = 'Nome de usuário deve ter pelo menos 3 caracteres';
    } else if (!/^[a-zA-Z0-9_-]+$/.test(formData.username)) {
      newErrors.username = 'Nome de usuário pode conter apenas letras, números, _ e -';
    }

    // Full name validation
    if (!formData.fullName) {
      newErrors.fullName = 'Nome completo é obrigatório';
    } else if (formData.fullName.trim().length < 2) {
      newErrors.fullName = 'Nome completo deve ter pelo menos 2 caracteres';
    }

    // Password validation
    if (!formData.password) {
      newErrors.password = 'Senha é obrigatória';
    } else {
      const passwordErrors = [];
      if (formData.password.length < 8) {
        passwordErrors.push('pelo menos 8 caracteres');
      }
      if (!/[A-Z]/.test(formData.password)) {
        passwordErrors.push('uma letra maiúscula');
      }
      if (!/[a-z]/.test(formData.password)) {
        passwordErrors.push('uma letra minúscula');
      }
      if (!/\d/.test(formData.password)) {
        passwordErrors.push('um número');
      }
      if (!/[!@#$%^&*(),.?":{}|<>]/.test(formData.password)) {
        passwordErrors.push('um caractere especial');
      }

      if (passwordErrors.length > 0) {
        newErrors.password = `A senha deve conter ${passwordErrors.join(', ')}`;
      }
    }

    // Confirm password validation
    if (!formData.confirmPassword) {
      newErrors.confirmPassword = 'Por favor, confirme sua senha';
    } else if (formData.password !== formData.confirmPassword) {
      newErrors.confirmPassword = 'As senhas não coincidem';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  // Handlers
  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
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
    setSuccessMessage('');

    try {
      await register({
        email: formData.email,
        username: formData.username,
        full_name: formData.fullName,
        password: formData.password,
        confirm_password: formData.confirmPassword
      });

      setSuccessMessage('Cadastro realizado com sucesso! Redirecionando...');
      setTimeout(() => {
        navigate('/dashboard');
      }, 1500);
    } catch (error) {
      console.error('Registration error:', error);

      if (error.response?.status === 409) {
        const detail = error.response.data?.detail;
        if (detail?.includes('Email')) {
          setErrors({ email: 'E-mail já cadastrado' });
        } else if (detail?.includes('Username')) {
          setErrors({ username: 'Nome de usuário já está em uso' });
        } else {
          setGlobalError(detail || 'Conta já existe');
        }
      } else if (error.response?.status === 400) {
        setGlobalError(error.response.data?.detail || 'Dados de cadastro inválidos');
      } else {
        setGlobalError('Falha no cadastro. Tente novamente.');
      }
    } finally {
      setLoading(false);
    }
  };

  const steps = ['Informações da Conta', 'Segurança', 'Confirmar'];


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
            <Box sx={{ textAlign: 'center', mb: 3 }}>
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
                Criar Conta
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Junte-se à Plataforma de Análise de Obras
              </Typography>
            </Box>

            {/* Stepper */}
            <Stepper activeStep={activeStep} sx={{ mb: 3 }}>
              {steps.map((label) => (
                <Step key={label}>
                  <StepLabel>{label}</StepLabel>
                </Step>
              ))}
            </Stepper>

            {/* Alerts */}
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

              {successMessage && (
                <motion.div
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: 'auto' }}
                  exit={{ opacity: 0, height: 0 }}
                >
                  <Alert severity="success" sx={{ mb: 2 }}>
                    {successMessage}
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
              />

              <TextField
                fullWidth
                name="username"
                label="Nome de Usuário"
                value={formData.username}
                onChange={handleChange}
                error={!!errors.username}
                helperText={errors.username}
                disabled={loading}
                InputProps={{
                  startAdornment: (
                    <InputAdornment position="start">
                      <Person />
                    </InputAdornment>
                  )
                }}
                sx={{ mb: 2 }}
                autoComplete="username"
              />

              <TextField
                fullWidth
                name="fullName"
                label="Nome Completo"
                value={formData.fullName}
                onChange={handleChange}
                error={!!errors.fullName}
                helperText={errors.fullName}
                disabled={loading}
                InputProps={{
                  startAdornment: (
                    <InputAdornment position="start">
                      <Person />
                    </InputAdornment>
                  )
                }}
                sx={{ mb: 2 }}
                autoComplete="name"
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
                autoComplete="new-password"
              />

              <PasswordStrengthIndicator password={formData.password} />
              <PasswordRequirements password={formData.password} />

              <TextField
                fullWidth
                name="confirmPassword"
                label="Confirmar Senha"
                type={showConfirmPassword ? 'text' : 'password'}
                value={formData.confirmPassword}
                onChange={handleChange}
                error={!!errors.confirmPassword}
                helperText={errors.confirmPassword}
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
                        onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                        edge="end"
                        disabled={loading}
                      >
                        {showConfirmPassword ? <VisibilityOff /> : <Visibility />}
                      </IconButton>
                    </InputAdornment>
                  )
                }}
                sx={{ mb: 3 }}
                autoComplete="new-password"
              />

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
                  'CRIAR CONTA'
                )}
              </Button>

              <Divider sx={{ my: 3 }}>OU</Divider>

              {/* Login Link */}
              <Box sx={{ textAlign: 'center' }}>
                <Typography variant="body2">
                  Já tem uma conta?{' '}
                  <MuiLink
                    component={Link}
                    to="/login"
                    sx={{ fontWeight: 'bold', textDecoration: 'none' }}
                  >
                    Entrar
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

export default Register;