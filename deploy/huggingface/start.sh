#!/usr/bin/env bash
# Starts FastAPI (internal) and the Next.js server (public) in one container.
# If either process exits, the container exits so the platform restarts it.
set -euo pipefail

API_PORT="${API_PORT:-8000}"

if [ -z "${SECRET_KEY:-}" ]; then
  # Sessions and the demo database are ephemeral on a free Space anyway; set a SECRET_KEY secret to keep logins across restarts.
  SECRET_KEY="$(python -c 'import secrets; print(secrets.token_urlsafe(48))')"
  export SECRET_KEY
  echo "WARNING: SECRET_KEY not set — generated a temporary one. Add it as a Space secret for stable sessions."
fi

cd /app/api
uvicorn app.main:app --host 127.0.0.1 --port "$API_PORT" --proxy-headers --forwarded-allow-ips '*' &
API_PID=$!

for _ in $(seq 1 90); do
  curl -fs "http://127.0.0.1:${API_PORT}/healthz" > /dev/null && break
  kill -0 "$API_PID" 2> /dev/null || { echo "API failed to start"; exit 1; }
  sleep 1
done

cd /app/web
HOSTNAME=0.0.0.0 node server.js &
WEB_PID=$!

echo "InsurePilot is up on port ${PORT:-7860}"
wait -n "$API_PID" "$WEB_PID"
exit $?
