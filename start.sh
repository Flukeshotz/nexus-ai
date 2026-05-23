#!/bin/bash
echo "🚀 Starting Nexus AI Platform..."

cd "$(dirname "$0")"

# Start Frontend
echo "Starting Frontend Server on http://localhost:3000..."
cd frontend
python3 -m http.server 3000 > /dev/null 2>&1 &
FRONTEND_PID=$!
cd ..

# Start Backend
echo "Starting Backend API Server on http://localhost:8000..."
cd backend
# Make sure database exists
python3 init_db.py
uvicorn app.main:app --host 0.0.0.0 --port 8000

# Cleanup on exit
trap "kill $FRONTEND_PID" EXIT
