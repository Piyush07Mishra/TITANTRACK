#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="/Users/ayushmishra/Projects/cat-digital-2/catrent"
TEMPLATE="$PROJECT_DIR/automation/com.catrent.reminders.plist.template"
TARGET_DIR="$HOME/Library/LaunchAgents"
TARGET_PLIST="$TARGET_DIR/com.catrent.reminders.plist"

mkdir -p "$TARGET_DIR"

sed "s|__PROJECT_DIR__|$PROJECT_DIR|g" "$TEMPLATE" > "$TARGET_PLIST"

launchctl bootout "gui/$UID/com.catrent.reminders" >/dev/null 2>&1 || true
launchctl bootstrap "gui/$UID" "$TARGET_PLIST"
launchctl enable "gui/$UID/com.catrent.reminders"

echo "Installed and enabled: com.catrent.reminders"
echo "Runs daily at 09:00 local time"
echo "Plist: $TARGET_PLIST"
echo "Logs: /tmp/catrent-reminders.out.log, /tmp/catrent-reminders.err.log"
