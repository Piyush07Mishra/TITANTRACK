#!/usr/bin/env bash
set -euo pipefail

TMP_FILE="$(mktemp)"
crontab -l 2>/dev/null | grep -v 'catrent.*send_rental_remainders' > "$TMP_FILE" || true
if [[ -s "$TMP_FILE" ]]; then
  crontab "$TMP_FILE"
else
  crontab -r || true
fi
rm -f "$TMP_FILE"

echo "Removed CatRent reminder cron schedule"
