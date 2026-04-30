#!/usr/bin/env bash
set -euo pipefail

TARGET_PLIST="$HOME/Library/LaunchAgents/com.catrent.reminders.plist"

launchctl bootout "gui/$UID/com.catrent.reminders" >/dev/null 2>&1 || true
rm -f "$TARGET_PLIST"

echo "Removed: com.catrent.reminders"
