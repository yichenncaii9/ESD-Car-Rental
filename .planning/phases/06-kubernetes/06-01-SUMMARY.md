---
phase: "06"
plan: "01"
subsystem: kubernetes-scaffolding
tags: [kubernetes, docker, scripts, kong, configmap, k8s-infra]
dependency_graph:
  requires: []
  provides:
    - scripts/build-images.sh
    - scripts/setup-secrets.sh
    - scripts/verify_phase6.sh
    - k8s/shared/common-configmap.yaml
    - k8s/kong/kong.yml
  affects:
    - All Wave 2-5 k8s plans (require images built and secrets created before kubectl apply)
tech_stack:
  added: []
  patterns:
    - "bash set -euo pipefail scripts with ROOT discovery via dirname"
    - "kubectl --dry-run=client -o yaml | kubectl apply -f - for idempotent secret creation"
    - "VITE_* vars passed as Docker --build-arg (baked into frontend bundle at build time)"
    - "K8s DNS uses hyphenated service names; Docker Compose uses underscore names — two separate kong.yml files"
key_files:
  created:
    - scripts/build-images.sh
    - scripts/setup-secrets.sh
    - scripts/verify_phase6.sh
    - k8s/shared/common-configmap.yaml
    - k8s/kong/kong.yml
  modified: []
decisions:
  - "Separate k8s/kong/kong.yml from root kong.yml — K8s DNS requires hyphens in service names, Docker Compose uses underscores; two files keep both environments working"
  - "kubectl --dry-run=client -o yaml | kubectl apply -f - pattern for idempotent secret creation (not kubectl apply --server-side)"
  - "firebase-sa and api-keys as distinct Secrets — firebase-sa uses --from-file (JSON mount), api-keys uses --from-literal (individual env vars)"
metrics:
  duration: "~5 minutes"
  completed: "2026-03-15"
  tasks_completed: 3
  files_created: 5
  files_modified: 0
---

# Phase 6 Plan 01: Kubernetes Scaffolding — Scripts and Shared Config Summary

**One-liner:** Three prerequisite bash scripts and two K8s config files that enable all subsequent Kubernetes deployment plans (Waves 2-5).

## What Was Built

### Task 1: build-images.sh and setup-secrets.sh (commit 2ef6304)

**scripts/build-images.sh** — builds all 18 esd-* Docker images from local Dockerfiles in one command:
- Pulls official rabbitmq:3-management and kong:3.0-alpine
- Builds 5 atomic services (ports 5001-5005), 4 composite services (ports 6001-6004), 4 wrappers, websocket-server, 2 workers, frontend
- Frontend build passes VITE_* as --build-arg so Firebase config is baked into the Vite bundle at build time
- Requires imagePullPolicy: Never on all K8s manifests (local images, no registry push)

**scripts/setup-secrets.sh** — creates K8s secrets idempotently:
- `firebase-sa` secret: --from-file mounts firebase-service-account.json into all Firestore pods
- `api-keys` secret: --from-literal for STRIPE_SECRET_KEY, OPENAI_API_KEY, GOOGLE_MAPS_API_KEY, TWILIO_* vars
- Uses `--dry-run=client -o yaml | kubectl apply -f -` pattern — safe to run multiple times without error

### Task 2: verify_phase6.sh smoke test script (commit 4067d57)

**scripts/verify_phase6.sh** — covers K8S-01 through K8S-07:
- `pod_check()`: checks `kubectl get pods -l app=$selector | grep Running`
- `check()`: generic command success/fail helper
- K8S-01: pod_check for all 19 services (rabbitmq, kong, 5 atomic, 4 composite, 4 wrappers, websocket, 2 workers, frontend)
- K8S-02: rabbitmq StatefulSet and PVC existence
- K8S-03: Kong admin API + /api/vehicles non-502 check
- K8S-04: firebase-sa secret exists
- K8S-05: common-config and kong-config ConfigMaps exist
- K8S-06: docker compose config validates root docker-compose.yml
- K8S-07: POST to /api/book-car, /api/cancel-booking, /api/report-issue — all non-502
- KONG_BASE=http://localhost:8000; requires `kubectl port-forward svc/kong 8000:8000` documented at script top

### Task 3: common-configmap.yaml and k8s/kong/kong.yml (commit 77251f4)

**k8s/shared/common-configmap.yaml** — ConfigMap `common-config`:
- RABBITMQ_HOST=rabbitmq, RABBITMQ_PORT=5672
- WEBSOCKET_SERVER_URL=http://websocket-server:6100
- TWILIO_WRAPPER_HOST=twilio-wrapper-http:6203

**k8s/kong/kong.yml** — Kong declarative config adapted for K8s DNS:
- All 9 upstream URLs use hyphenated K8s Service names:
  - composite_book_car → composite-book-car (port 6001)
  - composite_cancel_booking → composite-cancel-booking (port 6002)
  - composite_report_issue → composite-report-issue (port 6003)
  - composite_resolve_issue → composite-resolve-issue (port 6004)
  - vehicle_service → vehicle-service (port 5001)
  - booking_service → booking-service (port 5002)
  - driver_service → driver-service (port 5003)
  - report_service → report-service (port 5004)
  - pricing_service → pricing-service (port 5005)
- All other content (RS256 JWT consumer, CORS plugins, rate-limiting, routes) identical to root kong.yml
- Root kong.yml untouched — Docker Compose continues to work normally

**k8s/ directory tree:** All 19 service subdirectories scaffolded with .gitkeep for Waves 2-5 manifests.

## Deviations from Plan

None — plan executed exactly as written.

## Verification Results

- `bash -n scripts/build-images.sh` — SYNTAX OK
- `bash -n scripts/setup-secrets.sh` — SYNTAX OK
- `bash -n scripts/verify_phase6.sh` — SYNTAX OK
- `grep composite-book-car k8s/kong/kong.yml` — present (hyphenated)
- `grep composite_book_car k8s/kong/kong.yml` — absent (no underscores in URLs)
- `grep composite_book_car kong.yml` — still present (root file unchanged)
- `grep rabbitmq k8s/shared/common-configmap.yaml` — present

## Self-Check: PASSED

Files verified:
- FOUND: scripts/build-images.sh
- FOUND: scripts/setup-secrets.sh
- FOUND: scripts/verify_phase6.sh
- FOUND: k8s/shared/common-configmap.yaml
- FOUND: k8s/kong/kong.yml

Commits verified:
- FOUND: 2ef6304 (build-images.sh + setup-secrets.sh)
- FOUND: 4067d57 (verify_phase6.sh)
- FOUND: 77251f4 (common-configmap.yaml + k8s/kong/kong.yml)
