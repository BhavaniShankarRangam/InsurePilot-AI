#!/usr/bin/env bash
# Starts the API and web app for local development (macOS / Linux / Git Bash).
# Usage: API_PORT=8000 WEB_PORT=3000 ./scripts/dev.sh
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
API_PORT="${API_PORT:-8000}"
WEB_PORT="${WEB_PORT:-3000}"

cd "$ROOT/apps/api"
if [ ! -d .venv ]; then
  python3 -m venv .venv
  .venv/bin/pip install -r requirements-dev.txt 2>/dev/null || .venv/Scripts/pip install -r requirements-dev.txt
fi
PY=.venv/bin/python; [ -x "$PY" ] || PY=.venv/Scripts/python
"$PY" -m uvicorn app.main:app --reload --port "$API_PORT" &
API_PID=$!
trap 'kill $API_PID 2>/dev/null' EXIT

cd "$ROOT/apps/web"
[ -d node_modules ] || npm install
API_URL="http://127.0.0.1:$API_PORT" npx next dev --webpack -p "$WEB_PORT"
