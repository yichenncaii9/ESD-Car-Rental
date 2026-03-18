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

# ── 2. Apply all k8s manifests ─────────────────────────────────────────────────
echo "=== Applying k8s manifests ==="
kubectl apply -f "$ROOT/k8s/" --recursive

# ── 3. Restart all deployments to pick up new images ──────────────────────────
echo "=== Restarting all deployments ==="
kubectl rollout restart deployment --all

echo ""
echo "=== Done. Watching pod status (Ctrl+C to exit) ==="
kubectl get pods -w
