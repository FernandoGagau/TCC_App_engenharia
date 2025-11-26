# Multi-stage build for React frontend
# Stage 1: Dependencies and build
FROM node:18-alpine AS builder

# Set working directory
WORKDIR /app

# Install system dependencies for node-gyp (if needed)
RUN apk add --no-cache \
    python3 \
    make \
    g++ \
    && rm -rf /var/cache/apk/*

# Copy package files first for better caching
COPY package*.json ./

# Install ALL dependencies (including devDependencies for build)
RUN npm ci --no-audit --no-fund && \
    npm cache clean --force

# Copy source code
COPY . .

# Set environment for production build
# REACT_APP_BACKEND_URL will be injected by Railway at build time
# Default to /api for local builds
ARG REACT_APP_BACKEND_URL=/api
ENV REACT_APP_BACKEND_URL=${REACT_APP_BACKEND_URL}
ENV NODE_ENV=production
ENV GENERATE_SOURCEMAP=false

# Build the application
RUN npm run build

# Stage 2: Production server with serve
FROM node:18-alpine AS runtime

# Install serve globally for serving static files
RUN npm install -g serve

# Create non-root user
RUN addgroup -g 1001 -S appuser && \
    adduser -S appuser -u 1001 -G appuser

# Set working directory
WORKDIR /app

# Copy start script
COPY start.sh /app/start.sh
RUN chmod +x /app/start.sh

# Copy built files from builder stage
COPY --from=builder --chown=appuser:appuser /app/build ./build

# Switch to non-root user
USER appuser

# Expose port (Railway will inject $PORT)
EXPOSE 3000

# Start via entrypoint script
CMD ["/app/start.sh"]
