#!/usr/bin/env bash
# deploy-k8s.sh — Build all images for k8s and restart deployments
# Usage:
#   ./scripts/deploy-k8s.sh          # build all images + apply manifests + restart all
#   ./scripts/deploy-k8s.sh --apply  # apply manifests + restart all (skip rebuild)
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"

SKIP_BUILD=false
if [[ "${1:-}" == "--apply" ]]; then
  SKIP_BUILD=true
fi

# ── 1. Build images ────────────────────────────────────────────────────────────
if [ "$SKIP_BUILD" = false ]; then
  echo "=== Building all images for k8s (VITE_API_BASE_URL → :30000) ==="

  set -a; source "$ROOT/.env"; set +a

  # Override API base URL for k8s NodePort
  export VITE_API_BASE_URL="http://localhost:30000"

  # Reuse the existing build script (it reads VITE_API_BASE_URL from env)
  bash "$ROOT/scripts/build-images.sh"

  echo ""
fi

# ── 2. Ensure we're on the local docker-desktop context ───────────────────────
CURRENT_CONTEXT=$(kubectl config current-context 2>/dev/null || echo "none")
if [[ "$CURRENT_CONTEXT" != "docker-desktop" ]]; then
  echo "ERROR: kubectl context is '$CURRENT_CONTEXT', expected 'docker-desktop'."
  echo "Run: kubectl config use-context docker-desktop"
  exit 1
fi

# ── 3. Bootstrap Secrets + generated ConfigMaps ───────────────────────────────
echo "=== Ensuring required Kubernetes Secrets exist ==="
bash "$ROOT/scripts/setup-secrets.sh"

# ── 4. Apply all k8s manifests ─────────────────────────────────────────────────
echo "=== Applying k8s manifests ==="
find "$ROOT/k8s" -type f \( -name '*.yaml' -o -name '*.yml' \) \
  ! -path "$ROOT/k8s/kong/kong.yml" \
  -print0 | xargs -0 -n 1 kubectl apply -f

echo "=== Syncing Kong ConfigMap from k8s/kong/kong.yml ==="
kubectl create configmap kong-config \
  --from-file=kong.yml="$ROOT/k8s/kong/kong.yml" \
  --dry-run=client -o yaml | kubectl apply -f -

DEPLOYMENTS=(
  vehicle-service
  booking-service
  driver-service
  report-service
  composite-book-car
  composite-cancel-booking
  composite-report-issue
  composite-resolve-issue
  openai-wrapper
  googlemaps-wrapper
  stripe-wrapper
  twilio-wrapper-http
  websocket-server
  twilio-worker
  activity-log
  frontend
  kong
)

# ── 5. Restart all workloads to pick up new images/config ─────────────────────
echo "=== Restarting all deployments ==="
for deployment in "${DEPLOYMENTS[@]}"; do
  kubectl rollout restart "deployment/$deployment"
done
kubectl rollout restart statefulset/rabbitmq

# ── 6. Wait for workloads to stabilize ────────────────────────────────────────
echo "=== Waiting for RabbitMQ to be ready ==="
kubectl rollout status statefulset/rabbitmq --timeout=180s

echo "=== Waiting for critical deployments ==="
for deployment in "${DEPLOYMENTS[@]}"; do
  echo "  -> $deployment"
  kubectl rollout status "deployment/$deployment" --timeout=180s
done

# ── 7. Push Kong declarative config via admin API ────────────────────────────
# Kong DB-less mode reads kong.yml once at pod start. If the configmap kubelet
# sync races with pod startup, Kong loads a stale config. Pushing via admin API
# after Kong is ready guarantees the correct config is always applied.
echo "=== Waiting for Kong to be ready ==="
kubectl rollout status deployment/kong --timeout=120s

echo "=== Pushing Kong declarative config via admin API ==="
KONG_ADMIN="http://localhost:30001"
for i in 1 2 3 4 5; do
  HTTP=$(curl -s -o /dev/null -w "%{http_code}" "$KONG_ADMIN/")
  if [[ "$HTTP" == "200" ]]; then break; fi
  echo "  Kong admin not ready yet (attempt $i), waiting 5s..."
  sleep 5
done
curl -s -X POST "$KONG_ADMIN/config" \
  -F "config=<$ROOT/k8s/kong/kong.yml" \
  -o /dev/null -w "Kong config push: HTTP %{http_code}\n"

echo ""
echo "=== Done. Watching pod status (Ctrl+C to exit) ==="
kubectl get pods -w
