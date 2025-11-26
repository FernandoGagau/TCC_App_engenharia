# Deployment Guide - Docker & Railway Alignment

## Overview

This document describes the Docker and Railway deployment optimization implemented as part of task-19-docker-railway-alignment. The optimization includes multi-stage builds, unified configurations, and production-ready setups.

## Architecture Changes

### Backend Deployment
- **Multi-stage Docker build** with dependencies caching
- **Non-root user** for security
- **Optimized Python wheels** for faster builds
- **Production-ready uvicorn** with multiple workers

### Frontend Deployment
- **Multi-stage Docker build** with Node.js builder + Nginx runtime
- **Nginx optimization** with gzip, security headers, and caching
- **SPA routing support** for React Router
- **Production build optimizations**

## Docker Configurations

### Backend Dockerfile
```dockerfile
# Multi-stage build for Python backend
# Stage 1: Dependencies builder
FROM python:3.12-slim AS dependencies
# ... builds wheels for faster installation

# Stage 2: Runtime image
FROM python:3.12-slim AS runtime
# ... optimized runtime with non-root user
```

**Key Features:**
- Multi-stage build reduces final image size
- Wheels caching for faster subsequent builds
- Non-root user (appuser) for security
- Health checks and proper environment variables
- 4 workers for production scalability

### Frontend Dockerfile
```dockerfile
# Multi-stage build for React frontend
# Stage 1: Dependencies and build
FROM node:18-alpine AS builder
# ... builds React application

# Stage 2: Production server with Nginx
FROM nginx:alpine AS runtime
# ... serves static files with optimized nginx
```

**Key Features:**
- Multi-stage build for minimal production image
- Custom nginx configuration with security headers
- Gzip compression and caching strategies
- Health checks and non-root user
- API proxy configuration for backend communication

## Railway Configurations

### Backend railway.toml
```toml
[build]
builder = "dockerfile"
dockerfilePath = "Dockerfile"

[deploy]
startCommand = "python -m uvicorn src.main:app --host 0.0.0.0 --port $PORT --workers 4"
restartPolicyType = "ON_FAILURE"
restartPolicyMaxRetries = 3

[dependencies]
services = ["mongodb", "minio", "redis"]

[resources]
memory = "2Gi"
cpu = "1000m"
```

**Key Features:**
- Dockerfile-based builds for consistency
- Service dependencies for MongoDB, MinIO, Redis
- Health checks and restart policies
- Resource allocation optimization
- Persistent volumes for storage and logs

### Frontend railway.toml
```toml
[build]
builder = "dockerfile"
dockerfilePath = "Dockerfile"

[deploy]
startCommand = "nginx -g 'daemon off;'"

[dependencies]
services = ["backend"]

[resources]
memory = "512Mi"
cpu = "250m"
```

**Key Features:**
- Dependency on backend service
- Lighter resource allocation
- CDN and static asset optimization
- Custom domain support

## Docker Ignore Files

### Backend .dockerignore
Excludes:
- Virtual environments (.venv, venv, env)
- Python cache (__pycache__, *.pyc)
- Development tools (.vscode, .idea)
- Logs and temporary files
- Git and backup files

### Frontend .dockerignore
Excludes:
- Node modules and caches
- Build artifacts
- Environment files
- Development configurations
- Documentation and backup files

## Nginx Configuration

Custom nginx.conf for frontend includes:
- **Security headers**: CSP, X-Frame-Options, X-XSS-Protection
- **Gzip compression** for assets
- **Caching strategies** for static assets
- **API proxy** to backend service
- **SPA routing** support for React Router
- **Health check** endpoint

## Environment Variables

### Backend
- `PYTHONPATH=/app`
- `PYTHONUNBUFFERED=1`
- `PYTHONDONTWRITEBYTECODE=1`

### Frontend
- `REACT_APP_BACKEND_URL=/api`
- `NODE_ENV=production`
- `GENERATE_SOURCEMAP=false`

## Deployment Instructions

### Local Development
```bash
# Backend
cd backend
docker build -t backend:latest .
docker run -p 8000:8000 backend:latest

# Frontend
cd frontend
docker build -t frontend:latest .
docker run -p 3000:3000 frontend:latest
```

### Railway Deployment
1. Push code to repository
2. Railway will automatically detect railway.toml
3. Service dependencies will be provisioned automatically
4. Health checks will monitor application status

## Security Improvements

1. **Non-root users** in both containers
2. **Security headers** in nginx configuration
3. **Minimal base images** (alpine/slim)
4. **No secrets in images** (environment-based configuration)
5. **Read-only containers** where possible

## Performance Optimizations

1. **Multi-stage builds** reduce image sizes
2. **Wheels caching** speeds up Python builds
3. **Gzip compression** reduces bandwidth
4. **Static asset caching** improves load times
5. **Multiple workers** increase throughput

## Monitoring and Health Checks

- **Backend**: Health check on `/health` endpoint
- **Frontend**: Health check on `/health` endpoint
- **Interval**: 30 seconds
- **Timeout**: 10 seconds
- **Retries**: 3 attempts

## Troubleshooting

### Common Issues

1. **Build failures**: Check .dockerignore files exclude unnecessary files
2. **Permission errors**: Verify non-root user configurations
3. **Network issues**: Ensure service dependencies are properly configured
4. **Resource limits**: Adjust memory/CPU allocations in railway.toml

### Logs Access
```bash
# Railway CLI
railway logs --service backend
railway logs --service frontend

# Docker local
docker logs <container_id>
```

## Version Compatibility

- **Python**: 3.12+
- **Node.js**: 18+
- **Docker**: 20+
- **Railway**: Latest platform features

## Migration Notes

- Previous nixpacks builds replaced with Dockerfile-based builds
- Service dependencies now explicitly defined
- Resource allocations optimized for production workloads
- Security hardening applied across all containers

---
*Generated as part of task-19-docker-railway-alignment*
