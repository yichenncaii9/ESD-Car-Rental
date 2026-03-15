---
phase: 06-kubernetes
plan: "03"
subsystem: infra
tags: [kubernetes, k8s, deployment, configmap, service, firebase, clusterip]

# Dependency graph
requires:
  - phase: 06-02
    provides: RabbitMQ StatefulSet and Kong ConfigMap/Deployment/Service already in cluster
  - phase: 03-atomic-services
    provides: vehicle-service, booking-service, driver-service, report-service, pricing-service Flask apps with /health endpoints on ports 5001-5005
provides:
  - k8s/vehicle-service/deployment.yaml — vehicle-service Deployment with firebase-sa mount, port 5001
  - k8s/vehicle-service/service.yaml — ClusterIP Service port 5001
  - k8s/vehicle-service/configmap.yaml — ConfigMap with FIREBASE_PROJECT_ID and PORT=5001
  - k8s/booking-service/deployment.yaml — booking-service Deployment with firebase-sa mount, port 5002
  - k8s/booking-service/service.yaml — ClusterIP Service port 5002
  - k8s/booking-service/configmap.yaml — ConfigMap with FIREBASE_PROJECT_ID and PORT=5002
  - k8s/driver-service/deployment.yaml — driver-service Deployment with firebase-sa mount, port 5003
  - k8s/driver-service/service.yaml — ClusterIP Service port 5003
  - k8s/driver-service/configmap.yaml — ConfigMap with FIREBASE_PROJECT_ID and PORT=5003
  - k8s/report-service/deployment.yaml — report-service Deployment with firebase-sa mount, port 5004
  - k8s/report-service/service.yaml — ClusterIP Service port 5004
  - k8s/report-service/configmap.yaml — ConfigMap with FIREBASE_PROJECT_ID and PORT=5004
  - k8s/pricing-service/deployment.yaml — pricing-service Deployment, no firebase volume, port 5005
  - k8s/pricing-service/service.yaml — ClusterIP Service port 5005
  - k8s/pricing-service/configmap.yaml — ConfigMap with PORT=5005 only
affects: [06-04-composite-services, 06-05-workers-frontend]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Firebase-connected service pattern: Deployment with firebase-sa secret volume at /secrets, GOOGLE_APPLICATION_CREDENTIALS=/secrets/firebase-service-account.json, FIREBASE_PROJECT_ID from configMapKeyRef"
    - "No-firebase service pattern (pricing-service): Deployment with no volumes/volumeMounts/firebase env vars"
    - "Per-service ConfigMap: one ConfigMap per service containing FIREBASE_PROJECT_ID (if applicable) and PORT"
    - "imagePullPolicy: Never on all atomic service Deployments — uses locally-built Docker images"
    - "ClusterIP Services: each atomic service exposed on its port (5001-5005) for cluster-internal DNS"

key-files:
  created:
    - k8s/vehicle-service/deployment.yaml
    - k8s/vehicle-service/service.yaml
    - k8s/vehicle-service/configmap.yaml
    - k8s/booking-service/deployment.yaml
    - k8s/booking-service/service.yaml
    - k8s/booking-service/configmap.yaml
    - k8s/driver-service/deployment.yaml
    - k8s/driver-service/service.yaml
    - k8s/driver-service/configmap.yaml
    - k8s/report-service/deployment.yaml
    - k8s/report-service/service.yaml
    - k8s/report-service/configmap.yaml
    - k8s/pricing-service/deployment.yaml
    - k8s/pricing-service/service.yaml
    - k8s/pricing-service/configmap.yaml
  modified: []

key-decisions:
  - "pricing-service has no firebase volume or env vars — hardcoded rates, no Firestore dependency (per established Phase 1 decision)"
  - "kubectl dry-run validation unavailable (no live cluster); used python3 yaml.safe_load as established fallback per K8s YAML validated via python3 yaml.safe_load decision in STATE.md"
  - "Per-service ConfigMaps (not shared): each service gets its own ConfigMap with FIREBASE_PROJECT_ID + PORT to maintain clear ownership"

patterns-established:
  - "Firebase-connected atomic service manifest set: configmap.yaml (FIREBASE_PROJECT_ID+PORT) + deployment.yaml (firebase-sa volume, configMapKeyRef, liveness/readiness on /health) + service.yaml (ClusterIP)"
  - "Non-Firebase atomic service manifest set: configmap.yaml (PORT only) + deployment.yaml (no volumes, no firebase env) + service.yaml (ClusterIP)"

