#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"

if [[ ! -f "$ROOT/.env" ]]; then
  echo "ERROR: $ROOT/.env not found"
  exit 1
fi

set -a
source "$ROOT/.env"
set +a

if [[ ! -f "$ROOT/firebase-service-account.json" ]]; then
  echo "ERROR: $ROOT/firebase-service-account.json not found"
  exit 1
fi

require_env() {
  local name="$1"
  if [[ -z "${!name:-}" ]]; then
    echo "ERROR: Required environment variable '$name' is missing from .env"
    exit 1
  fi
}

require_env OPENAI_API_KEY
require_env GOOGLE_MAPS_API_KEY

STRIPE_SECRET_VALUE="${STRIPE_SECRET_KEY:-PLACEHOLDER}"
if [[ "$STRIPE_SECRET_VALUE" == "PLACEHOLDER" ]]; then
  echo "NOTE: STRIPE_SECRET_KEY not set in .env; creating api-keys secret with PLACEHOLDER so stripe-wrapper stays on the mock fallback."
fi

echo "=== Setting up Kubernetes Secrets ==="

# Firebase service account file (mounted into all Firestore pods)
kubectl create secret generic firebase-sa \
  --from-file=firebase-service-account.json="$ROOT/firebase-service-account.json" \
  --dry-run=client -o yaml | kubectl apply -f -

# API key secrets (sensitive values — never in YAML)
kubectl create secret generic api-keys \
  --from-literal=STRIPE_SECRET_KEY="${STRIPE_SECRET_VALUE}" \
  --from-literal=OPENAI_API_KEY="${OPENAI_API_KEY}" \
  --from-literal=GOOGLE_MAPS_API_KEY="${GOOGLE_MAPS_API_KEY}" \
  --dry-run=client -o yaml | kubectl apply -f -

echo "=== Secrets created/updated ==="
