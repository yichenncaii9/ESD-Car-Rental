---
phase: 06-kubernetes
plan: "06"
subsystem: infra
tags: [kubernetes, k8s, frontend, nodeport, deployment, service, smoke-test, kong, jwt, public-key]

# Dependency graph
requires:
  - phase: 06-05
    provides: Composite services and AMQP workers K8s manifests

provides:
  - k8s/frontend/deployment.yaml — Deployment: esd-frontend:latest, imagePullPolicy: Never, port 8080, liveness/readiness probes, no runtime env vars
  - k8s/frontend/service.yaml — NodePort Service exposing frontend at nodePort 30080
  - kong.yml (root) — Kong declarative config with correct RS256 public key (BEGIN PUBLIC KEY)
  - k8s/kong/kong.yml — K8s Kong declarative config reference with correct RS256 public key
  - k8s/kong/configmap.yaml — K8s ConfigMap with correct RS256 public key loaded by Kong pod

affects:
  - Full cluster: 30/30 smoke tests passing after three root causes fixed during deployment

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Frontend NodePort pattern: Deployment with imagePullPolicy: Never + no env vars (VITE_* baked at build time by scripts/build-images.sh) + NodePort 30080 for Docker Desktop host access"
    - "Kong RS256 JWT: requires PKCS#8 public key (BEGIN PUBLIC KEY) not x509 certificate (BEGIN CERTIFICATE) — extract via: openssl x509 -pubkey -noout -in cert.pem"
    - "k8s/kong/kong.yml is Kong declarative config (not a K8s manifest) — apply via configmap only, never via kubectl apply directly"

key-files:
  created:
    - k8s/frontend/deployment.yaml
    - k8s/frontend/service.yaml
  modified:
    - kong.yml
    - k8s/kong/kong.yml
    - k8s/kong/configmap.yaml

key-decisions:
  - "No env vars in frontend Deployment — VITE_* variables are baked into the image at build time by scripts/build-images.sh; adding runtime env vars would have no effect and is explicitly wrong"
  - "NodePort 30080 used instead of ClusterIP — frontend is the public-facing Vue.js app accessed from Docker Desktop host browser at localhost:30080"
  - "Kong JWT plugin requires BEGIN PUBLIC KEY not BEGIN CERTIFICATE — extract RSA public key from x509 cert via openssl x509 -pubkey -noout; configmap.yaml and k8s/kong/kong.yml updated"
  - "k8s/kong/kong.yml must NOT be applied with kubectl apply — it is Kong's declarative config loaded via configmap, not a K8s manifest; kubectl apply rejects it as invalid"
  - "esd-* Docker images must be built locally before kubectl apply — scripts/build-images.sh must run first; images use imagePullPolicy: Never so K8s will not pull from registry"

requirements-completed: [K8S-01, K8S-06, K8S-07]

# Metrics
duration: ~30min (including user-run deployment + fixes)
completed: 2026-03-15
---

# Phase 6 Plan 06: Frontend K8s Manifests + Final Smoke Test Summary

**Frontend Deployment (esd-frontend:latest, imagePullPolicy: Never, port 8080, no env vars) and NodePort Service (nodePort 30080) — final piece of the 18-service Kubernetes cluster. 30/30 smoke tests passing after three root causes fixed during deployment.**

## Performance

- **Duration:** ~30 min (manifests ~1 min automated + user deployment + three root-cause fixes)
- **Started:** 2026-03-15T06:21:13Z
- **Completed:** 2026-03-15
- **Tasks:** 3 tasks complete (1 auto, 1 human-run, 1 human-verify APPROVED)
- **Files modified:** 5

## Accomplishments

- Created `k8s/frontend/deployment.yaml`: esd-frontend:latest, imagePullPolicy: Never, containerPort 8080, liveness and readiness probes (httpGet /, initialDelaySeconds 15, periodSeconds 20, failureThreshold 5), NO runtime env vars (VITE_* baked at build time)
- Created `k8s/frontend/service.yaml`: NodePort Service, port 8080, targetPort 8080, nodePort 30080 — exposes Vue.js app to Docker Desktop host at localhost:30080
- User ran full kubectl apply sequence and smoke test — 30/30 checks passing
- Kong CrashLoopBackOff fixed: replaced BEGIN CERTIFICATE with BEGIN PUBLIC KEY in all three Kong config files (root kong.yml, k8s/kong/kong.yml, k8s/kong/configmap.yaml)
- Frontend accessible at http://localhost:30080
- docker-compose.yml valid (K8S-06 preserved)

## Task Commits

Each task was committed atomically:

