---
phase: 06-kubernetes
plan: "05"
subsystem: infra
tags: [kubernetes, k8s, composite-services, amqp-workers, firebase, clusterip, rabbitmq, twilio, configmap, deployment]

# Dependency graph
requires:
  - phase: 06-03
    provides: Atomic service K8s manifests (vehicle/booking/driver/report/pricing) with ClusterIP Services at ports 5001-5005
  - phase: 06-04
    provides: Wrapper and websocket-server K8s manifests (openai/googlemaps/stripe/twilio-http/websocket) with ClusterIP Services at ports 6100-6203

provides:
  - k8s/composite-book-car/deployment.yaml — Deployment: firebase-sa mount, port 6001, all 5 inter-service URL env vars from configmap
  - k8s/composite-book-car/service.yaml — ClusterIP Service port 6001
  - k8s/composite-book-car/configmap.yaml — ConfigMap: FIREBASE_PROJECT_ID + PORT + 5 hyphenated K8s host names (driver/vehicle/pricing/booking/stripe)
  - k8s/composite-cancel-booking/deployment.yaml — Deployment: firebase-sa mount, port 6002, 4 inter-service URL env vars from configmap
  - k8s/composite-cancel-booking/service.yaml — ClusterIP Service port 6002
  - k8s/composite-cancel-booking/configmap.yaml — ConfigMap: FIREBASE_PROJECT_ID + PORT + 4 hyphenated K8s host names (booking/vehicle/pricing/stripe)
  - k8s/composite-report-issue/deployment.yaml — Deployment: firebase-sa mount, port 6003, 4 inter-service URL env vars from configmap + RABBITMQ_HOST/PORT from common-config
  - k8s/composite-report-issue/service.yaml — ClusterIP Service port 6003
  - k8s/composite-report-issue/configmap.yaml — ConfigMap: FIREBASE_PROJECT_ID + PORT + 4 hyphenated K8s host names (booking/report/maps/openai)
  - k8s/composite-resolve-issue/deployment.yaml — Deployment: firebase-sa mount, port 6004, REPORT_SERVICE_HOST from configmap + TWILIO_WRAPPER_HOST from common-config
  - k8s/composite-resolve-issue/service.yaml — ClusterIP Service port 6004
  - k8s/composite-resolve-issue/configmap.yaml — ConfigMap: FIREBASE_PROJECT_ID + PORT + REPORT_SERVICE_HOST
  - k8s/twilio-worker/deployment.yaml — AMQP consumer Deployment: 3 env from common-config + 4 Twilio secretKeyRef from api-keys; no ports, no Service
  - k8s/activity-log/deployment.yaml — AMQP consumer Deployment: 3 env from common-config + firebase-sa mount + FIREBASE_PROJECT_ID from activity-log-config; no ports, no Service
  - k8s/activity-log/configmap.yaml — ConfigMap: FIREBASE_PROJECT_ID for activity-log

affects:
  - 06-06 (frontend/ingress — final phase)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Composite Firebase pattern: Deployment with firebase-sa secret volume at /secrets, GOOGLE_APPLICATION_CREDENTIALS=/secrets/firebase-service-account.json, per-service configMapKeyRef env vars, liveness/readiness at /health, ClusterIP Service"
    - "Inter-service URL override pattern: ConfigMap sets hyphenated K8s Service DNS names (e.g. vehicle-service:5001) to override app.py Docker Compose underscore defaults (e.g. vehicle_service:5001)"
    - "Cross-ConfigMap reference pattern: composite-report-issue and composite-resolve-issue pull shared vars (RABBITMQ_HOST, RABBITMQ_PORT, TWILIO_WRAPPER_HOST) from common-config rather than duplicating them in their own ConfigMaps"
    - "AMQP worker Deployment pattern: no ports, no livenessProbe, no Service — pure consumer; pika retry self-heals when RabbitMQ starts"
    - "imagePullPolicy: Never on all 6 Deployments — uses locally-built Docker images for Minikube"

key-files:
  created:
    - k8s/composite-book-car/configmap.yaml
    - k8s/composite-book-car/deployment.yaml
    - k8s/composite-book-car/service.yaml
    - k8s/composite-cancel-booking/configmap.yaml
    - k8s/composite-cancel-booking/deployment.yaml
    - k8s/composite-cancel-booking/service.yaml
    - k8s/composite-report-issue/configmap.yaml
    - k8s/composite-report-issue/deployment.yaml
    - k8s/composite-report-issue/service.yaml
    - k8s/composite-resolve-issue/configmap.yaml
    - k8s/composite-resolve-issue/deployment.yaml
    - k8s/composite-resolve-issue/service.yaml
    - k8s/twilio-worker/deployment.yaml
    - k8s/activity-log/configmap.yaml
    - k8s/activity-log/deployment.yaml
  modified: []

