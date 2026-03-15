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
    if docker-compose logs --no-color --tail=100 "$service" 2>/dev/null | grep -qE "$pattern"; then
        echo "PASS  $label"
        PASS=$((PASS + 1))
    else
        echo "FAIL  $label"
        FAIL=$((FAIL + 1))
    fi
}

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

# WORK-02: Service team SMS sent
log_check "WORK-02: Service team SMS sent" \
    "Service team SMS sent" "twilio_wrapper"

# WORK-05: activity_log queue binding
log_check "WORK-05: activity_log queue binding" \
    "Waiting for messages" "activity_log"

# WORK-07 (activity_log): RabbitMQ connection
log_check "WORK-07 (activity_log): RabbitMQ connection" \
    "Connected to RabbitMQ" "activity_log"

# WORK-06: Firestore write
log_check "WORK-06: Firestore write" \
    "Firestore write" "activity_log"

# WS-01 container: websocket_server log healthy
log_check "WS-01 container: websocket_server log healthy" \
    "Client connected|notify received|Phase 5" "websocket_server"

echo ""
echo "Results: ${PASS} passed, ${FAIL} failed"

if [ "$FAIL" -gt 0 ]; then
    exit 1
fi
