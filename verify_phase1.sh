#!/usr/bin/env bash
set -e
PASS=0
FAIL=0

check() {
  local name="$1"
  local cmd="$2"
  if eval "$cmd" > /dev/null 2>&1; then
    echo "  PASS: $name"
    PASS=$((PASS+1))
  else
    echo "  FAIL: $name"
    FAIL=$((FAIL+1))
  fi
}

echo "=== Phase 1 Smoke Tests ==="

# Infrastructure
check "Kong admin API (8001)" "curl -sf http://localhost:8001/"
check "RabbitMQ management UI (15672)" "curl -sf http://localhost:15672/"
check "Docker network rental-net" "docker network inspect rental-net"

# Kong routes (non-502 means upstream is reachable)
for route in book-car cancel-booking report-issue resolve-issue vehicles bookings drivers reports pricing; do
  status=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/api/$route)
  if [ "$status" != "502" ] && [ "$status" != "000" ]; then
    check "Kong route /api/$route ($status)" "true"
  else
    check "Kong route /api/$route ($status)" "false"
  fi
done

# CORS headers present
check "CORS headers on /api/vehicles" "curl -sv -H 'Origin: http://localhost:8080' http://localhost:8000/api/vehicles 2>&1 | grep -q 'Access-Control-Allow-Origin'"

echo ""
echo "Results: $PASS passed, $FAIL failed"
if [ "$FAIL" -gt 0 ]; then
  exit 1
fi
echo "All checks passed."
