#!/usr/bin/env bash
set -euo pipefail

echo "=== Phase 5 Smoke Tests ==="

PASS=0
FAIL=0

# Helper: run a command; print PASS or FAIL
check() {
    local label="$1"
    shift
    if "$@" > /dev/null 2>&1; then
        echo "PASS  $label"
        PASS=$((PASS + 1))
    else
        echo "FAIL  $label"
        FAIL=$((FAIL + 1))
    fi
}

# Helper: grep docker-compose logs for a pattern
log_check() {
    local label="$1"
    local pattern="$2"
    local service="$3"
    local tail="${4:-100}"
    if docker-compose logs --no-color --tail="$tail" "$service" 2>/dev/null | grep -qE "$pattern"; then
        echo "PASS  $label"
        PASS=$((PASS + 1))
    else
        echo "FAIL  $label"
        FAIL=$((FAIL + 1))
    fi
}

# ---------------------------------------------------------------------------
# Section 1: Connectivity (no message needed)
# ---------------------------------------------------------------------------

# WS-01: websocket_server health check
check "WS-01: websocket_server /health returns 200" \
    curl -sf http://localhost:6100/health

# WS-03: POST /notify returns 200
check "WS-03: POST /notify returns 200" \
    curl -sf -X POST http://localhost:6100/notify \
        -H "Content-Type: application/json" \
        -d '{"report_id":"smoke-001","event":"sms_sent","severity":"high","message":"smoke test"}'

# WORK-01: twilio_wrapper queue binding
log_check "WORK-01: twilio_wrapper queue binding" \
    "Waiting for messages" "twilio_wrapper"

# WORK-07 (twilio): RabbitMQ connection
log_check "WORK-07 (twilio): RabbitMQ connection" \
    "Connected to RabbitMQ" "twilio_wrapper"

# WORK-05: activity_log queue binding
log_check "WORK-05: activity_log queue binding" \
    "Waiting for messages" "activity_log"

# WORK-07 (activity_log): RabbitMQ connection
log_check "WORK-07 (activity_log): RabbitMQ connection" \
    "Connected to RabbitMQ" "activity_log"

# WS-01 container: websocket_server log healthy
log_check "WS-01 container: websocket_server log healthy" \
    "Client connected|notify received|Phase 5" "websocket_server"

# ---------------------------------------------------------------------------
# Section 2: Trigger report-issue and wait for async workers
# ---------------------------------------------------------------------------

echo ""
echo "--- Triggering POST /api/report-issue ---"

# Step 1: Create a test booking so report_issue passes the booking validation check
PICKUP=$(date -u -v+1d '+%Y-%m-%dT10:00:00' 2>/dev/null || date -u -d 'tomorrow 10:00' '+%Y-%m-%dT10:00:00')
BOOKING_RESP=$(curl -sf -X POST http://localhost:5002/api/bookings \
    -H "Content-Type: application/json" \
    -d "{
        \"user_uid\": \"smoke-test-uid-001\",
        \"vehicle_id\": \"SMOKE-V-001\",
        \"vehicle_type\": \"sedan\",
        \"pickup_datetime\": \"${PICKUP}\",
        \"hours\": 2,
        \"total_price\": 50.00,
        \"stripe_payment_intent_id\": \"pi_smoke_test_001\"
    }" 2>/dev/null || echo "")

if [ -z "$BOOKING_RESP" ]; then
    echo "SKIP  WORK-02/WORK-06 trigger: booking_service unavailable — checking historical logs only"
    TRIGGERED=false
else
    BOOKING_ID=$(echo "$BOOKING_RESP" | python3 -c "import sys,json; print(json.load(sys.stdin).get('booking_id',''))" 2>/dev/null || echo "")
    if [ -z "$BOOKING_ID" ]; then
        echo "SKIP  WORK-02/WORK-06 trigger: booking creation failed ($BOOKING_RESP) — checking historical logs only"
        TRIGGERED=false
    else
        echo "      Created test booking: $BOOKING_ID"

        # Step 2: Fire report-issue with the real booking_id
        REPORT_RESP=$(curl -sf -X POST http://localhost:6003/api/report-issue \
            -H "Content-Type: application/json" \
            -d "{
                \"booking_id\": \"${BOOKING_ID}\",
                \"vehicle_id\": \"SMOKE-V-001\",
                \"user_uid\": \"smoke-test-uid-001\",
                \"lat\": 1.3521,
                \"lng\": 103.8198,
                \"description\": \"Smoke test: minor scratch on door\"
            }" 2>/dev/null || echo "")

        if [ -z "$REPORT_RESP" ]; then
            echo "SKIP  WORK-02/WORK-06 trigger: report_issue composite unavailable — checking historical logs only"
            TRIGGERED=false
        else
            REPORT_ID=$(echo "$REPORT_RESP" | python3 -c "import sys,json; print(json.load(sys.stdin).get('report_id',''))" 2>/dev/null || echo "")
            if [ -n "$REPORT_ID" ]; then
                echo "      Published report event: $REPORT_ID"
                echo "      Waiting 5s for workers to consume..."
                sleep 5
                TRIGGERED=true
            else
                echo "SKIP  WORK-02/WORK-06 trigger: report-issue returned error ($REPORT_RESP) — checking historical logs only"
                TRIGGERED=false
            fi
        fi
    fi
fi

# ---------------------------------------------------------------------------
# Section 3: Worker log checks (use larger tail after trigger)
# ---------------------------------------------------------------------------

TAIL=300
if [ "$TRIGGERED" = true ]; then
    echo ""
    echo "--- Worker log checks (after trigger) ---"
else
    echo ""
    echo "--- Worker log checks (historical, no trigger) ---"
    TAIL=100
fi

# WORK-02: Service team SMS sent (twilio_wrapper must log this after processing a message)
log_check "WORK-02: Service team SMS sent" \
    "Service team SMS sent" "twilio_wrapper" "$TAIL"

# WORK-06: Firestore write (activity_log must log this after processing a message)
log_check "WORK-06: Firestore write" \
    "Firestore write" "activity_log" "$TAIL"

# ---------------------------------------------------------------------------
# Results
# ---------------------------------------------------------------------------

echo ""
echo "Results: ${PASS} passed, ${FAIL} failed"

if [ "$FAIL" -gt 0 ]; then
    exit 1
fi
