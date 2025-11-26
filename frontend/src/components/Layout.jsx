import React from 'react';
import { Box, AppBar, Toolbar, Typography, Button, Container, IconButton, Menu, MenuItem, Avatar, Divider } from '@mui/material';
import { Link as RouterLink, Outlet, useNavigate } from 'react-router-dom';
import { Construction, Chat, Dashboard as DashboardIcon, History, Business, Logout, Person } from '@mui/icons-material';
import { useAuth } from '../contexts/AuthContext';

function Layout() {
  const navigate = useNavigate();
  const { user, logout } = useAuth();
  const [anchorEl, setAnchorEl] = React.useState(null);

  const handleMenu = (event) => {
    setAnchorEl(event.currentTarget);
  };

  const handleClose = () => {
    setAnchorEl(null);
  };

  const handleLogout = async () => {
    handleClose();
    await logout();
    navigate('/login');
  };

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', minHeight: '100vh' }}>
      <AppBar position="static">
        <Toolbar>
          <Construction sx={{ mr: 2 }} />
          <Typography variant="h6" component="div" sx={{ flexGrow: 1 }}>
            Agente de Análise de Obras
          </Typography>
          <Button
            color="inherit"
            component={RouterLink}
            to="/dashboard"
            startIcon={<DashboardIcon />}
          >
            Dashboard
          </Button>
          <Button
            color="inherit"
            component={RouterLink}
            to="/chat"
            startIcon={<Chat />}
          >
            Chat
          </Button>
          <Button
            color="inherit"
            component={RouterLink}
            to="/history"
            startIcon={<History />}
          >
            Histórico
          </Button>
          <Button
            color="inherit"
            component={RouterLink}
            to="/projects"
            startIcon={<Business />}
          >
            Obras
          </Button>

          {/* User Menu */}
          <IconButton
            size="large"
            onClick={handleMenu}
            color="inherit"
            sx={{ ml: 2 }}
          >
            <Avatar sx={{ width: 32, height: 32, bgcolor: 'secondary.main' }}>
              {user?.full_name?.charAt(0).toUpperCase() || user?.email?.charAt(0).toUpperCase() || 'U'}
            </Avatar>
          </IconButton>
          <Menu
            anchorEl={anchorEl}
            open={Boolean(anchorEl)}
            onClose={handleClose}
          >
            <MenuItem disabled>
              <Person sx={{ mr: 1 }} />
              {user?.full_name || user?.email}
            </MenuItem>
            <Divider />
            <MenuItem onClick={handleLogout}>
              <Logout sx={{ mr: 1 }} />
              Sair
            </MenuItem>
          </Menu>
        </Toolbar>
      </AppBar>
      <Container component="main" sx={{ flex: 1, py: 3 }}>
        <Outlet />
      </Container>
      <Box component="footer" sx={{ py: 2, px: 2, mt: 'auto', backgroundColor: '#f5f5f5' }}>
        <Typography variant="body2" color="text.secondary" align="center">
          © 2025 Agente de Análise de Obras
        </Typography>
      </Box>
    </Box>
  );
}

export default Layout;