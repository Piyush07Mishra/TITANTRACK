#!/usr/bin/env bash
set -euo pipefail

PORT="${1:-${DEV_PORT:-8010}}"
BASE_URL="${DEV_BASE_URL:-http://127.0.0.1:$PORT}"

PASS_COUNT=0
FAIL_COUNT=0

check_endpoint() {
  local path="$1"
  local expected_csv="$2"
  local code
  code="$(curl -s -o /dev/null -w "%{http_code}" "$BASE_URL$path")"

  IFS=',' read -r -a expected_codes <<< "$expected_csv"
  local ok="false"
  local expected
  for expected in "${expected_codes[@]}"; do
    if [[ "$code" == "$expected" ]]; then
      ok="true"
      break
    fi
  done

  if [[ "$ok" == "true" ]]; then
    printf "✅ %s -> %s\n" "$path" "$code"
    PASS_COUNT=$((PASS_COUNT + 1))
  else
    printf "❌ %s -> %s (expected: %s)\n" "$path" "$code" "$expected_csv"
    FAIL_COUNT=$((FAIL_COUNT + 1))
  fi
}

echo "Health check base URL: $BASE_URL"

check_endpoint "/" "200"
check_endpoint "/admin/" "200,302"
check_endpoint "/admin/login/" "200"
check_endpoint "/static/admin/css/base.css" "200"
check_endpoint "/anomaly-data/" "200"
check_endpoint "/forecast_image/Bulldozer/" "200"

echo "---"
echo "Passed: $PASS_COUNT"
echo "Failed: $FAIL_COUNT"

if [[ "$FAIL_COUNT" -gt 0 ]]; then
  exit 1
fi

echo "All checks passed."
