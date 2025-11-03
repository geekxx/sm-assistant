#!/bin/bash
# Start SM Assistant locally
# Usage: ./start_local.sh

set -e

echo "🚀 Starting SM Assistant..."

# Kill any existing processes
echo "Stopping existing processes..."
pkill -f "python.*main_production_sk.py" 2>/dev/null || true
sleep 2

# Start backend
echo "Starting backend..."
cd "$(dirname "$0")"
source .venv/bin/activate
python src/backend/main_production_sk.py > /tmp/sm-backend.log 2>&1 &
BACKEND_PID=$!
echo "✅ Backend started (PID: $BACKEND_PID)"

# Wait for backend to be ready
echo "Waiting for backend to start..."
sleep 3

# Check if backend is running
if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo "✅ Backend is healthy"
else
    echo "⚠️  Backend might not be ready yet, check /tmp/sm-backend.log"
fi

# Check if frontend is running
if lsof -i :3001 > /dev/null 2>&1; then
    echo "✅ Frontend already running on http://localhost:3001"
else
    echo "⚠️  Frontend not running. Start it with:"
    echo "   cd src/frontend && npm run dev"
fi

echo ""
echo "🎉 SM Assistant is starting!"
echo "   Frontend: http://localhost:3001"
echo "   Backend:  http://localhost:8000"
echo "   API Docs: http://localhost:8000/docs"
echo ""
echo "To stop backend: pkill -f 'python.*main_production_sk.py'"
echo "To view logs:    tail -f /tmp/sm-backend.log"
