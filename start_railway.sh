#!/bin/bash

# Railway startup script
echo "🚂 Starting SM Assistant on Railway..."

# Use Railway's PORT environment variable
export BACKEND_PORT=${PORT:-8005}
export FRONTEND_PORT=$((BACKEND_PORT + 1))

echo "Backend starting on port: $BACKEND_PORT"
echo "Frontend starting on port: $FRONTEND_PORT"

# Start backend in background
cd /app
python src/backend/main_production_sk.py --port $BACKEND_PORT &

# Start frontend (Railway will serve the built static files)
cd src/frontend
# For Railway, we'll just serve the backend since Railway can serve static files
wait