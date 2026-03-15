#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"

set -a; source "$ROOT/.env"; set +a

echo "=== Setting up Kubernetes Secrets ==="

# Firebase service account file (mounted into all Firestore pods)
kubectl create secret generic firebase-sa \
  --from-file=firebase-service-account.json="$ROOT/firebase-service-account.json" \
  --dry-run=client -o yaml | kubectl apply -f -

# API key secrets (sensitive values — never in YAML)
kubectl create secret generic api-keys \
  --from-literal=STRIPE_SECRET_KEY="${STRIPE_SECRET_KEY}" \
  --from-literal=OPENAI_API_KEY="${OPENAI_API_KEY}" \
  --from-literal=GOOGLE_MAPS_API_KEY="${GOOGLE_MAPS_API_KEY}" \
  --from-literal=TWILIO_ACCOUNT_SID="${TWILIO_ACCOUNT_SID}" \
  --from-literal=TWILIO_AUTH_TOKEN="${TWILIO_AUTH_TOKEN}" \
  --from-literal=TWILIO_FROM_NUMBER="${TWILIO_FROM_NUMBER}" \
  --from-literal=TWILIO_SERVICE_TEAM_NUMBER="${TWILIO_SERVICE_TEAM_NUMBER}" \
  --dry-run=client -o yaml | kubectl apply -f -

echo "=== Secrets created/updated ==="
