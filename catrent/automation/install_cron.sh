#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="/c/Users/Piyush/Desktop/Project/cat-digital-2/catrent"
ROOT_DIR="$(cd "$PROJECT_DIR/.." && pwd)"
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

CRON_CMD="cd \"$PROJECT_DIR\" && set -a && source .env && set +a && \"$PYTHON_BIN\" manage.py send_rental_remainders >> /tmp/catrent-reminders.out.log 2>> /tmp/catrent-reminders.err.log"
CRON_LINE="*/2 * * * * /bin/zsh -lc '$CRON_CMD'"

TMP_FILE="$(mktemp)"
crontab -l 2>/dev/null | grep -v 'catrent.*send_rental_remainders' > "$TMP_FILE" || true
echo "$CRON_LINE" >> "$TMP_FILE"
crontab "$TMP_FILE"
rm -f "$TMP_FILE"

echo "Installed cron schedule for CatRent reminders every 2 minutes"
crontab -l | grep 'catrent.*send_rental_remainders' || true
