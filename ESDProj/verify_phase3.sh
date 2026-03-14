#!/usr/bin/env bash
# verify_phase3.sh — Phase 3 atomic services smoke tests
# Prerequisites:
#   1. docker-compose up (all containers running)
#   2. python seed_data.py (one-time Firestore seed — requires firebase-service-account.json at root)
# Tests call services directly on their mapped ports (bypassing Kong JWT).
# Ports: vehicle_service=5001, booking_service=5002, driver_service=5003,
#         report_service=5004, pricing_service=5005
# Estimated runtime: ~30 seconds
set -e
PASS=0; FAIL=0

check() {
  local name="$1"; local cmd="$2"
  if eval "$cmd" > /dev/null 2>&1; then
    echo "  PASS: $name"; PASS=$((PASS+1))
  else
    echo "  FAIL: $name"; FAIL=$((FAIL+1))
  fi
}

echo "=== Phase 3 Atomic Services Smoke Tests ==="

# ── Pre-test setup: create test booking and report for dependent checks ──

BOOKING_RESPONSE=$(curl -sf -X POST -H 'Content-Type: application/json' \
  -d '{"user_uid":"verify_test_uid","vehicle_id":"SBA1234A","vehicle_type":"sedan","pickup_datetime":"2027-06-01T10:00:00","hours":3,"total_price":37.50,"stripe_payment_intent_id":"pi_verify_001"}' \
  http://localhost:5002/api/bookings 2>/dev/null || echo '{}')
TEST_BOOKING_ID=$(echo "$BOOKING_RESPONSE" | python3 -c "import sys,json; print(json.load(sys.stdin).get('booking_id',''))" 2>/dev/null || echo "")

REPORT_RESPONSE=$(curl -sf -X POST -H 'Content-Type: application/json' \
  -d '{"booking_id":"bk_test","vehicle_id":"SBA1234A","user_uid":"test_driver_001","location":"Orchard Road","description":"Minor scratch on door"}' \
  http://localhost:5004/api/reports 2>/dev/null || echo '{}')
TEST_REPORT_ID=$(echo "$REPORT_RESPONSE" | python3 -c "import sys,json; print(json.load(sys.stdin).get('report_id',''))" 2>/dev/null || echo "")

# ── Vehicle Service (port 5001) ──

echo ""
echo "-- Vehicle Service --"

# VEH-01: GET /api/vehicles returns non-empty list
check "VEH-01: GET /api/vehicles returns non-empty list" \
  "curl -sf http://localhost:5001/api/vehicles | python3 -c \"import sys,json; d=json.load(sys.stdin); assert len(d['data']) > 0\""

# VEH-02: GET /api/vehicles/<plate> returns single vehicle
check "VEH-02: GET /api/vehicles/SBA1234A returns vehicle record" \
  "curl -sf http://localhost:5001/api/vehicles/SBA1234A | python3 -c \"import sys,json; d=json.load(sys.stdin); assert d['data']['plate_number'] == 'SBA1234A'\""

# VEH-03: PUT /api/vehicles/<plate>/status updates status — check 200
check "VEH-03: PUT /api/vehicles/SBA1234A/status returns ok" \
  "curl -sf -X PUT -H 'Content-Type: application/json' -d '{\"status\":\"available\"}' http://localhost:5001/api/vehicles/SBA1234A/status | python3 -c \"import sys,json; d=json.load(sys.stdin); assert d['status'] == 'ok'\""

# ── Booking Service (port 5002) ──

echo ""
echo "-- Booking Service --"

# BOOK-01: POST /api/bookings creates booking — capture booking_id
check "BOOK-01: POST /api/bookings creates booking with booking_id" \
  "curl -sf -X POST -H 'Content-Type: application/json' -d '{\"user_uid\":\"test_driver_001\",\"vehicle_id\":\"SBA1234A\",\"vehicle_type\":\"sedan\",\"pickup_datetime\":\"2027-01-15T10:00:00\",\"hours\":2,\"total_price\":25.00,\"stripe_payment_intent_id\":\"pi_test_001\"}' http://localhost:5002/api/bookings | python3 -c \"import sys,json; d=json.load(sys.stdin); assert 'booking_id' in d\""

# BOOK-02: GET /api/bookings/<id> — fetch the test booking created above
check "BOOK-02: GET /api/bookings/<id> returns booking data" \
  "[ -n \"\$TEST_BOOKING_ID\" ] && curl -sf http://localhost:5002/api/bookings/\$TEST_BOOKING_ID | python3 -c \"import sys,json; d=json.load(sys.stdin); assert 'data' in d\""

# BOOK-03: GET /api/bookings/user/<uid>/active — 200 or 404 both valid (no confirmed booking may exist)
check "BOOK-03: GET /api/bookings/user/test_driver_001/active returns 200 or 404" \
  "curl -s -o /dev/null -w \"%{http_code}\" http://localhost:5002/api/bookings/user/test_driver_001/active | grep -qE \"^(200|404)\$\""

# BOOK-04: GET /api/bookings/user/<uid> returns list
check "BOOK-04: GET /api/bookings/user/verify_test_uid returns list" \
  "curl -sf http://localhost:5002/api/bookings/user/verify_test_uid | python3 -c \"import sys,json; d=json.load(sys.stdin); assert isinstance(d['data'], list)\""

# BOOK-05: PUT /api/bookings/<id>/status updates booking status
check "BOOK-05: PUT /api/bookings/<id>/status returns ok" \
  "[ -n \"\$TEST_BOOKING_ID\" ] && curl -sf -X PUT -H 'Content-Type: application/json' -d '{\"status\":\"cancelled\"}' http://localhost:5002/api/bookings/\$TEST_BOOKING_ID/status | python3 -c \"import sys,json; d=json.load(sys.stdin); assert d['status'] == 'ok'\""

# ── Driver Service (port 5003) ──

echo ""
echo "-- Driver Service --"

# DRV-01: GET /api/drivers/<uid> returns driver record
check "DRV-01: GET /api/drivers/test_driver_001 returns driver record" \
  "curl -sf http://localhost:5003/api/drivers/test_driver_001 | python3 -c \"import sys,json; d=json.load(sys.stdin); assert d['data']['uid'] == 'test_driver_001'\""

# DRV-02: POST /api/drivers/validate with valid license returns valid:true
check "DRV-02: POST /api/drivers/validate returns valid:true for S1234567A" \
  "curl -sf -X POST -H 'Content-Type: application/json' -d '{\"license_number\":\"S1234567A\"}' http://localhost:5003/api/drivers/validate | python3 -c \"import sys,json; d=json.load(sys.stdin); assert d['valid'] == True\""

# ── Report Service (port 5004) ──

echo ""
echo "-- Report Service --"

# RPT-01: POST /api/reports creates report, returns report_id
check "RPT-01: POST /api/reports creates report with report_id" \
  "echo \"\$REPORT_RESPONSE\" | python3 -c \"import sys,json; d=json.load(sys.stdin); assert 'report_id' in d\""

# RPT-02: GET /api/reports/<id> returns report
check "RPT-02: GET /api/reports/<id> returns report data" \
  "[ -n \"\$TEST_REPORT_ID\" ] && curl -sf http://localhost:5004/api/reports/\$TEST_REPORT_ID | python3 -c \"import sys,json; d=json.load(sys.stdin); assert 'data' in d\""

# RPT-03: PUT /api/reports/<id>/evaluation updates severity
check "RPT-03: PUT /api/reports/<id>/evaluation updates severity and returns ok" \
  "[ -n \"\$TEST_REPORT_ID\" ] && curl -sf -X PUT -H 'Content-Type: application/json' -d '{\"severity\":\"low\",\"ai_evaluation\":\"Minor cosmetic damage\"}' http://localhost:5004/api/reports/\$TEST_REPORT_ID/evaluation | python3 -c \"import sys,json; d=json.load(sys.stdin); assert d['status'] == 'ok'\""

# RPT-04: PUT /api/reports/<id>/resolution updates resolution
check "RPT-04: PUT /api/reports/<id>/resolution updates resolution and returns ok" \
  "[ -n \"\$TEST_REPORT_ID\" ] && curl -sf -X PUT -H 'Content-Type: application/json' -d '{\"resolution\":\"Repaired at branch workshop\"}' http://localhost:5004/api/reports/\$TEST_REPORT_ID/resolution | python3 -c \"import sys,json; d=json.load(sys.stdin); assert d['status'] == 'ok'\""

# RPT-05: GET /api/reports/pending returns list of non-resolved reports
check "RPT-05: GET /api/reports/pending returns list" \
  "curl -sf http://localhost:5004/api/reports/pending | python3 -c \"import sys,json; d=json.load(sys.stdin); assert isinstance(d['data'], list)\""

# ── Pricing Service (port 5005) ──

echo ""
echo "-- Pricing Service --"

# PRICE-01: GET /api/pricing returns sedan/suv/van rates
check "PRICE-01: GET /api/pricing returns sedan rate 12.50" \
  "curl -sf http://localhost:5005/api/pricing | python3 -c \"import sys,json; d=json.load(sys.stdin); assert d['rates']['sedan'] == 12.50\""

# PRICE-02: GET /api/pricing/calculate?vehicle_type=sedan&hours=2 returns 25.00
check "PRICE-02: GET /api/pricing/calculate?vehicle_type=sedan&hours=2 returns 25.00" \
  "curl -sf 'http://localhost:5005/api/pricing/calculate?vehicle_type=sedan&hours=2' | python3 -c \"import sys,json; d=json.load(sys.stdin); assert d['total'] == 25.0\""

echo ""
echo "Results: $PASS passed, $FAIL failed"
if [ "$FAIL" -gt 0 ]; then exit 1; fi
echo "All checks passed."
