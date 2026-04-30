#!/usr/bin/env bash
set -euo pipefail

PORT="${1:-${DEV_PORT:-8010}}"

PIDS="$(lsof -ti tcp:"$PORT" || true)"
if [[ -z "$PIDS" ]]; then
  echo "Server is NOT running on port $PORT"
  exit 0
fi

echo "Server is running on port $PORT"
echo "PID(s): $PIDS"
lsof -i tcp:"$PORT" | awk 'NR==1 || /LISTEN/'
