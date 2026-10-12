#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
TASK_LOG_DIR=${TASK_LOG_DIR:-/workspace/care-navigator-runtime}
mkdir -p "$TASK_LOG_DIR"
chmod 700 "$TASK_LOG_DIR"
if [ -z "${PGHOST:-}" ] || [ "${PGHOST:-}" = /workspace/care-navigator-runtime ]; then scripts/postgres.sh; fi
# Refuse duplicate listeners; never terminate an unrelated existing service.
.venv/bin/python - <<'PY'
import socket
for port in (8000,5173):
 with socket.socket() as s:
  if s.connect_ex(('127.0.0.1',port))==0:
   raise SystemExit(f'Port {port} is already in use. Inspect the running service before starting another instance.')
PY
nohup "$PWD/.venv/bin/python" "$PWD/backend/manage.py" runserver 127.0.0.1:8000 --noreload > "$TASK_LOG_DIR/backend.log" 2>&1 &
TASK_BACKEND_PID=$!
nohup node "$PWD/frontend/node_modules/vite/bin/vite.js" "$PWD/frontend" --host 127.0.0.1 > "$TASK_LOG_DIR/frontend.log" 2>&1 &
TASK_FRONTEND_PID=$!
printf '%s\n' "$TASK_BACKEND_PID" > "$TASK_LOG_DIR/backend.pid"
printf '%s\n' "$TASK_FRONTEND_PID" > "$TASK_LOG_DIR/frontend.pid"
for attempt in $(seq 1 30); do
 if curl --fail --silent http://127.0.0.1:5173/api/session/ | .venv/bin/python -c 'import json,sys; assert "authenticated" in json.load(sys.stdin)' 2>/dev/null; then
  echo "Development services started; session endpoint responds through the frontend proxy. Logs: $TASK_LOG_DIR"
  exit 0
 fi
 sleep 1
done
echo "Startup failed. Inspect $TASK_LOG_DIR/backend.log and frontend.log." >&2
exit 1
