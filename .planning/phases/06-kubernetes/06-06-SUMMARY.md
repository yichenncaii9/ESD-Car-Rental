---
phase: 06-kubernetes
plan: "06"
subsystem: infra
tags: [kubernetes, k8s, frontend, nodport, deployment, service, smoke-test]

# Dependency graph
requires:
  - phase: 06-05
    provides: Composite services and AMQP workers K8s manifests

provides:
  - k8s/frontend/deployment.yaml — Deployment: esd-frontend:latest, imagePullPolicy: Never, port 8080, liveness/readiness probes, no runtime env vars
  - k8s/frontend/service.yaml — NodePort Service exposing frontend at nodePort 30080

affects:
  - Full cluster readiness: frontend is the final piece; all 18 pod_check assertions in verify_phase6.sh now have their corresponding Deployment/Service

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Frontend NodePort pattern: Deployment with imagePullPolicy: Never + no env vars (VITE_* baked at build time by scripts/build-images.sh) + NodePort 30080 for Docker Desktop host access"

key-files:
  created:
    - k8s/frontend/deployment.yaml
    - k8s/frontend/service.yaml
  modified: []

key-decisions:
  - "No env vars in frontend Deployment — VITE_* variables are baked into the image at build time by scripts/build-images.sh; adding runtime env vars would have no effect and is explicitly wrong"
  - "NodePort 30080 used instead of ClusterIP — frontend is the public-facing Vue.js app accessed from Docker Desktop host browser at localhost:30080"
  - "python3 yaml.safe_load used for YAML validation (no live cluster) — established project fallback per STATE.md decisions"

requirements-completed: [K8S-01, K8S-06, K8S-07]

# Metrics
duration: ~1min
completed: 2026-03-15
---

# Phase 6 Plan 06: Frontend K8s Manifests + Final Smoke Test Summary

**Frontend Deployment (esd-frontend:latest, imagePullPolicy: Never, port 8080, no env vars) and NodePort Service (nodePort 30080) — final piece of the 18-service Kubernetes cluster**

## Performance

- **Duration:** ~1 min
- **Started:** 2026-03-15T06:21:13Z
- **Completed:** 2026-03-15T06:21:44Z
- **Tasks:** 1 completed (auto) / 1 requires cluster (auto) / 1 checkpoint (human-verify)
- **Files modified:** 2

## Accomplishments

- Created `k8s/frontend/deployment.yaml`: esd-frontend:latest, imagePullPolicy: Never, containerPort 8080, liveness and readiness probes (httpGet /, initialDelaySeconds 15, periodSeconds 20, failureThreshold 5), NO runtime env vars (VITE_* baked at build time)
- Created `k8s/frontend/service.yaml`: NodePort Service, port 8080, targetPort 8080, nodePort 30080 — exposes Vue.js app to Docker Desktop host at localhost:30080
- Both files validated as correct YAML via python3 yaml.safe_load with structural assertions

## Task Commits

Each task was committed atomically:

1. **Task 1: Frontend Deployment + Service manifests** - `dc2a9db` (feat)

## Files Created/Modified

- `k8s/frontend/deployment.yaml` — Deployment: esd-frontend:latest, imagePullPolicy: Never, port 8080, liveness/readiness probes at path /, no env section
- `k8s/frontend/service.yaml` — NodePort Service: port 8080, targetPort 8080, nodePort 30080

## Decisions Made

- No env vars in frontend Deployment: VITE_* variables are baked into the image at build time by `scripts/build-images.sh` — adding them at runtime has no effect (Vite static bundle)
- NodePort chosen over ClusterIP: frontend is the only service needing direct host access from Docker Desktop browser
- python3 yaml.safe_load for YAML validation (established project fallback — kubectl --dry-run=client requires live API server)

## Deviations from Plan

### Auth Gate / Environment Requirement

**Task 2 (Apply all manifests and run smoke test):** Requires a live Kubernetes cluster (Docker Desktop with Kubernetes enabled). No cluster was available during automated execution — connection refused on localhost:8080. This is the same environment constraint encountered and documented throughout Phase 6. Task 2 commands must be run manually by the user once Docker Desktop Kubernetes is active.

**Commands to run (Task 2 sequence):**

```bash
# From project root: /Applications/MAMP/htdocs/y2s2/ESD/ESDProj

# 0. Create Secrets FIRST
bash scripts/setup-secrets.sh

# 1. Shared ConfigMap
kubectl apply -f k8s/shared/

# 2. Infrastructure
kubectl apply -f k8s/rabbitmq/
kubectl apply -f k8s/kong/

# 3. Atomic services
kubectl apply -f k8s/vehicle-service/
kubectl apply -f k8s/booking-service/
kubectl apply -f k8s/driver-service/
kubectl apply -f k8s/report-service/
kubectl apply -f k8s/pricing-service/

# 4. Wrappers + websocket-server
kubectl apply -f k8s/openai-wrapper/
kubectl apply -f k8s/googlemaps-wrapper/
kubectl apply -f k8s/stripe-wrapper/
kubectl apply -f k8s/twilio-wrapper-http/
kubectl apply -f k8s/websocket-server/

# 5. Composite services
kubectl apply -f k8s/composite-book-car/
kubectl apply -f k8s/composite-cancel-booking/
kubectl apply -f k8s/composite-report-issue/
kubectl apply -f k8s/composite-resolve-issue/

# 6. Workers
kubectl apply -f k8s/twilio-worker/
kubectl apply -f k8s/activity-log/

# 7. Frontend
kubectl apply -f k8s/frontend/

# 8. Wait ~90s for pods to initialize
kubectl get pods --watch

# 9. Port-forward Kong in a separate terminal
kubectl port-forward svc/kong 8000:8000 8001:8001

# 10. Run smoke test
bash scripts/verify_phase6.sh
```

## Issues Encountered

- kubectl cluster not available during automated execution (Docker Desktop Kubernetes not running). Resolved by committing manifests and documenting manual apply sequence for user.

## Self-Check

---
## Self-Check: PASSED

Files verified to exist:
- k8s/frontend/deployment.yaml: FOUND
- k8s/frontend/service.yaml: FOUND

Commits verified:
- dc2a9db: FOUND (feat(06-06): frontend Kubernetes Deployment and Service manifests)

## User Setup Required

**Docker Desktop Kubernetes must be running before executing the apply sequence.**

1. Enable Kubernetes in Docker Desktop → Settings → Kubernetes → Enable Kubernetes → Apply & Restart
2. Wait until Docker Desktop shows "Kubernetes running" (green dot)
3. Run `kubectl cluster-info` to verify cluster is accessible
4. Run the Task 2 command sequence above
5. In a separate terminal: `kubectl port-forward svc/kong 8000:8000 8001:8001`
6. Run `bash scripts/verify_phase6.sh` — expect all 18 pod_check assertions to PASS
7. Open browser at http://localhost:30080 to confirm frontend is accessible
8. Run `docker compose config` to confirm K8S-06 (docker-compose.yml still valid)

## Next Phase Readiness

- All K8s manifests for all 18 services are now created and committed
- Phase 6 (Kubernetes) is complete from a manifest perspective
- Final verification requires user to run the cluster with Docker Desktop Kubernetes

---
*Phase: 06-kubernetes*
*Completed: 2026-03-15*
