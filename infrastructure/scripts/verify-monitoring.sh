#!/usr/bin/env bash
# End-to-end verification of LANCAST Phase 4 monitoring, privacy boundaries, and dashboards.
#
# Usage:
#   ./infrastructure/scripts/verify-monitoring.sh [--gateway-url http://localhost]

set -euo pipefail

GATEWAY_URL="http://localhost"
PROM_URL="http://127.0.0.1:${PROMETHEUS_PORT:-9090}"
GRAFANA_URL="http://127.0.0.1:${GRAFANA_PORT:-3000}"
GRAFANA_USER="${GRAFANA_ADMIN_USER:-admin}"
GRAFANA_PASS="${GRAFANA_ADMIN_PASSWORD:-lancast-grafana-dev}"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --gateway-url)
      GATEWAY_URL="${2:?Missing URL after --gateway-url}"
      shift 2
      ;;
    *)
      echo "Unknown argument: $1" >&2
      exit 2
      ;;
  esac
done

GATEWAY_URL="${GATEWAY_URL%/}"

# 1. Confirm /metrics is blocked at Traefik (T11, T20).
METRICS_CODE="$(curl -sS -o /dev/null -w "%{http_code}" "$GATEWAY_URL/metrics")"
if [[ "$METRICS_CODE" != "403" ]]; then
  echo "FAIL $GATEWAY_URL/metrics expected 403, got $METRICS_CODE" >&2
  exit 1
fi
echo "OK   Gateway blocks /metrics -> 403"

# 2. Confirm internal API /metrics exposes expected lancast_* families with zero PII/secrets.
API_METRICS="$(docker compose exec -T api python3 -c "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:8000/metrics', timeout=5).read().decode())")"
for family in \
  "lancast_http_requests_total" \
  "lancast_http_request_duration_seconds_bucket" \
  "lancast_http_in_progress_requests" \
  "lancast_execution_queue_depth" \
  "lancast_execution_dead_letter_depth"; do
  if ! grep -q "$family" <<< "$API_METRICS"; then
    echo "FAIL missing metric family: $family" >&2
    exit 1
  fi
done
echo "OK   Internal API /metrics exposes core lancast_* families"

for forbidden in "@campus.edu" "Bearer " "password_hash" "eyJhbGciOi"; do
  if grep -q "$forbidden" <<< "$API_METRICS"; then
    echo "FAIL sensitive token/PII marker found in /metrics: $forbidden" >&2
    exit 1
  fi
done
echo "OK   Privacy check passed (zero emails/JWTs/passwords in /metrics)"

# 3. Confirm Prometheus targets are UP and rules loaded.
curl -sf "$PROM_URL/api/v1/targets" | python3 -c "
import json, sys
targets = json.load(sys.stdin)['data']['activeTargets']
if not targets:
    raise SystemExit('FAIL no Prometheus active targets')
down = [t['labels'].get('job') for t in targets if t['health'] != 'up']
if down:
    raise SystemExit(f'FAIL Prometheus targets down: {down}')
print(f'OK   Prometheus targets UP ({len(targets)}/{len(targets)})')
"

curl -sf "$PROM_URL/api/v1/rules" | python3 -c "
import json, sys
groups = json.load(sys.stdin)['data']['groups']
rule_count = sum(len(g.get('rules', [])) for g in groups)
if rule_count < 8:
    raise SystemExit(f'FAIL expected >=8 alert rules, got {rule_count}')
print(f'OK   Prometheus alert rules loaded ({rule_count} rules across {len(groups)} groups)')
"

# 4. Confirm Grafana provisioned dashboards exist.
curl -sf -u "$GRAFANA_USER:$GRAFANA_PASS" "$GRAFANA_URL/api/search" | python3 -c "
import json, sys
uids = {d.get('uid') for d in json.load(sys.stdin)}
required = {'lancast-overview', 'lancast-infrastructure'}
missing = required - uids
if missing:
    raise SystemExit(f'FAIL missing Grafana dashboards: {sorted(missing)}')
print('OK   Grafana provisioned dashboards present:', ', '.join(sorted(required)))
"

echo "All Phase 4 monitoring verification checks passed."
