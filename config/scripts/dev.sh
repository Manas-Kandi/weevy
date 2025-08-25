#!/bin/bash
# Start both frontend and backend
PROJECT_ROOT="$(dirname "$0")/../.."
cd "$PROJECT_ROOT"

# Activate Python virtual environment if available
if [ -f "config/venv/bin/activate" ]; then
  echo "Activating Python venv at config/venv"
  # shellcheck disable=SC1091
  source "config/venv/bin/activate"
elif [ -f "config/backend_venv/bin/activate" ]; then
  echo "Activating Python venv at config/backend_venv"
  # shellcheck disable=SC1091
  source "config/backend_venv/bin/activate"
else
  echo "No Python venv found in config/. Proceeding without activation."
fi

echo "Starting Weev development servers..."
echo "Backend: http://localhost:8004"
echo "Frontend: http://localhost:3000"

# Start backend in background
( cd backend && python -m uvicorn main:app --host 0.0.0.0 --port 8004 --reload ) &
BACKEND_PID=$!

# Start frontend from frontend directory
cd frontend
npm run dev &
FRONTEND_PID=$!

# Cleanup on exit
trap "kill $BACKEND_PID; kill $FRONTEND_PID" EXIT
