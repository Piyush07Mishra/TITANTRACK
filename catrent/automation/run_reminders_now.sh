#!/usr/bin/env bash
set -euo pipefail

launchctl kickstart -k "gui/$UID/com.catrent.reminders"
echo "Triggered com.catrent.reminders immediately"
