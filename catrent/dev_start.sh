#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

PORT="${1:-${DEV_PORT:-8010}}"
HOST="${DEV_HOST:-127.0.0.1}"

print_link() {
  local label="$1"
  local url="$2"

  # OSC 8 makes links clickable in terminals that support hyperlinks.
  if [[ -t 1 ]]; then
    printf '%s: \033]8;;%s\a%s\033]8;;\a\n' "$label" "$url" "$url"
  else
    echo "$label: $url"
  fi
}

PYTHON_BIN=""
for candidate in \
  "$ROOT_DIR/.venv/bin/python" \
  "$ROOT_DIR/../.venv/bin/python" \
  "$ROOT_DIR/../.venv/Scripts/python.exe"
do
  if [[ -x "$candidate" || -f "$candidate" ]]; then
    PYTHON_BIN="$candidate"
    break
  fi
done

if [[ -z "$PYTHON_BIN" ]]; then
  echo "Missing virtual environment python. Checked:"
  echo "  - $ROOT_DIR/.venv/bin/python"
  echo "  - $ROOT_DIR/../.venv/bin/python"
  echo "  - $ROOT_DIR/../.venv/Scripts/python.exe"
  echo "Create it first, then install dependencies."
  exit 1
fi

if [[ -f "$ROOT_DIR/.env" ]]; then
  set -a
  source "$ROOT_DIR/.env"
  set +a
fi

if "$PYTHON_BIN" - "$HOST" "$PORT" <<'PY'
import socket
import sys

host = sys.argv[1]
port = int(sys.argv[2])

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.settimeout(0.4)
try:
    rc = sock.connect_ex((host, port))
finally:
    sock.close()

sys.exit(0 if rc == 0 else 1)
PY
then
  echo "Server already running on http://$HOST:$PORT"
  print_link "Dashboard" "http://$HOST:$PORT/"
  print_link "Admin" "http://$HOST:$PORT/admin/"
  exit 0
fi

if command -v lsof >/dev/null 2>&1; then
  if lsof -ti tcp:"$PORT" >/dev/null 2>&1; then
    echo "Port $PORT is in use. Stopping existing process..."
    lsof -ti tcp:"$PORT" | xargs kill -15 || true
    sleep 1
  fi
fi

echo "Running migrations..."
"$PYTHON_BIN" manage.py migrate

echo "Starting Django server on http://$HOST:$PORT"
print_link "Dashboard" "http://$HOST:$PORT/"
print_link "Admin" "http://$HOST:$PORT/admin/"
"$PYTHON_BIN" manage.py runserver "$HOST:$PORT"