key-decisions:
  - "Inter-service host env vars use hyphenated K8s DNS names in ConfigMaps — app.py os.environ.get() defaults use Docker Compose underscore names which cause NXDOMAIN in K8s; ConfigMap values override the defaults"
  - "RABBITMQ_HOST, RABBITMQ_PORT for composite-report-issue and TWILIO_WRAPPER_HOST for composite-resolve-issue sourced from common-config (not duplicated in per-service ConfigMaps)"
  - "AMQP workers (twilio-worker, activity-log) intentionally have no K8s Service — pure consumers with no inbound HTTP traffic; CrashLoopBackOff expected until RabbitMQ ready, pika retry self-heals"
  - "python3 yaml.safe_load used for YAML validation — kubectl --dry-run=client requires live API server (not available in dev); established fallback per STATE.md decisions"

requirements-completed: [K8S-01, K8S-04, K8S-05, K8S-07]

# Metrics
duration: ~3min
completed: 2026-03-15
---

# Phase 6 Plan 05: Composite Services and AMQP Workers K8s Manifests Summary

**15 K8s manifests for 4 composite services (ports 6001-6004, firebase-sa + hyphenated inter-service host env vars) and 2 AMQP worker Deployments (no Service — intentional) consuming from RabbitMQ queues**

## Performance

- **Duration:** ~3 min
- **Started:** 2026-03-15T06:16:29Z
- **Completed:** 2026-03-15T06:18:49Z
- **Tasks:** 2
- **Files modified:** 15

## Accomplishments

- Created 12 manifests for 4 composite services (book-car/cancel-booking/report-issue/resolve-issue) — each with Deployment (firebase-sa volume mount, imagePullPolicy: Never, liveness/readiness probes), ClusterIP Service, and ConfigMap with hyphenated K8s DNS names overriding app.py Docker Compose underscore defaults
- composite-report-issue Deployment references common-config for RABBITMQ_HOST and RABBITMQ_PORT (2 cross-ConfigMap refs)
- composite-resolve-issue Deployment references common-config for TWILIO_WRAPPER_HOST (1 cross-ConfigMap ref)
- Created 3 manifests for 2 AMQP workers: twilio-worker (Deployment only — 4 Twilio secretKeyRef entries + 3 common-config entries), activity-log (ConfigMap + Deployment — firebase-sa volume, 3 common-config entries + activity-log-config FIREBASE_PROJECT_ID)
- No Service manifests for either worker — pure AMQP consumers with no inbound HTTP by design
- All 15 files validated as valid YAML via python3 yaml.safe_load; structural assertions confirmed all must-have truths

## Task Commits

Each task was committed atomically:

1. **Task 1: composite-book-car, composite-cancel-booking, composite-report-issue, composite-resolve-issue manifests** - `ddf922f` (feat)
2. **Task 2: twilio-worker and activity-log Deployment manifests** - `f87136e` (feat)

## Files Created/Modified

- `k8s/composite-book-car/configmap.yaml` — ConfigMap: FIREBASE_PROJECT_ID=esd-rental-car, PORT=6001, DRIVER_SERVICE_HOST=driver-service:5003, VEHICLE_SERVICE_HOST=vehicle-service:5001, PRICING_SERVICE_HOST=pricing-service:5005, BOOKING_SERVICE_HOST=booking-service:5002, STRIPE_WRAPPER_HOST=stripe-wrapper:6202
- `k8s/composite-book-car/deployment.yaml` — Deployment: esd-composite-book-car:latest, firebase-sa volume, 7 env vars from configmap, /health probes at port 6001
- `k8s/composite-book-car/service.yaml` — ClusterIP Service port 6001
- `k8s/composite-cancel-booking/configmap.yaml` — ConfigMap: FIREBASE_PROJECT_ID, PORT=6002, BOOKING/VEHICLE/PRICING/STRIPE hosts (hyphenated)
- `k8s/composite-cancel-booking/deployment.yaml` — Deployment: esd-composite-cancel-booking:latest, firebase-sa volume, 6 env vars, /health probes at port 6002
- `k8s/composite-cancel-booking/service.yaml` — ClusterIP Service port 6002
- `k8s/composite-report-issue/configmap.yaml` — ConfigMap: FIREBASE_PROJECT_ID, PORT=6003, BOOKING/REPORT/MAPS/OPENAI hosts (hyphenated); RABBITMQ vars in Deployment only (from common-config)
- `k8s/composite-report-issue/deployment.yaml` — Deployment: esd-composite-report-issue:latest, firebase-sa volume, 4 service hosts from own ConfigMap + RABBITMQ_HOST/PORT from common-config, /health probes at port 6003
- `k8s/composite-report-issue/service.yaml` — ClusterIP Service port 6003
- `k8s/composite-resolve-issue/configmap.yaml` — ConfigMap: FIREBASE_PROJECT_ID, PORT=6004, REPORT_SERVICE_HOST=report-service:5004; TWILIO_WRAPPER_HOST in Deployment only (from common-config)
- `k8s/composite-resolve-issue/deployment.yaml` — Deployment: esd-composite-resolve-issue:latest, firebase-sa volume, REPORT_SERVICE_HOST from own ConfigMap + TWILIO_WRAPPER_HOST from common-config, /health probes at port 6004
- `k8s/composite-resolve-issue/service.yaml` — ClusterIP Service port 6004
- `k8s/twilio-worker/deployment.yaml` — Deployment: esd-twilio-worker:latest, imagePullPolicy: Never, RABBITMQ_HOST/PORT/WEBSOCKET_SERVER_URL from common-config, TWILIO_ACCOUNT_SID/AUTH_TOKEN/FROM_NUMBER/SERVICE_TEAM_NUMBER from api-keys Secret; no ports, no probes, no volumes
- `k8s/activity-log/configmap.yaml` — ConfigMap: FIREBASE_PROJECT_ID=esd-rental-car
- `k8s/activity-log/deployment.yaml` — Deployment: esd-activity-log:latest, imagePullPolicy: Never, RABBITMQ_HOST/PORT/WEBSOCKET_SERVER_URL from common-config + FIREBASE_PROJECT_ID from activity-log-config, firebase-sa volume at /secrets; no ports, no probes

