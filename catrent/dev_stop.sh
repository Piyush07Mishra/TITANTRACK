#!/usr/bin/env bash
set -euo pipefail

PORT="${1:-${DEV_PORT:-8010}}"

PIDS="$(lsof -ti tcp:"$PORT" || true)"
if [[ -z "$PIDS" ]]; then
  echo "No process found on port $PORT"
  exit 0
fi

echo "Stopping process(es) on port $PORT: $PIDS"
kill -15 $PIDS || true
