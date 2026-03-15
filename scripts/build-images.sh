#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"

set -a; source "$ROOT/.env"; set +a

echo "=== Building all ESD images ==="

# Official images — pull to ensure available locally
docker pull rabbitmq:3-management
docker pull kong:3.0-alpine

# Atomic services
docker build -t esd-vehicle-service:latest    "$ROOT/atomic/vehicle_service"
docker build -t esd-booking-service:latest    "$ROOT/atomic/booking_service"
docker build -t esd-driver-service:latest     "$ROOT/atomic/driver_service"
docker build -t esd-report-service:latest     "$ROOT/atomic/report_service"
docker build -t esd-pricing-service:latest    "$ROOT/atomic/pricing_service"

# Composite services
docker build -t esd-composite-book-car:latest       "$ROOT/composite/book_car"
docker build -t esd-composite-cancel-booking:latest "$ROOT/composite/cancel_booking"
docker build -t esd-composite-report-issue:latest   "$ROOT/composite/report_issue"
docker build -t esd-composite-resolve-issue:latest  "$ROOT/composite/resolve_issue"

# Wrappers
docker build -t esd-openai-wrapper:latest      "$ROOT/wrappers/openai_wrapper"
docker build -t esd-googlemaps-wrapper:latest  "$ROOT/wrappers/googlemaps_wrapper"
docker build -t esd-stripe-wrapper:latest      "$ROOT/wrappers/stripe_wrapper"
docker build -t esd-twilio-wrapper-http:latest "$ROOT/wrappers/twilio_wrapper"

# WebSocket server
docker build -t esd-websocket-server:latest "$ROOT/websocket_server"

# Workers
docker build -t esd-twilio-worker:latest "$ROOT/workers/twilio_wrapper"
docker build -t esd-activity-log:latest  "$ROOT/workers/activity_log"

# Frontend — VITE_* baked at build time
docker build -t esd-frontend:latest \
  --build-arg VITE_FIREBASE_API_KEY="${VITE_FIREBASE_API_KEY}" \
  --build-arg VITE_FIREBASE_AUTH_DOMAIN="${VITE_FIREBASE_AUTH_DOMAIN}" \
  --build-arg VITE_FIREBASE_PROJECT_ID="${VITE_FIREBASE_PROJECT_ID}" \
  --build-arg VITE_FIREBASE_STORAGE_BUCKET="${VITE_FIREBASE_STORAGE_BUCKET}" \
  --build-arg VITE_FIREBASE_MESSAGING_SENDER_ID="${VITE_FIREBASE_MESSAGING_SENDER_ID}" \
  --build-arg VITE_FIREBASE_APP_ID="${VITE_FIREBASE_APP_ID}" \
  --build-arg VITE_GOOGLE_MAPS_KEY="${VITE_GOOGLE_MAPS_KEY}" \
  --build-arg VITE_API_BASE_URL="${VITE_API_BASE_URL:-http://localhost:8000}" \
  "$ROOT/frontend"

echo "=== All images built ==="
