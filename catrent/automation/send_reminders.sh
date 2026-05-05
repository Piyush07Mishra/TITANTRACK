Kyhala Bharwar EK. #!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="/c/Users/Piyush/Desktop/Project/cat-digital-2/catrent"
ROOT_DIR="$(cd "$PROJECT_DIR/.." && pwd)"
cd "$PROJECT_DIR"

if [[ -f "$PROJECT_DIR/.env" ]]; then
  set -a
  source "$PROJECT_DIR/.env"
  set +a
fi

PYTHON_BIN=""
for candidate in \
  "$PROJECT_DIR/.venv-1/Scripts/python.exe" \
  "$PROJECT_DIR/.venv/Scripts/python.exe" \
  "$PROJECT_DIR/.venv-1/bin/python" \
  "$PROJECT_DIR/.venv/bin/python" \
  "$ROOT_DIR/.venv/Scripts/python.exe" \
  "$ROOT_DIR/.venv/bin/python"
do
  if [[ -f "$candidate" ]]; then
    PYTHON_BIN="$candidate"
    break
  fi
done

if [[ -z "$PYTHON_BIN" ]]; then
  echo "Python venv not found. Checked .venv-1 and .venv." >&2
  exit 1
fi

"$PYTHON_BIN" manage.py send_rental_remainders
