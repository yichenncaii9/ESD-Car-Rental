#!/usr/bin/env bash
# verify_phase4.sh — Phase 4 composite services smoke test
# Tests COMP-01 through COMP-11 via direct service ports (bypasses Kong/JWT)
# Usage: bash verify_phase4.sh
set -euo pipefail

# ─── Service base URLs (direct, no Kong) ────────────────────────────────────
BOOK_CAR_URL="http://localhost:6001"
CANCEL_URL="http://localhost:6002"
REPORT_URL="http://localhost:6003"
RESOLVE_URL="http://localhost:6004"
VEHICLE_URL="http://localhost:5001"
BOOKING_URL="http://localhost:5002"
REPORT_SVC_URL="http://localhost:5004"

# ─── Pass/fail counters ──────────────────────────────────────────────────────
PASS=0; FAIL=0

check() {
  local label="$1"; local expected_code="$2"; local actual_code="$3"; local body="$4"
  if [ "$actual_code" = "$expected_code" ]; then
    echo "PASS [$label] HTTP $actual_code"; PASS=$((PASS+1))
  else
    echo "FAIL [$label] expected $expected_code got $actual_code | body: $body"; FAIL=$((FAIL+1))
  fi
}

json_field() { python3 -c "import sys,json; d=json.loads(sys.argv[1]); print(d.get('$1','MISSING'))" "$2" 2>/dev/null || echo "PARSE_ERROR"; }

# ─── Health Checks ───────────────────────────────────────────────────────────
echo "=== Health Checks ==="
for port in 6001 6002 6003 6004; do
  code=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:$port/health")
  check "composite-port-$port-health" "200" "$code" ""
done

# ─── COMP-01 / COMP-02: book_car ─────────────────────────────────────────────
echo "=== COMP-01: POST /api/book-car ==="
# Use a pre-seeded vehicle_id (plate number) from seed_data
# book_car body: user_uid, vehicle_id, vehicle_type, pickup_datetime (far future for full refund tier), hours
BOOK_BODY='{"user_uid":"test_user_001","vehicle_id":"SBA1234A","vehicle_type":"sedan","pickup_datetime":"2028-01-01T10:00:00","hours":2}'
resp=$(curl -s -w "\n%{http_code}" -X POST -H "Content-Type: application/json" -d "$BOOK_BODY" "$BOOK_CAR_URL/api/book-car")
body=$(echo "$resp" | head -n -1); code=$(echo "$resp" | tail -n 1)
check "COMP-01 book-car 201" "201" "$code" "$body"
TEST_BOOKING_ID=$(json_field "booking_id" "$body")
echo "  booking_id=$TEST_BOOKING_ID"

# ─── COMP-03 through COMP-07: cancel_booking ─────────────────────────────────
echo "=== COMP-03 to COMP-07: POST /api/cancel-booking ==="
# Use booking from COMP-01 if it succeeded
if [ "$TEST_BOOKING_ID" != "MISSING" ] && [ "$TEST_BOOKING_ID" != "PARSE_ERROR" ]; then
  CANCEL_BODY="{\"booking_id\":\"$TEST_BOOKING_ID\"}"
  resp=$(curl -s -w "\n%{http_code}" -X POST -H "Content-Type: application/json" -d "$CANCEL_BODY" "$CANCEL_URL/api/cancel-booking")
  body=$(echo "$resp" | head -n -1); code=$(echo "$resp" | tail -n 1)
  check "COMP-05 cancel-booking 200" "200" "$code" "$body"
  # COMP-07: check response shape
  refund_status=$(json_field "refund_status" "$body")
  check "COMP-07 refund_status present" "processed" "$refund_status" "$body"
  booking_status=$(json_field "status" "$body")
  check "COMP-07 status=cancelled" "cancelled" "$booking_status" "$body"
else
  echo "SKIP cancel-booking tests — no booking_id from COMP-01"
fi
# COMP-03: cancel already-cancelled booking returns 400
if [ "$TEST_BOOKING_ID" != "MISSING" ] && [ "$TEST_BOOKING_ID" != "PARSE_ERROR" ]; then
  resp2=$(curl -s -w "\n%{http_code}" -X POST -H "Content-Type: application/json" -d "$CANCEL_BODY" "$CANCEL_URL/api/cancel-booking")
  code2=$(echo "$resp2" | tail -n 1)
  check "COMP-03 cancel-already-cancelled 400" "400" "$code2" "$(echo "$resp2" | head -n -1)"
fi

# ─── COMP-08 / COMP-09 / COMP-10: report_issue ───────────────────────────────
echo "=== COMP-08 to COMP-10: POST /api/report-issue ==="
# COMP-09: RabbitMQ publish verified manually at localhost:15672 — not automatable via curl
REPORT_BODY='{"booking_id":"test_booking_001","vehicle_id":"SBA1234A","user_uid":"test_user_001","lat":1.3521,"lng":103.8198,"description":"Scratch on rear bumper"}'
resp=$(curl -s -w "\n%{http_code}" -X POST -H "Content-Type: application/json" -d "$REPORT_BODY" "$REPORT_URL/api/report-issue")
body=$(echo "$resp" | head -n -1); code=$(echo "$resp" | tail -n 1)
check "COMP-08/10 report-issue 200" "200" "$code" "$body"
TEST_REPORT_ID=$(json_field "report_id" "$body")
report_status=$(json_field "status" "$body")
check "COMP-10 status=submitted" "submitted" "$report_status" "$body"
severity=$(json_field "severity" "$body")
[ "$severity" != "MISSING" ] && [ "$severity" != "PARSE_ERROR" ] && check "COMP-10 severity present" "$severity" "$severity" "$body" || check "COMP-10 severity present" "low_or_medium_or_high" "$severity" "$body"
echo "  report_id=$TEST_REPORT_ID severity=$severity"

# ─── COMP-11: resolve_issue ───────────────────────────────────────────────────
echo "=== COMP-11: POST /api/resolve-issue ==="
if [ "$TEST_REPORT_ID" != "MISSING" ] && [ "$TEST_REPORT_ID" != "PARSE_ERROR" ]; then
  RESOLVE_BODY="{\"report_id\":\"$TEST_REPORT_ID\",\"resolution\":\"Damage assessed and repaired\",\"driver_phone\":\"+6591234567\"}"
  resp=$(curl -s -w "\n%{http_code}" -X POST -H "Content-Type: application/json" -d "$RESOLVE_BODY" "$RESOLVE_URL/api/resolve-issue")
  body=$(echo "$resp" | head -n -1); code=$(echo "$resp" | tail -n 1)
  check "COMP-11 resolve-issue 200" "200" "$code" "$body"
  sms_status=$(json_field "sms_status" "$body")
  echo "  sms_status=$sms_status (sent or unsent both acceptable)"
else
  echo "SKIP resolve-issue — no report_id from COMP-08"
fi

# ─── Summary ─────────────────────────────────────────────────────────────────
echo ""
echo "=== Phase 4 Verification Summary ==="
echo "PASS: $PASS | FAIL: $FAIL"
[ $FAIL -eq 0 ] && echo "ALL CHECKS PASSED" && exit 0 || echo "SOME CHECKS FAILED" && exit 1
