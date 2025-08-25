#!/bin/bash
# Start both frontend and backend
cd "$(dirname "$0")/.."

echo "Starting Weev development servers..."
echo "Backend: http://localhost:8004"
echo "Frontend: http://localhost:3000"

# Start backend in background
cd config && python -m uvicorn ../backend/main:app --reload --port 8004 &
BACKEND_PID=$!

# Start frontend dev server from config (SvelteKit project lives here)
npm run dev

# Cleanup on exit
trap "kill $BACKEND_PID" EXIT