## Decisions Made

- Hyphenated K8s DNS names in all composite ConfigMaps: `vehicle-service:5001` (not `vehicle_service:5001`) because app.py defaults use Docker Compose underscore names that fail K8s DNS resolution with NXDOMAIN
- RABBITMQ_HOST/PORT sourced from common-config in composite-report-issue Deployment (not duplicated in composite-report-issue-config) — avoids configuration drift; same pattern as workers
- TWILIO_WRAPPER_HOST sourced from common-config in composite-resolve-issue Deployment — consistent with twilio-worker reading from common-config
- Workers intentionally omit K8s Service: no inbound HTTP traffic; CrashLoopBackOff is expected and acceptable until RabbitMQ becomes available; pika retry loop recovers automatically
- python3 yaml.safe_load used for YAML validation (established project fallback since kubectl --dry-run=client requires live API server)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

- kubectl --dry-run=client unavailable (no live cluster). Resolved by using python3 yaml.safe_load per established STATE.md decision: "K8s YAML validated via python3 yaml.safe_load when no cluster is available".

## Self-Check

---
## Self-Check: PASSED

Files verified to exist:
- k8s/composite-book-car/configmap.yaml: FOUND
- k8s/composite-book-car/deployment.yaml: FOUND
- k8s/composite-book-car/service.yaml: FOUND
- k8s/composite-cancel-booking/configmap.yaml: FOUND
- k8s/composite-cancel-booking/deployment.yaml: FOUND
- k8s/composite-cancel-booking/service.yaml: FOUND
- k8s/composite-report-issue/configmap.yaml: FOUND
- k8s/composite-report-issue/deployment.yaml: FOUND
- k8s/composite-report-issue/service.yaml: FOUND
- k8s/composite-resolve-issue/configmap.yaml: FOUND
- k8s/composite-resolve-issue/deployment.yaml: FOUND
- k8s/composite-resolve-issue/service.yaml: FOUND
- k8s/twilio-worker/deployment.yaml: FOUND
- k8s/activity-log/configmap.yaml: FOUND
- k8s/activity-log/deployment.yaml: FOUND

Commits verified:
- ddf922f: FOUND (feat(06-05): composite service K8s manifests)
- f87136e: FOUND (feat(06-05): AMQP worker K8s manifests)

## User Setup Required

None - manifest files only. To deploy to cluster:
```bash
kubectl apply -f k8s/composite-book-car/
kubectl apply -f k8s/composite-cancel-booking/
kubectl apply -f k8s/composite-report-issue/
kubectl apply -f k8s/composite-resolve-issue/
kubectl apply -f k8s/twilio-worker/
kubectl apply -f k8s/activity-log/
```
Secrets `firebase-sa` and `api-keys` must already exist (created in Plan 06-01).

## Next Phase Readiness

- All 4 composite service Deployment + Service + ConfigMap manifests ready for deployment
- Both worker Deployments ready; will CrashLoopBackOff until RabbitMQ is up (expected behavior, pika retry self-heals)
- Plan 06-06 (frontend/ingress) can proceed — all backend K8s manifests are now complete

---
*Phase: 06-kubernetes*
*Completed: 2026-03-15*
