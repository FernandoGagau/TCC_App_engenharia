#!/bin/bash
set -e

# Use PORT from environment or default to 8000
PORT=${PORT:-8000}

# Start uvicorn with dynamic port
exec uvicorn src.main:app \
    --host 0.0.0.0 \
    --port $PORT \
    --workers 4 \
    --log-level info \
    --access-log