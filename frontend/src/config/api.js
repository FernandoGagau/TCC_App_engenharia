/**
 * Centralize backend API URL handling and guarantee we never trigger mixed-content
 * issues when the frontend is served through HTTPS (e.g. Railway).
 */

const rawEnvUrl = (process.env.REACT_APP_BACKEND_URL || '').trim();

const isBrowser = typeof window !== 'undefined';
const isSecurePage = () => isBrowser && window.location?.protocol === 'https:';
const currentOrigin = () => (isBrowser ? window.location.origin : '');
const isRailwayHost = (host) => typeof host === 'string' && host.includes('railway.app');

const hasProtocol = (value) => /^[a-zA-Z][a-zA-Z\d+\-.]*:\/\//.test(value);
const trimTrailingSlash = (value) => value.replace(/\/+$/, '');

const normalizeUrl = (url) => {
  if (!url) return '';

  let normalized = url;

  if (normalized.startsWith('%') && normalized.endsWith('%')) {
    // Placeholder not replaced during build
    return '';
  }

  if (normalized.startsWith('/')) {
    // Treat as relative path to current origin
    const origin = currentOrigin();
    if (!origin) {
      return '';
    }
    normalized = `${origin}${normalized}`;
  }

  try {
    const parsed = new URL(normalized);

    parsed.pathname = parsed.pathname.replace(/\/+$/, '');

    return trimTrailingSlash(parsed.toString());
  } catch (error) {
    console.error('Invalid backend URL detected, falling back to same origin:', normalized, error);
    return '';
  }
};

let processedBackend = normalizeUrl(rawEnvUrl);

if (!processedBackend) {
  // Fallback to same origin when env var is missing or invalid
  processedBackend = trimTrailingSlash(currentOrigin() || '');
}

if (!processedBackend) {
  // Last resort: assume localhost for local development only
  processedBackend = 'http://localhost:8000';
}

export const API_BASE_URL = processedBackend.endsWith('/api')
  ? processedBackend
  : `${processedBackend}/api`;

if (process.env.NODE_ENV !== 'production') {
  console.info('API_BASE_URL resolved to:', API_BASE_URL);
}

export default API_BASE_URL;
