#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="/Users/ayushmishra/Projects/cat-digital-2/catrent"
CRON_CMD="cd \"$PROJECT_DIR\" && set -a && source .env && set +a && ./.venv/bin/python manage.py send_rental_remainders >> /tmp/catrent-reminders.out.log 2>> /tmp/catrent-reminders.err.log"
CRON_LINE="*/2 * * * * /bin/zsh -lc '$CRON_CMD'"

TMP_FILE="$(mktemp)"
crontab -l 2>/dev/null | grep -v 'catrent.*send_rental_remainders' > "$TMP_FILE" || true
echo "$CRON_LINE" >> "$TMP_FILE"
crontab "$TMP_FILE"
rm -f "$TMP_FILE"

echo "Installed cron schedule for CatRent reminders every 2 minutes"
crontab -l | grep 'catrent.*send_rental_remainders' || true