requirements-completed: [K8S-01, K8S-04, K8S-05]

# Metrics
duration: 5min
completed: 2026-03-15
---

# Phase 6 Plan 03: Atomic Services K8s Manifests Summary

**15 Kubernetes manifests (Deployment + Service + ConfigMap x 5) for all atomic services with firebase-sa secret volume on 4 Firebase services and no-volume pattern for pricing-service**

## Performance

- **Duration:** ~5 min
- **Started:** 2026-03-15T06:12:39Z
- **Completed:** 2026-03-15T06:17:39Z
- **Tasks:** 2
- **Files modified:** 15

## Accomplishments
- Created 9 manifest files for vehicle-service (5001), booking-service (5002), driver-service (5003) — all Firebase-connected with firebase-sa volume
- Created 6 manifest files for report-service (5004) and pricing-service (5005) — report follows Firebase pattern, pricing has no firebase deps
- All 15 files validated as valid YAML; structural assertions confirmed firebase-sa presence on 4 services and absence on pricing-service
- All ClusterIP Services configured with correct ports 5001-5005 for cluster-internal DNS resolution

## Task Commits

Each task was committed atomically:

1. **Task 1: vehicle-service, booking-service, driver-service manifests** - `141b4e2` (feat)
2. **Task 2: report-service and pricing-service manifests** - `a03ddad` (feat)

**Plan metadata:** (docs commit follows)

## Files Created/Modified
- `k8s/vehicle-service/configmap.yaml` — ConfigMap: FIREBASE_PROJECT_ID=esd-rental-car, PORT=5001
- `k8s/vehicle-service/deployment.yaml` — Deployment: esd-vehicle-service:latest, firebase-sa volume, /health probes at 5001
- `k8s/vehicle-service/service.yaml` — ClusterIP Service port 5001
- `k8s/booking-service/configmap.yaml` — ConfigMap: FIREBASE_PROJECT_ID=esd-rental-car, PORT=5002
- `k8s/booking-service/deployment.yaml` — Deployment: esd-booking-service:latest, firebase-sa volume, /health probes at 5002
- `k8s/booking-service/service.yaml` — ClusterIP Service port 5002
- `k8s/driver-service/configmap.yaml` — ConfigMap: FIREBASE_PROJECT_ID=esd-rental-car, PORT=5003
- `k8s/driver-service/deployment.yaml` — Deployment: esd-driver-service:latest, firebase-sa volume, /health probes at 5003
- `k8s/driver-service/service.yaml` — ClusterIP Service port 5003
- `k8s/report-service/configmap.yaml` — ConfigMap: FIREBASE_PROJECT_ID=esd-rental-car, PORT=5004
- `k8s/report-service/deployment.yaml` — Deployment: esd-report-service:latest, firebase-sa volume, /health probes at 5004
- `k8s/report-service/service.yaml` — ClusterIP Service port 5004
- `k8s/pricing-service/configmap.yaml` — ConfigMap: PORT=5005 only (no FIREBASE_PROJECT_ID)
- `k8s/pricing-service/deployment.yaml` — Deployment: esd-pricing-service:latest, NO volumes/volumeMounts/firebase env
- `k8s/pricing-service/service.yaml` — ClusterIP Service port 5005

## Decisions Made
- pricing-service has no firebase volume/env: confirmed from the established Phase 1 decision (hardcoded rates, no Firestore dependency)
- Used python3 yaml.safe_load for YAML validation as kubectl dry-run requires a live API server (not available in dev without running cluster); this is the established fallback per STATE.md decision
- Per-service ConfigMaps (not shared) for clear ownership — each service owns its FIREBASE_PROJECT_ID + PORT values

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- kubectl dry-run returned connection refused (no live cluster). Resolved by using python3 yaml.safe_load validation as documented in STATE.md established decision: "K8s YAML validated via python3 yaml.safe_load when no cluster is available".

## User Setup Required
None - no external service configuration required for manifest creation.

## Next Phase Readiness
- All 5 atomic service Deployment + Service + ConfigMap manifests ready; composite service manifests can reference these K8s Service DNS names (vehicle-service:5001, booking-service:5002, etc.)
- Plan 06-04 (composite service manifests) can proceed immediately

---
*Phase: 06-kubernetes*
*Completed: 2026-03-15*
