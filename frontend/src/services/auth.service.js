/**
 * Authentication Service
 * Handles JWT authentication with automatic token refresh
 */

import axios from 'axios';
import API_BASE_URL from '../config/api';

class AuthService {
  constructor() {
    // Remove /api from the base URL for auth endpoints
    this.baseUrl = API_BASE_URL.replace(/\/api$/, '');
    this.tokenRefreshPromise = null;
    this.refreshIntervalId = null;

    // Initialize axios interceptors
    // this.setupInterceptors();

    // Start token refresh timer if user is logged in
    if (this.getAccessToken()) {
      this.startTokenRefreshTimer();
    }
  }

  /**
   * Setup axios interceptors for automatic token handling
   */
  setupInterceptors() {
    // Request interceptor to add token
    axios.interceptors.request.use(
      (config) => {
        const token = this.getAccessToken();
        if (token) {
          config.headers['Authorization'] = `Bearer ${token}`;
        }
        return config;
      },
      (error) => Promise.reject(error)
    );

    // Response interceptor to handle token refresh
    axios.interceptors.response.use(
      (response) => response,
      async (error) => {
        const originalRequest = error.config;

        if (error.response?.status === 401 && !originalRequest._retry) {
          originalRequest._retry = true;

          try {
            await this.refreshToken();
            const token = this.getAccessToken();
            originalRequest.headers['Authorization'] = `Bearer ${token}`;
            return axios(originalRequest);
          } catch (refreshError) {
            this.logout();
            window.location.href = '/login';
            return Promise.reject(refreshError);
          }
        }

        return Promise.reject(error);
      }
    );
  }

  /**
   * Register new user
   */
  async register(email, username, password, fullName = null) {
    try {
      const response = await axios.post(`${this.baseUrl}/auth/register`, {
        email,
        username,
        password,
        full_name: fullName
      });

      return {
        success: true,
        user: response.data
      };
    } catch (error) {
      return {
        success: false,
        error: error.response?.data?.detail || 'Registration failed'
      };
    }
  }

  /**
   * Login user
   */
  async login(email, password) {
    try {
      const response = await axios.post(`${this.baseUrl}/auth/login`, {
        email,
        password
      });

      const { access_token, refresh_token, expires_in } = response.data;

      // Store tokens
      this.setTokens(access_token, refresh_token);

      // Calculate and store expiry time
      const expiryTime = new Date().getTime() + (expires_in * 1000);
      localStorage.setItem('token_expiry', expiryTime.toString());

      // Start refresh timer
      this.startTokenRefreshTimer();

      // Get user info
      const userInfo = await this.getCurrentUser();

      return {
        success: true,
        user: userInfo
      };
    } catch (error) {
      return {
        success: false,
        error: error.response?.data?.detail || 'Login failed'
      };
    }
  }

  /**
   * Logout user
   */
  async logout() {
    const refreshToken = this.getRefreshToken();

    // Call logout endpoint if we have a token
    if (refreshToken) {
      try {
        await axios.post(
          `${this.baseUrl}/auth/logout`,
          { refresh_token: refreshToken },
          {
            headers: {
              'Authorization': `Bearer ${this.getAccessToken()}`
            }
          }
        );
      } catch (error) {
        console.error('Logout API call failed:', error);
      }
    }

    // Clear local storage
    this.clearTokens();

    // Stop refresh timer
    this.stopTokenRefreshTimer();
  }

  /**
   * Refresh access token
   */
  async refreshToken() {
    // Prevent multiple simultaneous refresh calls
    if (this.tokenRefreshPromise) {
      return this.tokenRefreshPromise;
    }

    const refreshToken = this.getRefreshToken();

    if (!refreshToken) {
      throw new Error('No refresh token available');
    }

    this.tokenRefreshPromise = axios.post(`${this.baseUrl}/auth/refresh`, {
      refresh_token: refreshToken
    })
      .then((response) => {
        const { access_token, refresh_token, expires_in } = response.data;

        // Update tokens
        this.setTokens(access_token, refresh_token);

        // Update expiry time
        const expiryTime = new Date().getTime() + (expires_in * 1000);
        localStorage.setItem('token_expiry', expiryTime.toString());

        return response.data;
      })
      .finally(() => {
        this.tokenRefreshPromise = null;
      });

    return this.tokenRefreshPromise;
  }

  /**
   * Get current user info
   */
  async getCurrentUser() {
    try {
      const response = await axios.get(`${this.baseUrl}/auth/me`);
      return response.data;
    } catch (error) {
      throw new Error('Failed to get user info');
    }
  }

  /**
   * Change password
   */
  async changePassword(currentPassword, newPassword) {
    try {
      const response = await axios.post(`${this.baseUrl}/auth/change-password`, {
        current_password: currentPassword,
        new_password: newPassword
      });

      return {
        success: true,
        message: response.data.message
      };
    } catch (error) {
      return {
        success: false,
        error: error.response?.data?.detail || 'Password change failed'
      };
    }
  }

  /**
   * Request password reset
   */
  async requestPasswordReset(email) {
    try {
      const response = await axios.post(`${this.baseUrl}/auth/reset-password`, {
        email
      });

      return {
        success: true,
        message: response.data.message
      };
    } catch (error) {
      return {
        success: false,
        error: error.response?.data?.detail || 'Password reset request failed'
      };
    }
  }

  /**
   * Confirm password reset
   */
  async confirmPasswordReset(token, newPassword) {
    try {
      const response = await axios.post(`${this.baseUrl}/auth/reset-password/confirm`, {
        token,
        new_password: newPassword
      });

      return {
        success: true,
        message: response.data.message
      };
    } catch (error) {
      return {
        success: false,
        error: error.response?.data?.detail || 'Password reset failed'
      };
    }
  }

  /**
   * Start automatic token refresh timer
   */
  startTokenRefreshTimer() {
    this.stopTokenRefreshTimer();

    // Check token expiry every minute
    this.refreshIntervalId = setInterval(async () => {
      const expiryTime = localStorage.getItem('token_expiry');

      if (!expiryTime) {
        this.stopTokenRefreshTimer();
        return;
      }

      const now = new Date().getTime();
      const expiry = parseInt(expiryTime);
      const timeUntilExpiry = expiry - now;

      // Refresh if less than 5 minutes until expiry
      if (timeUntilExpiry < 5 * 60 * 1000) {
        try {
          await this.refreshToken();
        } catch (error) {
          console.error('Token refresh failed:', error);
          this.logout();
        }
      }
    }, 60000); // Check every minute
  }

  /**
   * Stop token refresh timer
   */
  stopTokenRefreshTimer() {
    if (this.refreshIntervalId) {
      clearInterval(this.refreshIntervalId);
      this.refreshIntervalId = null;
    }
  }

  /**
   * Token management helpers
   */
  setTokens(accessToken, refreshToken) {
    localStorage.setItem('access_token', accessToken);
    localStorage.setItem('refresh_token', refreshToken);
  }

  clearTokens() {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    localStorage.removeItem('token_expiry');
    localStorage.removeItem('user');
  }

  getAccessToken() {
    return localStorage.getItem('access_token');
  }

  getRefreshToken() {
    return localStorage.getItem('refresh_token');
  }

  isAuthenticated() {
    return !!this.getAccessToken();
  }

  /**
   * Check if token is expired
   */
  isTokenExpired() {
    const expiryTime = localStorage.getItem('token_expiry');

    if (!expiryTime) {
      return true;
    }

    const now = new Date().getTime();
    const expiry = parseInt(expiryTime);

    return now >= expiry;
  }
}

// Create singleton instance
const authService = new AuthService();

export default authService;