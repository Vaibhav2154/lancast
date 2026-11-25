#!/usr/bin/env bash
# Post-deploy smoke verification for LANCAST gateway, API, frontend, and security boundaries.
#
# Usage:
#   ./infrastructure/scripts/smoke-test.sh [--url http://localhost] [--cacert path/to/ca.crt]

set -euo pipefail

BASE_URL="http://localhost"
CACERT_ARGS=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    --url)
      BASE_URL="${2:?Missing URL after --url}"
      shift 2
      ;;
    --cacert)
      CACERT_ARGS=(--cacert "${2:?Missing path after --cacert}")
      shift 2
      ;;
    *)
      echo "Unknown argument: $1" >&2
      exit 2
      ;;
  esac
done

BASE_URL="${BASE_URL%/}"

check_code() {
  local method="$1"
  local path="$2"
  local expected="$3"
  local actual
  actual="$(curl "${CACERT_ARGS[@]}" -sS -o /dev/null -w "%{http_code}" -X "$method" "$BASE_URL$path")"
  if [[ "$actual" != "$expected" ]]; then
    echo "FAIL $method $path: expected HTTP $expected, got $actual" >&2
    exit 1
  fi
  echo "OK   $method $path -> $actual"
}

check_code GET /api/health 200
check_code GET /api/ready 200
check_code GET / 200
check_code POST /api/internal/execution/jobs/00000000-0000-0000-0000-000000000000/result 403

HEADERS="$(curl "${CACERT_ARGS[@]}" -sSI "$BASE_URL/api/health" | tr -d '\r')"
for expected_hdr in "x-content-type-options: nosniff" "x-frame-options: DENY"; do
  if ! grep -qi "^$expected_hdr$" <<< "$HEADERS"; then
    echo "FAIL missing security header: $expected_hdr" >&2
    exit 1
  fi
  echo "OK   header present: $expected_hdr"
done

echo "All smoke checks passed for $BASE_URL"
