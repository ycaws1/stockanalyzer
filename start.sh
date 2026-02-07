#!/bin/bash

# Start Backend
echo "Starting Backend..."
cd backend
source venv/bin/activate
uvicorn app.main:app --reload --port 8001 &
BACKEND_PID=$!

# Start Frontend
echo "Starting Frontend..."
cd ../frontend
npm run dev &
FRONTEND_PID=$!

# Cleanup on exit
trap "kill $BACKEND_PID $FRONTEND_PID" EXIT

wait
