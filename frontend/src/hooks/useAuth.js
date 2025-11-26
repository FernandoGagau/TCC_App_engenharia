/**
 * React Hook for Authentication
 * Provides authentication state and actions
 */

import { useState, useEffect, useCallback } from 'react';
import authService from '../services/auth.service';

export function useAuth() {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  /**
   * Load user from token on mount
   */
  useEffect(() => {
    const loadUser = async () => {
      try {
        if (authService.isAuthenticated()) {
          const userData = await authService.getCurrentUser();
          setUser(userData);
          localStorage.setItem('user', JSON.stringify(userData));
        } else {
          const storedUser = localStorage.getItem('user');
          if (storedUser && storedUser !== 'undefined') {
            try {
              setUser(JSON.parse(storedUser));
            } catch (error) {
              console.error('Failed to parse stored user:', error);
              localStorage.removeItem('user');
            }
          }
        }
      } catch (err) {
        console.error('Failed to load user:', err);
        authService.logout();
        setUser(null);
      } finally {
        setLoading(false);
      }
    };

    loadUser();
  }, []);

  /**
   * Login function
   */
  const login = useCallback(async (email, password) => {
    setLoading(true);
    setError(null);

    try {
      const result = await authService.login(email, password);

      if (result.success) {
        setUser(result.user);
        localStorage.setItem('user', JSON.stringify(result.user));
        return { success: true };
      } else {
        setError(result.error);
        return { success: false, error: result.error };
      }
    } catch (err) {
      const errorMessage = 'Login failed. Please try again.';
      setError(errorMessage);
      return { success: false, error: errorMessage };
    } finally {
      setLoading(false);
    }
  }, []);

  /**
   * Register function
   */
  const register = useCallback(async (email, username, password, fullName) => {
    setLoading(true);
    setError(null);

    try {
      const result = await authService.register(email, username, password, fullName);

      if (result.success) {
        // Auto-login after successful registration
        const loginResult = await authService.login(email, password);

        if (loginResult.success) {
          setUser(loginResult.user);
          localStorage.setItem('user', JSON.stringify(loginResult.user));
        }

        return { success: true, user: result.user };
      } else {
        setError(result.error);
        return { success: false, error: result.error };
      }
    } catch (err) {
      const errorMessage = 'Registration failed. Please try again.';
      setError(errorMessage);
      return { success: false, error: errorMessage };
    } finally {
      setLoading(false);
    }
  }, []);

  /**
   * Logout function
   */
  const logout = useCallback(async () => {
    setLoading(true);

    try {
      await authService.logout();
      setUser(null);
      localStorage.removeItem('user');
    } catch (err) {
      console.error('Logout error:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  /**
   * Update user profile
   */
  const updateProfile = useCallback(async (fullName, avatarUrl) => {
    setLoading(true);
    setError(null);

    try {
      const response = await fetch(`${authService.baseUrl}/auth/me`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${authService.getAccessToken()}`
        },
        body: JSON.stringify({
          full_name: fullName,
          avatar_url: avatarUrl
        })
      });

      if (!response.ok) {
        throw new Error('Profile update failed');
      }

      const updatedUser = await response.json();
      setUser(updatedUser);
      localStorage.setItem('user', JSON.stringify(updatedUser));

      return { success: true, user: updatedUser };
    } catch (err) {
      const errorMessage = 'Failed to update profile';
      setError(errorMessage);
      return { success: false, error: errorMessage };
    } finally {
      setLoading(false);
    }
  }, []);

  /**
   * Change password
   */
  const changePassword = useCallback(async (currentPassword, newPassword) => {
    setLoading(true);
    setError(null);

    try {
      const result = await authService.changePassword(currentPassword, newPassword);

      if (result.success) {
        return { success: true, message: result.message };
      } else {
        setError(result.error);
        return { success: false, error: result.error };
      }
    } catch (err) {
      const errorMessage = 'Password change failed';
      setError(errorMessage);
      return { success: false, error: errorMessage };
    } finally {
      setLoading(false);
    }
  }, []);

  /**
   * Request password reset
   */
  const requestPasswordReset = useCallback(async (email) => {
    setLoading(true);
    setError(null);

    try {
      const result = await authService.requestPasswordReset(email);

      if (result.success) {
        return { success: true, message: result.message };
      } else {
        setError(result.error);
        return { success: false, error: result.error };
      }
    } catch (err) {
      const errorMessage = 'Password reset request failed';
      setError(errorMessage);
      return { success: false, error: errorMessage };
    } finally {
      setLoading(false);
    }
  }, []);

  /**
   * Confirm password reset
   */
  const confirmPasswordReset = useCallback(async (token, newPassword) => {
    setLoading(true);
    setError(null);

    try {
      const result = await authService.confirmPasswordReset(token, newPassword);

      if (result.success) {
        return { success: true, message: result.message };
      } else {
        setError(result.error);
        return { success: false, error: result.error };
      }
    } catch (err) {
      const errorMessage = 'Password reset failed';
      setError(errorMessage);
      return { success: false, error: errorMessage };
    } finally {
      setLoading(false);
    }
  }, []);

  /**
   * Check if user has specific role
   */
  const hasRole = useCallback((role) => {
    if (!user || !user.roles) return false;
    return user.roles.includes(role);
  }, [user]);

  /**
   * Check if user is admin
   */
  const isAdmin = useCallback(() => {
    return hasRole('admin');
  }, [hasRole]);

  /**
   * Check if user is manager
   */
  const isManager = useCallback(() => {
    return hasRole('manager') || hasRole('admin');
  }, [hasRole]);

  /**
   * Clear error
   */
  const clearError = useCallback(() => {
    setError(null);
  }, []);

  return {
    user,
    loading,
    error,
    isAuthenticated: !!user,
    login,
    register,
    logout,
    updateProfile,
    changePassword,
    requestPasswordReset,
    confirmPasswordReset,
    hasRole,
    isAdmin,
    isManager,
    clearError
  };
}