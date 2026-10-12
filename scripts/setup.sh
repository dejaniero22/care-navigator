#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
export UV_CACHE_DIR=${UV_CACHE_DIR:-/workspace/.cache/uv}
if [ ! -d .venv ]; then uv venv .venv; fi
uv pip install --python .venv/bin/python -r backend/requirements.lock
npm ci --prefix frontend --cache /workspace/.cache/npm
if [ -z "${PGHOST:-}" ] || [ "${PGHOST:-}" = /workspace/care-navigator-runtime ]; then
  scripts/install-postgres.sh
  scripts/postgres.sh
fi
.venv/bin/python backend/manage.py migrate --noinput
.venv/bin/python backend/manage.py seed_demo
npm run build --prefix frontend
