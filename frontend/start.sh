#!/bin/sh
set -e

# Use PORT from Railway environment or default to 3000
PORT=${PORT:-3000}

echo "Starting serve on port $PORT"

# Start serve
exec serve -s build -l tcp://0.0.0.0:$PORT