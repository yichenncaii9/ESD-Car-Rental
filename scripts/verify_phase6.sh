#!/usr/bin/env bash
set -euo pipefail

# PREREQUISITE: kubectl port-forward svc/kong 8000:8000
# Run in a separate terminal before executing this script.

echo "=== Phase 6 Smoke Tests: Kubernetes ==="
echo "    Requires: kubectl port-forward svc/kong 8000:8000"
echo ""

PASS=0
FAIL=0
KONG_BASE="http://localhost:8000"

check() {
    local label="$1"; shift
    if "$@" > /dev/null 2>&1; then
        echo "PASS  $label"; PASS=$((PASS + 1))
    else
        echo "FAIL  $label"; FAIL=$((FAIL + 1))
    fi
}

pod_check() {
    local label="$1"
    local selector="$2"
    if kubectl get pods -l "app=$selector" --no-headers 2>/dev/null | grep -q "Running"; then
        echo "PASS  $label"; PASS=$((PASS + 1))
    else
        echo "FAIL  $label"; FAIL=$((FAIL + 1))
    fi
}

# ── K8S-01: All pods Running ──────────────────────────────────────────────────
for svc in rabbitmq kong vehicle-service booking-service driver-service \
           report-service pricing-service composite-book-car \
           composite-cancel-booking composite-report-issue \
           composite-resolve-issue openai-wrapper googlemaps-wrapper \
           stripe-wrapper twilio-wrapper-http websocket-server \
           twilio-worker activity-log frontend; do
    pod_check "K8S-01: $svc pod Running" "$svc"
done

# ── K8S-02: RabbitMQ StatefulSet + PVC ───────────────────────────────────────
check "K8S-02: rabbitmq StatefulSet exists" kubectl get statefulset rabbitmq
check "K8S-02: rabbitmq PVC exists" bash -c "kubectl get pvc | grep -q rabbitmq"

# ── K8S-03: Kong routing live (non-502) ──────────────────────────────────────
check "K8S-03: Kong admin API responds" curl -sf "http://localhost:8001/"
check "K8S-03: Kong routes /api/vehicles (non-502)" \
    bash -c "code=\$(curl -s -o /dev/null -w '%{http_code}' '$KONG_BASE/api/vehicles'); [ \"\$code\" != '502' ] && [ \"\$code\" != '000' ]"

# ── K8S-04: Firebase secret exists ───────────────────────────────────────────
check "K8S-04: firebase-sa secret exists" kubectl get secret firebase-sa

# ── K8S-05: ConfigMaps exist ─────────────────────────────────────────────────
check "K8S-05: common-config ConfigMap exists" kubectl get configmap common-config
check "K8S-05: kong-config ConfigMap exists" kubectl get configmap kong-config

# ── K8S-06: docker-compose.yml still valid ───────────────────────────────────
check "K8S-06: docker-compose.yml valid" docker compose config

# ── K8S-07: Three scenarios route through Kong (non-502) ─────────────────────
for path in /api/book-car /api/cancel-booking /api/report-issue; do
    check "K8S-07: Kong routes $path (non-502)" \
        bash -c "code=\$(curl -s -o /dev/null -w '%{http_code}' -X POST '$KONG_BASE$path' -H 'Content-Type: application/json' -d '{}' 2>/dev/null || echo 000); [ \"\$code\" != '502' ] && [ \"\$code\" != '000' ]"
done

# ── Summary ───────────────────────────────────────────────────────────────────
echo ""
echo "Results: ${PASS} passed, ${FAIL} failed"
[ "$FAIL" -gt 0 ] && exit 1 || exit 0
