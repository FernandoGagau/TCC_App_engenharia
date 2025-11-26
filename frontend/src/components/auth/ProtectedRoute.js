/**
 * Protected Route Component
 * Ensures users are authenticated before accessing protected routes
 */

import React from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { CircularProgress, Box } from '@mui/material';
import { useAuthContext } from '../../contexts/AuthContext';

export function ProtectedRoute({
  children,
  requiredRole = null,
  redirectTo = '/login'
}) {
  const location = useLocation();
  const { isAuthenticated, loading, user, hasRole } = useAuthContext();

  // Show loading spinner while checking authentication
  if (loading) {
    return (
      <Box
        sx={{
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
          height: '100vh'
        }}
      >
        <CircularProgress />
      </Box>
    );
  }

  // Redirect to login if not authenticated
  if (!isAuthenticated) {
    // Save the attempted location for redirect after login
    return (
      <Navigate
        to={redirectTo}
        state={{ from: location }}
        replace
      />
    );
  }

  // Check role-based access if required
  if (requiredRole && !hasRole(requiredRole)) {
    // Redirect to unauthorized page or dashboard
    return (
      <Navigate
        to="/unauthorized"
        state={{ from: location }}
        replace
      />
    );
  }

  // User is authenticated and has required role (if specified)
  return children;
}

/**
 * Admin Route Component
 * Only allows admin users
 */
export function AdminRoute({ children }) {
  return (
    <ProtectedRoute requiredRole="admin">
      {children}
    </ProtectedRoute>
  );
}

/**
 * Manager Route Component
 * Allows manager and admin users
 */
export function ManagerRoute({ children }) {
  const { hasRole } = useAuthContext();

  // Allow both manager and admin roles
  if (hasRole('manager') || hasRole('admin')) {
    return <ProtectedRoute>{children}</ProtectedRoute>;
  }

  return (
    <Navigate
      to="/unauthorized"
      replace
    />
  );
}