#!/usr/bin/env bash
# Start SocialLens backend on :8000 bound for phone/glasses LAN access.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ -f .venv/bin/activate ]]; then
  # shellcheck disable=SC1091
  source .venv/bin/activate
fi

if [[ -f .env ]]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi

PORT="${PORT:-8000}"
pids="$(lsof -t -iTCP:"$PORT" -sTCP:LISTEN 2>/dev/null || true)"
if [[ -n "${pids}" ]]; then
  echo "Port $PORT in use by: $(ps -p $pids -o args= 2>/dev/null || echo "$pids")"
  if ps -p $pids -o args= 2>/dev/null | grep -q 'uvicorn app.main'; then
    echo "Stopping existing SocialLens uvicorn…"
    # shellcheck disable=SC2086
    kill $pids
    sleep 0.4
  else
    echo "Refusing to stop an unrelated process. Set PORT to another value or stop it manually." >&2
    exit 1
  fi
fi

export XAI_MODEL="${XAI_MODEL:-grok-4.20-0309-non-reasoning}"
echo "Starting SocialLens on 0.0.0.0:$PORT (model=$XAI_MODEL)"
exec uvicorn app.main:app --host 0.0.0.0 --port "$PORT"