1. **Task 1: Frontend Deployment + Service manifests** - `dc2a9db` (feat)
2. **Task 2: Apply manifests + smoke test** - run manually by user (no automated commit)
3. **Task 3: Human verify** - APPROVED (30/30 passing)
4. **Root cause fixes: Kong public key format** - `e060247` (fix)

## Files Created/Modified

- `k8s/frontend/deployment.yaml` — Deployment: esd-frontend:latest, imagePullPolicy: Never, port 8080, liveness/readiness probes at path /, no env section
- `k8s/frontend/service.yaml` — NodePort Service: port 8080, targetPort 8080, nodePort 30080
- `kong.yml` (root) — RSA public key updated from BEGIN CERTIFICATE to BEGIN PUBLIC KEY
- `k8s/kong/kong.yml` — RSA public key updated (K8s declarative config reference copy)
- `k8s/kong/configmap.yaml` — RSA public key updated (this is what Kong pod actually loads in K8s)

## Decisions Made

- No env vars in frontend Deployment: VITE_* variables are baked into the image at build time by `scripts/build-images.sh` — adding them at runtime has no effect (Vite static bundle)
- NodePort chosen over ClusterIP: frontend is the only service needing direct host access from Docker Desktop browser
- Kong RS256 JWT requires PKCS#8 public key, not x509 certificate: `openssl x509 -pubkey -noout` extracts the correct format from the Firebase-issued certificate

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Kong JWT public key format: CERTIFICATE replaced with PUBLIC KEY**
- **Found during:** Task 2 (user deployment) — Kong pod entered CrashLoopBackOff
- **Root cause:** Kong JWT plugin requires a PKCS#8 public key (-----BEGIN PUBLIC KEY-----). The config contained an x509 certificate (-----BEGIN CERTIFICATE-----) which Kong rejects at startup.
- **Fix:** Extracted RSA public key via `openssl x509 -pubkey -noout` from the Firebase certificate. Updated all three locations: `kong.yml` (root, Docker Compose), `k8s/kong/kong.yml` (K8s reference), `k8s/kong/configmap.yaml` (what K8s actually mounts into the Kong pod).
- **Files modified:** `kong.yml`, `k8s/kong/kong.yml`, `k8s/kong/configmap.yaml`
- **Commit:** `e060247`

### Environment Gates (Expected)

**Task 2 — Live cluster required:** Task 2 (apply manifests and run smoke test) requires a live Kubernetes cluster. No cluster was available during automated execution. The user ran the full apply sequence manually.

**Task 2 — esd-* images needed:** User ran `scripts/build-images.sh` first to build all `esd-*` Docker images with `imagePullPolicy: Never`. This is documented in the plan but was an explicit prerequisite step.

**Task 2 — kong.yml not a K8s manifest:** `k8s/kong/kong.yml` is Kong's declarative config file, not a Kubernetes manifest. `kubectl apply` rejects it. The user applied all other directories and skipped this file, which is correct — it gets loaded via `k8s/kong/configmap.yaml`.

## Smoke Test Results

User verified: **30/30 checks PASS**

- All 18+ pod_check assertions: PASS
- Kong admin and routing checks: PASS
- K8S-04 (firebase-sa secret): PASS
- K8S-05 (ConfigMaps): PASS
- K8S-06 (docker-compose.yml valid): PASS
- Frontend at http://localhost:30080: accessible

## Self-Check

---
## Self-Check: PASSED

Files verified to exist:
- k8s/frontend/deployment.yaml: FOUND
- k8s/frontend/service.yaml: FOUND
- k8s/kong/configmap.yaml: FOUND (updated with BEGIN PUBLIC KEY)
- k8s/kong/kong.yml: FOUND (updated with BEGIN PUBLIC KEY)
- kong.yml: FOUND (updated with BEGIN PUBLIC KEY)

Commits verified:
- dc2a9db: FOUND (feat(06-06): frontend Kubernetes Deployment and Service manifests)
- e060247: FOUND (fix(06-06): Kong JWT public key format — CERTIFICATE -> PUBLIC KEY)

## Phase 6 Complete

All 6 plans of Phase 6 (Kubernetes) are complete. The full 18-service car rental platform runs on Kubernetes (Docker Desktop):

- **Phase 6-01:** Core infrastructure (RabbitMQ, Kong, shared ConfigMap, setup scripts)
- **Phase 6-02:** Atomic services (vehicle, booking, driver, report, pricing)
- **Phase 6-03:** Additional atomic services + verify script
- **Phase 6-04:** Wrappers + websocket-server K8s manifests
- **Phase 6-05:** Composite services + AMQP workers K8s manifests
- **Phase 6-06:** Frontend manifests + full cluster smoke test (30/30 PASS)

---
*Phase: 06-kubernetes*
*Completed: 2026-03-15*
