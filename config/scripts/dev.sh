#!/bin/bash
# Start both frontend and backend
PROJECT_ROOT="$(dirname "$0")/../.."
cd "$PROJECT_ROOT"

# Load environment variables for backend and Alembic (DATABASE_URL, etc.)
if [ -f ".env" ]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
elif [ -f ".env.local" ]; then
  set -a
  # shellcheck disable=SC1091
  source .env.local
  set +a
fi

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

# Run database migrations before starting backend
if command -v alembic >/dev/null 2>&1; then
  echo "Running database migrations (alembic upgrade head)..."
  alembic -c Backend/database/migrations/alembic.ini upgrade head || {
    echo "Alembic migration failed. Check DATABASE_URL and migration files." >&2
  }
else
  echo "Alembic not found in PATH. Skipping migrations."
fi

# Start backend in background
( cd Backend && python -m uvicorn main:app --host 0.0.0.0 --port 8004 --reload ) &
BACKEND_PID=$!

# Start frontend from frontend directory
cd frontend
npm run dev &
FRONTEND_PID=$!

# Cleanup on exit
trap "kill $BACKEND_PID; kill $FRONTEND_PID" EXIT
