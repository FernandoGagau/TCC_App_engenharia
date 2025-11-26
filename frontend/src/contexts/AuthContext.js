/**
 * Authentication Context
 * Manages user authentication state and provides auth methods
 */

import React, { createContext, useState, useContext, useEffect, useCallback } from 'react';
import axios from 'axios';
import API_BASE_URL from '../config/api';

// Create context
const AuthContext = createContext({});

// DO NOT set axios.defaults.baseURL globally!
// Each component uses API_BASE_URL explicitly
// Setting it globally can cause race conditions and caching issues
axios.defaults.headers.common['Content-Type'] = 'application/json';

// Token management
const TOKEN_KEY = 'access_token';
const REFRESH_TOKEN_KEY = 'refresh_token';
const USER_KEY = 'user_info';
const TOKEN_EXPIRY_KEY = 'token_expiry';

// Get stored tokens
const getAccessToken = () => localStorage.getItem(TOKEN_KEY);
const getRefreshToken = () => localStorage.getItem(REFRESH_TOKEN_KEY);
const getTokenExpiry = () => localStorage.getItem(TOKEN_EXPIRY_KEY);

// Set tokens with expiry
const setTokens = (accessToken, refreshToken, expiresIn = 43200) => {
  localStorage.setItem(TOKEN_KEY, accessToken);
  localStorage.setItem(REFRESH_TOKEN_KEY, refreshToken);

  // Calculate expiry timestamp (current time + expiresIn seconds)
  const expiryTimestamp = Date.now() + (expiresIn * 1000);
  localStorage.setItem(TOKEN_EXPIRY_KEY, expiryTimestamp.toString());
};

