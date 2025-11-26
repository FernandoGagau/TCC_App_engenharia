# Multi-stage build for Python backend
# Stage 1: Dependencies builder
FROM python:3.12-slim AS dependencies

# Set working directory
WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    build-essential \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Update pip and setuptools
RUN pip install --no-cache-dir --upgrade pip setuptools wheel

# Copy requirements first for better caching
COPY requirements.txt .

# Create wheels for all dependencies
RUN pip wheel --no-cache-dir --no-deps --wheel-dir /wheels -r requirements.txt

# Stage 2: Runtime image
FROM python:3.12-slim AS runtime

# Set working directory
WORKDIR /app

# Create non-root user for security
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Install runtime system dependencies
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-por \
    libmagic1 \
    poppler-utils \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Copy wheels from builder stage
COPY --from=dependencies /wheels /wheels

# Copy requirements for installation
COPY requirements.txt .

# Install dependencies from wheels
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir --find-links /wheels -r requirements.txt && \
    rm -rf /wheels

# Copy source code
COPY --chown=appuser:appuser ./src ./src

# Copy config files
COPY --chown=appuser:appuser ./config ./config

# Copy entrypoint script
COPY --chown=appuser:appuser ./entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# Create necessary directories with proper permissions
RUN mkdir -p /app/logs /app/storage /home/appuser/.config/matplotlib /home/appuser/.cache/fontconfig && \
    chown -R appuser:appuser /app /home/appuser

# Switch to non-root user
USER appuser

# Expose port (Railway will inject PORT env var)
EXPOSE 8000

# Set environment variables for production
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PORT=8000
ENV MPLCONFIGDIR=/home/appuser/.config/matplotlib
ENV FONTCONFIG_PATH=/etc/fonts

# Health check (uses PORT env var)
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:${PORT:-8000}/health || exit 1

# Run the application with uvicorn via entrypoint
ENTRYPOINT ["/app/entrypoint.sh"]
