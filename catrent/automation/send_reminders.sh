#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="/Users/ayushmishra/Projects/cat-digital-2/catrent"
cd "$PROJECT_DIR"

if [[ -f "$PROJECT_DIR/.env" ]]; then
  set -a
  source "$PROJECT_DIR/.env"
  set +a
fi

"$PROJECT_DIR/.venv/bin/python" manage.py send_rental_remainders