// Clear tokens
const clearTokens = () => {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(REFRESH_TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
  localStorage.removeItem(TOKEN_EXPIRY_KEY);
};

// Axios interceptor for adding auth header
axios.interceptors.request.use(
  (config) => {
    const token = getAccessToken();
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Axios interceptor for handling token refresh
let isRefreshing = false;
let refreshSubscribers = [];

const subscribeTokenRefresh = (callback) => {
  refreshSubscribers.push(callback);
};

const onTokenRefreshed = (token) => {
  refreshSubscribers.forEach((callback) => callback(token));
  refreshSubscribers = [];
};

axios.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    if (error.response?.status === 401 && !originalRequest._retry) {
      if (isRefreshing) {
        return new Promise((resolve) => {
          subscribeTokenRefresh((token) => {
            originalRequest.headers.Authorization = `Bearer ${token}`;
            resolve(axios(originalRequest));
          });
        });
      }

      originalRequest._retry = true;
      isRefreshing = true;

      const refreshToken = getRefreshToken();

      if (refreshToken) {
        try {
          const response = await axios.post(`${API_BASE_URL}/auth/refresh`, {
            refresh_token: refreshToken
          });

          const { access_token, expires_in } = response.data;

          // Update tokens with new expiration
          const currentRefreshToken = getRefreshToken();
          setTokens(access_token, currentRefreshToken, expires_in || 43200);

          axios.defaults.headers.common['Authorization'] = `Bearer ${access_token}`;

          isRefreshing = false;
          onTokenRefreshed(access_token);

          return axios(originalRequest);
        } catch (refreshError) {
          isRefreshing = false;
          clearTokens();
          window.location.href = '/login';
          return Promise.reject(refreshError);
        }
      }
    }

    return Promise.reject(error);
  }
);

// Auth Provider Component
export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [isAuthenticated, setIsAuthenticated] = useState(false);

  // Check token validity based on stored expiry timestamp
  const isTokenValid = useCallback(() => {
    try {
      const expiryStr = getTokenExpiry();
      if (!expiryStr) return false;

      const expiry = parseInt(expiryStr, 10);
      return expiry > Date.now();
    } catch {
      return false;
    }
  }, []);

  // Load user from storage
  const loadUser = useCallback(() => {
    const token = getAccessToken();
    const userStr = localStorage.getItem(USER_KEY);

    if (token && userStr && userStr !== 'undefined' && isTokenValid()) {
      try {
        const userData = JSON.parse(userStr);
        setUser(userData);
        setIsAuthenticated(true);
        return true;
      } catch (error) {
        console.error('Failed to parse user data:', error);
        clearTokens();
        setUser(null);
        setIsAuthenticated(false);
        return false;
      }
    }

    // If token is expired but refresh token exists, don't clear - let interceptor handle refresh
    if (token && userStr && userStr !== 'undefined' && getRefreshToken()) {
      try {
        // Keep user data but mark as not authenticated yet
        // The axios interceptor will try to refresh the token
        const userData = JSON.parse(userStr);
        setUser(userData);
        setIsAuthenticated(false);
        return false;
      } catch (error) {
        console.error('Failed to parse user data:', error);
        clearTokens();
        setUser(null);
        setIsAuthenticated(false);
        return false;
      }
    }

    clearTokens();
    setUser(null);
    setIsAuthenticated(false);
    return false;
  }, [isTokenValid]);

  // Initialize auth state
  useEffect(() => {
    loadUser();
    setLoading(false);
  }, [loadUser]);

  // Auto-refresh token before expiration
  useEffect(() => {
    if (!isAuthenticated) return;

    const checkTokenExpiry = async () => {
      const expiryStr = getTokenExpiry();
      if (!expiryStr) return;

      const expiry = parseInt(expiryStr, 10);
      const now = Date.now();
      const timeUntilExpiry = expiry - now;

      // If token expires in less than 30 minutes, refresh it
      const REFRESH_THRESHOLD = 30 * 60 * 1000; // 30 minutes in milliseconds

      if (timeUntilExpiry < REFRESH_THRESHOLD && timeUntilExpiry > 0) {
        try {
          const refreshToken = getRefreshToken();
          if (refreshToken) {
            const response = await axios.post(`${API_BASE_URL}/auth/refresh`, {
              refresh_token: refreshToken
            });

            const { access_token, expires_in } = response.data;

            // Update access token and expiry
            const currentRefreshToken = getRefreshToken();
            setTokens(access_token, currentRefreshToken, expires_in || 43200);

            console.log('Token refreshed successfully');
          }
        } catch (error) {
          console.error('Auto-refresh failed:', error);
          // If refresh fails, logout
          await logout();
        }
      }
    };

    // Check every 5 minutes
    const interval = setInterval(checkTokenExpiry, 5 * 60 * 1000);

    // Check immediately
    checkTokenExpiry();

    return () => clearInterval(interval);
  }, [isAuthenticated]);

  // Login
  const login = async (email, password, rememberMe = false) => {
    try {
      console.log('🔐 Login attempt to:', `${API_BASE_URL}/auth/login`);
      const response = await axios.post(`${API_BASE_URL}/auth/login`, {
        email,
        password,
        remember_me: rememberMe
      });

      const { access_token, refresh_token, user, expires_in } = response.data;

      // Store tokens with expiration
      setTokens(access_token, refresh_token, expires_in || 43200);

      // Store user info
      localStorage.setItem(USER_KEY, JSON.stringify(user));

      // Update state
      setUser(user);
      setIsAuthenticated(true);

      return response.data;
    } catch (error) {
      console.error('Login error:', error);
      throw error;
    }
  };

  // Register
  const register = async (userData) => {
    try {
      const response = await axios.post(`${API_BASE_URL}/auth/register`, userData);

      const { access_token, refresh_token, user, expires_in } = response.data;

      // Store tokens with expiration
      setTokens(access_token, refresh_token, expires_in || 43200);

      // Store user info
      localStorage.setItem(USER_KEY, JSON.stringify(user));

      // Update state
      setUser(user);
      setIsAuthenticated(true);

      return response.data;
    } catch (error) {
      console.error('Register error:', error);
      throw error;
    }
  };

  // Logout
  const logout = async () => {
    try {
      // Call logout endpoint
      await axios.post(`${API_BASE_URL}/auth/logout`);
    } catch (error) {
      console.error('Logout error:', error);
    } finally {
      // Clear local storage
      clearTokens();

      // Update state
      setUser(null);
      setIsAuthenticated(false);
    }
  };

  // Get current user info
  const getCurrentUser = async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/auth/me`);
      const userData = response.data;

      // Update user info
      localStorage.setItem(USER_KEY, JSON.stringify(userData));
      setUser(userData);

      return userData;
    } catch (error) {
      console.error('Get user error:', error);
      throw error;
    }
  };

  // Change password
  const changePassword = async (currentPassword, newPassword, confirmPassword) => {
    try {
      await axios.post(`${API_BASE_URL}/auth/change-password`, {
        current_password: currentPassword,
        new_password: newPassword,
        confirm_password: confirmPassword
      });

      // Password changed successfully, tokens are revoked
      // User needs to login again
      await logout();
      return true;
    } catch (error) {
      console.error('Change password error:', error);
      throw error;
    }
  };

  // Request password reset
  const requestPasswordReset = async (email) => {
    try {
      await axios.post(`${API_BASE_URL}/auth/reset-password`, { email });
      return true;
    } catch (error) {
      console.error('Password reset request error:', error);
      throw error;
    }
  };

  // Confirm password reset
  const confirmPasswordReset = async (token, newPassword, confirmPassword) => {
    try {
      await axios.post(`${API_BASE_URL}/auth/reset-password/confirm`, {
        token,
        new_password: newPassword,
        confirm_password: confirmPassword
      });
      return true;
    } catch (error) {
      console.error('Password reset confirm error:', error);
      throw error;
    }
  };

  // Check if user has role
  const hasRole = useCallback((role) => {
    return user?.role === role;
  }, [user]);

  // Check if user has permission
  const hasPermission = useCallback((permission) => {
    return user?.permissions?.includes(permission) || false;
  }, [user]);

  // Context value
  const value = {
    user,
    loading,
    isAuthenticated,
    login,
    register,
    logout,
    getCurrentUser,
    changePassword,
    requestPasswordReset,
    confirmPasswordReset,
    hasRole,
    hasPermission,
    getAccessToken,
    getRefreshToken
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};

// Custom hook to use auth context
export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

// HOC for protecting components
export const withAuth = (Component) => {
  return (props) => {
    const { isAuthenticated, loading } = useAuth();

    if (loading) {
      return <div>Loading...</div>;
    }

    if (!isAuthenticated) {
      window.location.href = '/login';
      return null;
    }

    return <Component {...props} />;
  };
};

// Protected Route Component
export const ProtectedRoute = ({ children, roles = [], permissions = [] }) => {
  const { isAuthenticated, loading, hasRole, hasPermission } = useAuth();

  if (loading) {
    return <div>Loading...</div>;
  }

  if (!isAuthenticated) {
    window.location.href = '/login';
    return null;
  }

  // Check roles
  if (roles.length > 0) {
    const hasRequiredRole = roles.some((role) => hasRole(role));
    if (!hasRequiredRole) {
      return <div>Access denied. Insufficient role.</div>;
    }
  }

  // Check permissions
  if (permissions.length > 0) {
    const hasRequiredPermission = permissions.some((perm) => hasPermission(perm));
    if (!hasRequiredPermission) {
      return <div>Access denied. Insufficient permissions.</div>;
    }
  }

  return children;
};

export default AuthContext;