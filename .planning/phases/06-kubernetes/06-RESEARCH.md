# Phase 6: Kubernetes - Research

**Researched:** 2026-03-15
**Domain:** Kubernetes manifests for a 18-service microservices stack on Docker Desktop
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **Target cluster:** Docker Desktop Kubernetes — local single-node cluster, shares the local Docker daemon
- All 18 services deployed (full stack, not demo-minimum) — satisfies K8S-01
- **default namespace** — no custom namespace needed; zero extra config
- **verify_phase6.sh** smoke test script included — consistent with verify_phase3.sh/verify_phase5.sh; validates all pods Running, Kong routing live, and end-to-end scenarios pass
- **Kong:** runs as a standalone Deployment + Service (NOT Kong Ingress Controller)
- Direct translation of Docker Compose Kong: same DB-less `kong.yml`, same ports, same plugins
- `kong.yml` mounted as a ConfigMap — structure, routes, and plugins unchanged
- **One required change:** upstream hostnames updated from underscore to hyphen (K8s DNS cannot use underscores)
  - `composite_book_car:6001` → `composite-book-car:6001`
  - `composite_cancel_booking:6002` → `composite-cancel-booking:6002`
  - etc. — find-and-replace only, not a rewrite
- Kong exposed via **NodePort on port 8000** — accessible at `localhost:8000` on Docker Desktop
- **imagePullPolicy: Never** on all Deployments — K8s uses locally-built images from Docker daemon, no registry needed
- Image naming convention: `esd-<service-name>:latest`
  - e.g. `esd-vehicle-service:latest`, `esd-composite-book-car:latest`, `esd-rabbitmq:latest`
  - Hyphenated names, `esd-` prefix to avoid collisions with pulled images
- **`scripts/build-images.sh`** — shell script that builds all 18 images in one command with correct tags
- **`scripts/setup-secrets.sh`** — sources `.env` automatically (`set -a; source .env; set +a`), then runs `kubectl create secret` commands for all sensitive values
- **Secrets (sensitive values):** `STRIPE_SECRET_KEY`, `OPENAI_API_KEY`, `GOOGLE_MAPS_API_KEY`, `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_FROM_NUMBER`, `TWILIO_SERVICE_TEAM_NUMBER`
- **firebase-service-account.json** stored as a separate K8s Secret (`kubectl create secret generic firebase-sa --from-file=firebase-service-account.json`), mounted read-only at `/secrets/firebase-service-account.json`
- **ConfigMaps (non-sensitive values):** `FIREBASE_PROJECT_ID`, `RABBITMQ_HOST`, `RABBITMQ_PORT`, `WEBSOCKET_SERVER_URL`, `TWILIO_WRAPPER_HOST`, `PORT` per service — declared as YAML ConfigMaps in `k8s/`
- **Frontend VITE_* vars** baked into the image at build time — `scripts/build-images.sh` passes them as `--build-arg` from `.env`
- No Secret YAML files committed to git; setup script is the single source of truth

### Claude's Discretion
- Exact replica count per Deployment (1 is appropriate for a university demo)
- RabbitMQ StatefulSet PVC size and storage class
- Liveness/readiness probe paths and intervals (can mirror existing Docker healthchecks: `/health` endpoints)
- Inter-service DNS resolution pattern in manifests (use K8s Service names as hostnames in env vars)
- Whether to split ConfigMaps per service or use shared ConfigMaps for common values (RABBITMQ_HOST etc.)

### Deferred Ideas (OUT OF SCOPE)
- None — discussion stayed within Phase 6 scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| K8S-01 | Every service has a Kubernetes Deployment + Service + ConfigMap manifest (k8s/ directory) | Deployment/Service/ConfigMap YAML patterns documented below |
| K8S-02 | RabbitMQ runs as a Kubernetes StatefulSet with persistent volume | StatefulSet + PVC pattern documented; `rabbitmq:3-management` image used |
| K8S-03 | Kong runs as a standalone Kubernetes pod or Ingress controller, routing all /api/* paths | Deployment + NodePort Service + ConfigMap pattern; same kong.yml with hostname fix |
| K8S-04 | firebase-service-account.json stored as a Kubernetes Secret, mounted read-only into all Firestore-connected pods | `kubectl create secret generic firebase-sa --from-file` + volumeMount pattern |
| K8S-05 | All .env values migrated to Kubernetes ConfigMaps (non-sensitive) and Secrets (API keys) | Full inventory of env vars by service documented; ConfigMap/Secret split defined |
| K8S-06 | docker-compose.yml is preserved and functional for local development | No changes to docker-compose.yml; k8s/ is an additive directory |
| K8S-07 | All three scenarios (book-car, cancel-booking, report-issue) work end-to-end in the Kubernetes cluster | verify_phase6.sh smoke test design documented |
</phase_requirements>

---

## Summary

Phase 6 converts the existing 18-service Docker Compose stack to Kubernetes declarative manifests targeting Docker Desktop's local cluster. Every service already has a Dockerfile and known env vars — the work is translation, not re-architecture. The Docker Compose service names use underscores; Kubernetes DNS requires hyphens, so the primary cross-cutting change is a systematic underscore-to-hyphen rename in Kong upstream URLs and all inter-service env vars (e.g. `RABBITMQ_HOST`, `WEBSOCKET_SERVER_URL`, `TWILIO_WRAPPER_HOST`).

The stack splits into three manifest categories: (1) standard Deployments + ClusterIP Services for most services, (2) a StatefulSet + PVC for RabbitMQ, and (3) a NodePort Service for Kong's proxy port (8000) and admin port (8001) so the host can reach the cluster. Secrets and firebase-service-account.json are injected imperatively via `scripts/setup-secrets.sh` so no credential YAML is committed to git. VITE_* frontend vars are baked at image build time using `--build-arg`, exactly as Docker Compose does.

**Primary recommendation:** Work wave by wave — Wave 0: k8s/ directory scaffold + scripts + Kong ConfigMap; Wave 1: atomic services manifests; Wave 2: composite + wrapper + websocket manifests; Wave 3: workers; Wave 4: frontend; Wave 5: verify_phase6.sh smoke test.

---

## Service Inventory

Complete list of all 18 services derived from docker-compose.yml, with their K8s resource requirements:

| Service (Docker Compose) | K8s Name (hyphenated) | Image Tag | Port | Has Firebase | Has Ports | Resource Type |
|---|---|---|---|---|---|---|
| rabbitmq | rabbitmq | esd-rabbitmq:latest | 5672, 15672 | No | Yes | StatefulSet |
| kong | kong | kong:3.0-alpine (official) | 8000, 8001 | No | Yes (NodePort) | Deployment |
| vehicle_service | vehicle-service | esd-vehicle-service:latest | 5001 | Yes | Yes | Deployment |
| booking_service | booking-service | esd-booking-service:latest | 5002 | Yes | Yes | Deployment |
| driver_service | driver-service | esd-driver-service:latest | 5003 | Yes | Yes | Deployment |
| report_service | report-service | esd-report-service:latest | 5004 | Yes | Yes | Deployment |
| pricing_service | pricing-service | esd-pricing-service:latest | 5005 | No | Yes | Deployment |
| composite_book_car | composite-book-car | esd-composite-book-car:latest | 6001 | Yes | Yes | Deployment |
| composite_cancel_booking | composite-cancel-booking | esd-composite-cancel-booking:latest | 6002 | Yes | Yes | Deployment |
| composite_report_issue | composite-report-issue | esd-composite-report-issue:latest | 6003 | Yes | Yes | Deployment |
| composite_resolve_issue | composite-resolve-issue | esd-composite-resolve-issue:latest | 6004 | Yes | Yes | Deployment |
| openai_wrapper | openai-wrapper | esd-openai-wrapper:latest | 6200 | No | Yes | Deployment |
| googlemaps_wrapper | googlemaps-wrapper | esd-googlemaps-wrapper:latest | 6201 | No | Yes | Deployment |
| stripe_wrapper | stripe-wrapper | esd-stripe-wrapper:latest | 6202 | No | Yes | Deployment |
| twilio_wrapper_http | twilio-wrapper-http | esd-twilio-wrapper-http:latest | 6203 | No | Yes | Deployment |
| websocket_server | websocket-server | esd-websocket-server:latest | 6100 | No | Yes | Deployment |
| twilio_wrapper (worker) | twilio-worker | esd-twilio-worker:latest | None | No | No (ClusterIP headless) | Deployment |
| activity_log (worker) | activity-log | esd-activity-log:latest | None | Yes | No (ClusterIP headless) | Deployment |
| frontend | frontend | esd-frontend:latest | 8080 | No | Yes | Deployment |

**Note:** Kong uses the official `kong:3.0-alpine` image pulled from Docker Hub — `imagePullPolicy: IfNotPresent` for Kong (it is not a locally-built image). All `esd-*` images use `imagePullPolicy: Never`.

---

## Standard Stack

### Core (K8s resources)
| Resource | Purpose | Notes |
|----------|---------|-------|
| Deployment | Stateless services | All services except RabbitMQ |
| StatefulSet | Stateful services | RabbitMQ only — needs stable identity and PVC |
| Service (ClusterIP) | Internal pod-to-pod DNS | Default for all services; workers with no port get headless or omit |
| Service (NodePort) | Expose Kong to host | Kong proxy port 8000 → NodePort 30000 (or 8000 if available) |
| ConfigMap | Non-sensitive env vars | FIREBASE_PROJECT_ID, RABBITMQ_HOST, port numbers, etc. |
| Secret | Sensitive credentials + firebase-sa.json | Created imperatively via setup-secrets.sh, never in YAML |
| PersistentVolumeClaim | RabbitMQ data persistence | Bound to StatefulSet |

### Supporting Scripts
| Script | Purpose |
|--------|---------|
| `scripts/build-images.sh` | Builds all 18 `esd-*` images from local Dockerfiles |
| `scripts/setup-secrets.sh` | Creates K8s Secrets from `.env` and `firebase-service-account.json` |
| `scripts/verify_phase6.sh` | Smoke test: pod status + Kong routing + 3 end-to-end scenarios |

### Key Kubernetes DNS Rule
In K8s, a Service named `vehicle-service` in the `default` namespace is reachable at `vehicle-service` (short name) or `vehicle-service.default.svc.cluster.local` (FQDN). Pods within the same namespace can use the short name. Docker Compose used underscored names (`vehicle_service`) — these must become hyphenated (`vehicle-service`) in all K8s env vars and ConfigMaps.

---

## Architecture Patterns

### Recommended k8s/ Directory Structure
```
k8s/
├── rabbitmq/
│   ├── statefulset.yaml
│   ├── service.yaml
│   └── pvc.yaml            # Optional: StatefulSet can define volumeClaimTemplates inline
├── kong/
│   ├── deployment.yaml
│   ├── service.yaml        # NodePort for ports 8000 and 8001
│   └── configmap.yaml      # kong-config ConfigMap with kong.yml content
├── vehicle-service/
│   ├── deployment.yaml
│   ├── service.yaml
│   └── configmap.yaml
├── booking-service/
│   ├── ...
├── [one subdirectory per service]
└── shared/
    └── common-configmap.yaml   # RABBITMQ_HOST, RABBITMQ_PORT, WEBSOCKET_SERVER_URL
```

### Pattern 1: Standard Deployment + ClusterIP Service

```yaml
# k8s/vehicle-service/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: vehicle-service
  namespace: default
spec:
  replicas: 1
  selector:
    matchLabels:
      app: vehicle-service
  template:
    metadata:
      labels:
        app: vehicle-service
    spec:
      containers:
        - name: vehicle-service
          image: esd-vehicle-service:latest
          imagePullPolicy: Never
          ports:
            - containerPort: 5001
          env:
            - name: FIREBASE_PROJECT_ID
              valueFrom:
                configMapKeyRef:
                  name: vehicle-service-config
                  key: FIREBASE_PROJECT_ID
            - name: GOOGLE_APPLICATION_CREDENTIALS
              value: /secrets/firebase-service-account.json
          volumeMounts:
            - name: firebase-sa
              mountPath: /secrets
              readOnly: true
          livenessProbe:
            httpGet:
              path: /health
              port: 5001
            initialDelaySeconds: 20
            periodSeconds: 15
          readinessProbe:
            httpGet:
              path: /health
              port: 5001
            initialDelaySeconds: 20
            periodSeconds: 15
      volumes:
        - name: firebase-sa
          secret:
            secretName: firebase-sa
---
# k8s/vehicle-service/service.yaml
apiVersion: v1
kind: Service
metadata:
  name: vehicle-service
  namespace: default
spec:
  selector:
    app: vehicle-service
  ports:
    - port: 5001
      targetPort: 5001
  type: ClusterIP
```

### Pattern 2: RabbitMQ StatefulSet with PVC

```yaml
# k8s/rabbitmq/statefulset.yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: rabbitmq
  namespace: default
spec:
  serviceName: rabbitmq
  replicas: 1
  selector:
    matchLabels:
      app: rabbitmq
  template:
    metadata:
      labels:
        app: rabbitmq
    spec:
      containers:
        - name: rabbitmq
          image: rabbitmq:3-management
          imagePullPolicy: IfNotPresent
          ports:
            - containerPort: 5672
            - containerPort: 15672
          livenessProbe:
            exec:
              command: ["rabbitmq-diagnostics", "check_running"]
            initialDelaySeconds: 30
            periodSeconds: 10
          readinessProbe:
            exec:
              command: ["rabbitmq-diagnostics", "check_running"]
            initialDelaySeconds: 30
            periodSeconds: 10
          volumeMounts:
            - name: rabbitmq-data
              mountPath: /var/lib/rabbitmq
  volumeClaimTemplates:
    - metadata:
        name: rabbitmq-data
      spec:
        accessModes: ["ReadWriteOnce"]
        resources:
          requests:
            storage: 1Gi
---
# k8s/rabbitmq/service.yaml
apiVersion: v1
kind: Service
metadata:
  name: rabbitmq
  namespace: default
spec:
  selector:
    app: rabbitmq
  ports:
    - name: amqp
      port: 5672
      targetPort: 5672
    - name: management
      port: 15672
      targetPort: 15672
  type: ClusterIP
```

### Pattern 3: Kong Deployment with ConfigMap-mounted kong.yml

```yaml
# k8s/kong/configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: kong-config
  namespace: default
data:
  kong.yml: |
    _format_version: "3.0"
    _transform: true
    # ... full content of kong.yml with underscores replaced by hyphens in upstream URLs ...
---
# k8s/kong/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: kong
  namespace: default
spec:
  replicas: 1
  selector:
    matchLabels:
      app: kong
  template:
    metadata:
      labels:
        app: kong
    spec:
      containers:
        - name: kong
          image: kong:3.0-alpine
          imagePullPolicy: IfNotPresent
          env:
            - name: KONG_DATABASE
              value: "off"
            - name: KONG_DECLARATIVE_CONFIG
              value: /usr/local/kong/declarative/kong.yml
            - name: KONG_ADMIN_LISTEN
              value: "0.0.0.0:8001"
            - name: KONG_PROXY_LISTEN
              value: "0.0.0.0:8000"
            - name: KONG_LOG_LEVEL
              value: info
          ports:
            - containerPort: 8000
            - containerPort: 8001
          volumeMounts:
            - name: kong-config
              mountPath: /usr/local/kong/declarative
              readOnly: true
          livenessProbe:
            httpGet:
              path: /
              port: 8001
            initialDelaySeconds: 15
            periodSeconds: 15
      volumes:
        - name: kong-config
          configMap:
            name: kong-config
---
# k8s/kong/service.yaml
apiVersion: v1
kind: Service
metadata:
  name: kong
  namespace: default
spec:
  selector:
    app: kong
  type: NodePort
  ports:
    - name: proxy
      port: 8000
      targetPort: 8000
      nodePort: 30000
    - name: admin
      port: 8001
      targetPort: 8001
      nodePort: 30001
```

**Note on NodePort:** Docker Desktop maps NodePort to `localhost:<nodePort>`. Using nodePort 30000 means Kong is at `localhost:30000`. If the user wants `localhost:8000` to keep parity, they need `nodePort: 8000` — but K8s only allows NodePort in range 30000-32767 by default. The planner must pick: either use `localhost:30000` in verify_phase6.sh, OR run `kubectl port-forward svc/kong 8000:8000` for the duration of testing. The port-forward approach preserves `localhost:8000` without changing the NodePort range.

### Pattern 4: Firebase Secret Mount

```bash
# scripts/setup-secrets.sh (excerpt)
# Create firebase-sa secret from local file
kubectl create secret generic firebase-sa \
  --from-file=firebase-service-account.json=./firebase-service-account.json \
  --dry-run=client -o yaml | kubectl apply -f -
```

Mount in pod spec:
```yaml
volumes:
  - name: firebase-sa
    secret:
      secretName: firebase-sa
      items:
        - key: firebase-service-account.json
          path: firebase-service-account.json
containers:
  - volumeMounts:
      - name: firebase-sa
        mountPath: /secrets
        readOnly: true
    env:
      - name: GOOGLE_APPLICATION_CREDENTIALS
        value: /secrets/firebase-service-account.json
```

The secret file key matches the `--from-file` filename. The `items` block renames it inside the pod if needed — but since `--from-file=firebase-service-account.json` sets the key to `firebase-service-account.json`, mounting to `/secrets` with `readOnly: true` automatically places it at `/secrets/firebase-service-account.json` without the `items` block.

### Pattern 5: Workers (No Ports — AMQP consumers only)

Workers (`twilio-worker`, `activity-log`) have no HTTP ports. They still need a Service for DNS resolution (other pods may reference them) but can omit it if nothing calls them. More importantly: they need `restartPolicy: Always` (default in Deployment) and must wait for RabbitMQ to be ready. Since K8s has no `depends_on`, use the pika retry logic already in the worker code — it reconnects on failure.

For workers, a ClusterIP Service with no ports is valid, or omit the Service entirely. The recommended approach is to omit the Service since nothing calls into them.

### Pattern 6: Shared ConfigMap for Common Values

```yaml
# k8s/shared/common-configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: common-config
  namespace: default
data:
  RABBITMQ_HOST: "rabbitmq"
  RABBITMQ_PORT: "5672"
  WEBSOCKET_SERVER_URL: "http://websocket-server:6100"
  TWILIO_WRAPPER_HOST: "twilio-wrapper-http:6203"
```

Services reference this ConfigMap via `configMapKeyRef` for shared values and their own per-service ConfigMap for service-specific values (FIREBASE_PROJECT_ID, PORT).

### Pattern 7: build-images.sh Script Structure

```bash
#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"

# Load .env for VITE_* build args
set -a; source "$ROOT/.env"; set +a

echo "=== Building all 18 ESD images ==="

# Infrastructure (official images — no build needed, but pull to ensure available)
docker pull rabbitmq:3-management
docker pull kong:3.0-alpine

# Atomic services
docker build -t esd-vehicle-service:latest "$ROOT/atomic/vehicle_service"
docker build -t esd-booking-service:latest "$ROOT/atomic/booking_service"
docker build -t esd-driver-service:latest "$ROOT/atomic/driver_service"
docker build -t esd-report-service:latest "$ROOT/atomic/report_service"
docker build -t esd-pricing-service:latest "$ROOT/atomic/pricing_service"

# Composite services
docker build -t esd-composite-book-car:latest "$ROOT/composite/book_car"
docker build -t esd-composite-cancel-booking:latest "$ROOT/composite/cancel_booking"
docker build -t esd-composite-report-issue:latest "$ROOT/composite/report_issue"
docker build -t esd-composite-resolve-issue:latest "$ROOT/composite/resolve_issue"

# Wrappers
docker build -t esd-openai-wrapper:latest "$ROOT/wrappers/openai_wrapper"
docker build -t esd-googlemaps-wrapper:latest "$ROOT/wrappers/googlemaps_wrapper"
docker build -t esd-stripe-wrapper:latest "$ROOT/wrappers/stripe_wrapper"
docker build -t esd-twilio-wrapper-http:latest "$ROOT/wrappers/twilio_wrapper"

# WebSocket server
docker build -t esd-websocket-server:latest "$ROOT/websocket_server"

# Workers
docker build -t esd-twilio-worker:latest "$ROOT/workers/twilio_wrapper"
docker build -t esd-activity-log:latest "$ROOT/workers/activity_log"

# Frontend (VITE_* baked at build time)
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

echo "=== All images built successfully ==="
```

### Pattern 8: setup-secrets.sh Script Structure

```bash
#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"

# Load .env for all API keys
set -a; source "$ROOT/.env"; set +a

echo "=== Setting up Kubernetes Secrets ==="

# Firebase service account file
kubectl create secret generic firebase-sa \
  --from-file=firebase-service-account.json="$ROOT/firebase-service-account.json" \
  --dry-run=client -o yaml | kubectl apply -f -

# API key secrets
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
```

The `--dry-run=client -o yaml | kubectl apply -f -` pattern is idempotent — safe to re-run.

---

## Environment Variable Inventory

Complete mapping of all .env vars per service:

### Services with Firebase Secret mount
These pods need `firebase-sa` volume mount + `GOOGLE_APPLICATION_CREDENTIALS=/secrets/firebase-service-account.json`:
- vehicle-service, booking-service, driver-service, report-service
- composite-book-car, composite-cancel-booking, composite-report-issue, composite-resolve-issue
- activity-log (worker)

### Services with API Keys (from `api-keys` Secret)
| Service | Secret Keys Needed |
|---------|-------------------|
| openai-wrapper | OPENAI_API_KEY |
| googlemaps-wrapper | GOOGLE_MAPS_API_KEY |
| stripe-wrapper | STRIPE_SECRET_KEY |
| twilio-wrapper-http | TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_FROM_NUMBER |
| twilio-worker | TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_FROM_NUMBER, TWILIO_SERVICE_TEAM_NUMBER |

### Services with ConfigMap (non-sensitive)
| Service | ConfigMap Keys Needed |
|---------|----------------------|
| All Firestore services | FIREBASE_PROJECT_ID |
| composite-report-issue, twilio-worker, activity-log | RABBITMQ_HOST, RABBITMQ_PORT |
| twilio-worker, activity-log | WEBSOCKET_SERVER_URL |
| composite-resolve-issue | TWILIO_WRAPPER_HOST |
| All services | PORT (per-service value) |

### Underscore-to-Hyphen Changes Required in kong.yml
These upstream URL strings must be updated (find-and-replace):
```
composite_book_car      → composite-book-car
composite_cancel_booking → composite-cancel-booking
composite_report_issue  → composite-report-issue
composite_resolve_issue → composite-resolve-issue
vehicle_service         → vehicle-service
booking_service         → booking-service
driver_service          → driver-service
report_service          → report-service
pricing_service         → pricing-service
```

### Underscore-to-Hyphen Changes Required in env vars across manifests
```
RABBITMQ_HOST: rabbitmq          (stays "rabbitmq" — K8s Service name)
WEBSOCKET_SERVER_URL: http://websocket-server:6100  (was websocket_server)
TWILIO_WRAPPER_HOST: twilio-wrapper-http:6203       (was twilio_wrapper_http)
```

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Idempotent secret creation | Custom shell logic | `--dry-run=client -o yaml \| kubectl apply -f -` | Handles create vs. update cleanly |
| RabbitMQ persistence | Manual volume management | StatefulSet `volumeClaimTemplates` | K8s manages PVC lifecycle tied to pod identity |
| Service discovery | Hard-coded IPs | K8s ClusterIP Service + DNS short name | Pod IPs change on restart; Service DNS is stable |
| Worker startup ordering | Polling/sleep loops | Pika retry logic already in worker code | K8s has no `depends_on`; workers must tolerate RabbitMQ startup delay |
| Image registry | Push to DockerHub/ECR | `imagePullPolicy: Never` + local Docker daemon | Docker Desktop shares daemon with K8s; no registry needed |

**Key insight:** Docker Desktop Kubernetes shares the same Docker daemon as the host. Images built with `docker build` are immediately visible to K8s pods with `imagePullPolicy: Never` — no push/pull cycle needed.

---

## Common Pitfalls

### Pitfall 1: Underscore in Service Names / DNS Lookup Failures
**What goes wrong:** Kubernetes Service names cannot contain underscores. Pods referencing `vehicle_service` instead of `vehicle-service` get DNS lookup failures (`Name or service not known`), causing 500 errors in composite services.
**Why it happens:** Docker Compose allows underscore names; K8s DNS (RFC 1123) does not.
**How to avoid:** Systematically rename all services and update ALL references: (1) K8s Service metadata.name, (2) Deployment selector labels, (3) kong.yml upstream URLs, (4) all env vars containing service names (WEBSOCKET_SERVER_URL, TWILIO_WRAPPER_HOST, RABBITMQ_HOST).
**Warning signs:** Pod starts fine but gets connection refused / DNS errors in logs; Kong returns 502.

### Pitfall 2: imagePullPolicy Default Pulls from Registry
**What goes wrong:** K8s defaults `imagePullPolicy: Always` for images tagged `:latest`. It tries to pull `esd-vehicle-service:latest` from Docker Hub and fails (image not pushed).
**Why it happens:** `:latest` tag triggers pull attempt even if image exists locally.
**How to avoid:** Explicitly set `imagePullPolicy: Never` on every Deployment container using `esd-*` images. Kong uses `IfNotPresent` (official image, pulled once).
**Warning signs:** `ErrImageNeverPull` or `ImagePullBackOff` in `kubectl get pods`.

### Pitfall 3: Workers Start Before RabbitMQ is Ready
**What goes wrong:** twilio-worker and activity-log pods start, fail to connect to RabbitMQ, and enter CrashLoopBackOff.
**Why it happens:** K8s has no `depends_on: condition: service_healthy` equivalent. Workers start in parallel with RabbitMQ.
**How to avoid:** The existing pika retry logic in both workers already handles this — they reconnect on failure. Set `restartPolicy: Always` (default in Deployment) and allow the CrashLoop to self-heal once RabbitMQ is ready. Alternatively add an init container that waits for RabbitMQ port. For a university demo, relying on the retry logic is sufficient.
**Warning signs:** Workers in CrashLoopBackOff initially — this is expected and should self-heal within ~60 seconds.

### Pitfall 4: Firebase Secret Volume Mount Path Mismatch
**What goes wrong:** Pod starts but Flask app cannot read Firestore — `google.auth.exceptions.DefaultCredentialsError`.
**Why it happens:** The `GOOGLE_APPLICATION_CREDENTIALS` env var points to `/secrets/firebase-service-account.json` but the volume mount lands the file at a different path.
**How to avoid:** Mount the `firebase-sa` secret volume at `mountPath: /secrets` (not `/secrets/firebase-service-account.json` — that would be wrong; the mount path is the directory). The secret key `firebase-service-account.json` becomes the filename under that directory automatically.
**Warning signs:** Pod Running but Firestore calls return 403 or DefaultCredentialsError in logs.

### Pitfall 5: Kong ConfigMap Volume Replaces Entire Directory
**What goes wrong:** Kong fails to start — missing config files.
**Why it happens:** Mounting a ConfigMap at `/usr/local/kong/declarative/` replaces ALL contents of that directory with only the ConfigMap keys. If Kong expects other files there, they are gone.
**How to avoid:** The DB-less Kong only needs `kong.yml` in the declarative config directory — no other files. The mount is safe. Verify with `KONG_DECLARATIVE_CONFIG=/usr/local/kong/declarative/kong.yml` pointing to the exact filename matching the ConfigMap key.
**Warning signs:** Kong pod CrashLoopBackOff; logs show `declarative config file not found`.

### Pitfall 6: VITE_* Vars Not Available at Runtime
**What goes wrong:** Frontend loads but Firebase Auth fails — API key is undefined.
**Why it happens:** Vite bakes env vars at BUILD time. If the image is built without the correct `--build-arg` values, the JS bundle has empty strings.
**How to avoid:** `scripts/build-images.sh` must source `.env` and pass all `VITE_*` vars as `--build-arg`. Never mount VITE_* as runtime env vars — Vite does not read them at runtime.
**Warning signs:** Frontend console shows `undefined` for Firebase config; auth fails immediately.

### Pitfall 7: NodePort Range vs. Desired Port
**What goes wrong:** User expects Kong at `localhost:8000` but NodePort must be 30000-32767 by default.
**Why it happens:** Kubernetes restricts NodePort range to 30000-32767 unless the API server is reconfigured with `--service-node-port-range`.
**How to avoid:** Use `kubectl port-forward svc/kong 8000:8000` for smoke test access, or document that Kong is at `localhost:30000` in verify_phase6.sh. The port-forward approach is cleaner for a demo — no cluster config changes needed.
**Warning signs:** `kubectl apply` fails with `Invalid value: 8000: provided port is not in the valid range`.

### Pitfall 8: Applying Manifests Before Secrets Exist
**What goes wrong:** Pods reference secrets that don't exist yet → pods stuck in `CreateContainerConfigError`.
**Why it happens:** Manifests reference `firebase-sa` and `api-keys` secrets, but `setup-secrets.sh` hasn't been run.
**How to avoid:** Document the correct apply order in README/verify script: (1) run `setup-secrets.sh`, (2) `kubectl apply -f k8s/shared/`, (3) `kubectl apply -f k8s/rabbitmq/`, (4) `kubectl apply -f k8s/kong/`, (5) `kubectl apply -f k8s/` (remaining services).
**Warning signs:** `kubectl describe pod <name>` shows `secret "firebase-sa" not found`.

---

## verify_phase6.sh Design

Follows the same pattern as verify_phase3.sh and verify_phase5.sh. Key differences from verify_phase5.sh:
- Uses `kubectl` instead of `docker-compose logs`
- Kong accessed via `localhost:8000` (port-forward running) or `localhost:30000` (NodePort)
- Pod health checked via `kubectl get pods --field-selector=status.phase=Running`

```bash
#!/usr/bin/env bash
set -euo pipefail

echo "=== Phase 6 Smoke Tests: Kubernetes ==="

PASS=0
FAIL=0
KONG_BASE="http://localhost:8000"   # Requires: kubectl port-forward svc/kong 8000:8000

check() {
    local label="$1"; shift
    if "$@" > /dev/null 2>&1; then
        echo "PASS  $label"; PASS=$((PASS + 1))
    else
        echo "FAIL  $label"; FAIL=$((FAIL + 1))
    fi
}

pod_check() {
    local label="$1"
    local pod_selector="$2"
    if kubectl get pods -l "app=$pod_selector" --field-selector=status.phase=Running --no-headers 2>/dev/null | grep -q Running; then
        echo "PASS  $label"; PASS=$((PASS + 1))
    else
        echo "FAIL  $label"; FAIL=$((FAIL + 1))
    fi
}

# K8S-01: All pods running
for svc in rabbitmq kong vehicle-service booking-service driver-service \
           report-service pricing-service composite-book-car \
           composite-cancel-booking composite-report-issue \
           composite-resolve-issue openai-wrapper googlemaps-wrapper \
           stripe-wrapper twilio-wrapper-http websocket-server \
           twilio-worker activity-log frontend; do
    pod_check "K8S-01: $svc pod Running" "$svc"
done

# K8S-03: Kong routing live
check "K8S-03: Kong admin API responds" curl -sf "${KONG_BASE%:8000}:8001/"
check "K8S-03: Kong routes /api/vehicles" curl -sf -o /dev/null -w "%{http_code}" "$KONG_BASE/api/vehicles" | grep -qv "502"

# K8S-07: End-to-end scenario validation (requires valid Firebase JWT — smoke only checks routing)
# Full scenario tests require a real JWT; verify Kong returns non-502 for each /api/* path
for path in /api/book-car /api/cancel-booking /api/report-issue; do
    check "K8S-07: Kong routes $path (non-502)" \
        bash -c "code=\$(curl -sf -o /dev/null -w '%{http_code}' -X POST $KONG_BASE$path -H 'Content-Type: application/json' -d '{}' 2>/dev/null || echo 000); [ \"\$code\" != '502' ] && [ \"\$code\" != '000' ]"
done

echo ""
echo "Results: ${PASS} passed, ${FAIL} failed"
[ "$FAIL" -gt 0 ] && exit 1 || exit 0
```

---

## State of the Art

| Old Approach | Current Approach | Impact |
|--------------|------------------|--------|
| `kubectl run` imperative | Declarative YAML manifests | Reproducible, version-controlled |
| Single global ConfigMap | Per-service ConfigMap + shared ConfigMap | Clear ownership; avoids key collision |
| Hardcoded `imagePullPolicy: Always` | `imagePullPolicy: Never` for local images | No registry needed on Docker Desktop |
| Init containers for dependency ordering | App-level retry logic (pika) | Simpler manifests; workers self-heal |

**Deprecated/outdated:**
- `kubectl create -f` (non-idempotent): Use `kubectl apply -f` always
- `apiVersion: extensions/v1beta1` for Deployment: Use `apps/v1` (required since K8s 1.16+); Docker Desktop ships K8s 1.29+ as of 2026

---

## Open Questions

1. **NodePort vs. port-forward for Kong access**
   - What we know: NodePort must be 30000-32767 by default; `localhost:8000` requires port-forward
   - What's unclear: Whether the planner will use port-forward (simpler, temporary) or NodePort 30000 (permanent, needs doc update)
   - Recommendation: Use `kubectl port-forward svc/kong 8000:8000` in verify_phase6.sh preamble; document that user must run it before the smoke test. Avoids cluster config changes.

2. **Shared ConfigMap vs. per-service ConfigMap for RABBITMQ_HOST**
   - What we know: Both approaches work; shared is DRY but creates coupling
   - Recommendation: Use one `common-config` ConfigMap for RABBITMQ_HOST, RABBITMQ_PORT, WEBSOCKET_SERVER_URL, TWILIO_WRAPPER_HOST; per-service ConfigMap for FIREBASE_PROJECT_ID and PORT

3. **Kong k8s-specific kong.yml (fork) vs. sed at apply time**
   - What we know: The kong.yml needs underscore→hyphen substitution in URLs
   - Recommendation: Create a separate `k8s/kong/kong.yml` (fork of root kong.yml with hostnames updated). Do NOT modify the root kong.yml — Docker Compose still uses it. The k8s version differs only in upstream hostnames.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | Bash smoke script (no test framework — matches project convention) |
| Config file | `scripts/verify_phase6.sh` — to be created in Wave 0 |
| Quick run command | `bash scripts/verify_phase6.sh` |
| Full suite command | `bash scripts/verify_phase6.sh` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| K8S-01 | All 18 pods in Running state | smoke | `kubectl get pods --field-selector=status.phase=Running` | Wave 0 |
| K8S-02 | RabbitMQ StatefulSet + PVC exists | smoke | `kubectl get statefulset rabbitmq && kubectl get pvc` | Wave 0 |
| K8S-03 | Kong routes /api/* paths (non-502) | smoke | `curl -sf localhost:8000/api/vehicles` (after port-forward) | Wave 0 |
| K8S-04 | Firebase secret exists and mounted | smoke | `kubectl get secret firebase-sa` | Wave 0 |
| K8S-05 | ConfigMaps exist for all services | smoke | `kubectl get configmap` | Wave 0 |
| K8S-06 | docker-compose.yml unchanged/functional | manual | `docker-compose config` (no error) | Existing |
| K8S-07 | Three end-to-end scenarios succeed | smoke | `bash scripts/verify_phase6.sh` (JWT check + 200 response) | Wave 0 |

### Sampling Rate
- **Per task commit:** `kubectl get pods` — verify no new CrashLoopBackOff pods
- **Per wave merge:** `bash scripts/verify_phase6.sh`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `scripts/verify_phase6.sh` — covers K8S-01 through K8S-07
- [ ] `scripts/build-images.sh` — prerequisite for all pod starts
- [ ] `scripts/setup-secrets.sh` — prerequisite for all pod starts
- [ ] `k8s/` directory — no manifests exist yet

---

## Sources

### Primary (HIGH confidence)
- Kubernetes official documentation — Deployment, StatefulSet, Service, ConfigMap, Secret resource schemas
- Docker Desktop documentation — Kubernetes integration, shared Docker daemon, NodePort behavior on macOS
- Existing `docker-compose.yml` in project root — authoritative service inventory with all ports, env vars, volume mounts
- Existing `kong.yml` in project root — authoritative Kong configuration; all upstream URLs identified

### Secondary (MEDIUM confidence)
- K8s DNS specification (RFC 1123 hostname requirements) — Service name constraints; underscore prohibition
- Kubernetes StatefulSet documentation — volumeClaimTemplates pattern for RabbitMQ persistence
- Kong DB-less declarative config documentation — ConfigMap mount approach

### Tertiary (LOW confidence)
- NodePort range restriction (30000-32767 default) — standard K8s default; exact Docker Desktop behavior on macOS may allow port-forward workaround

---

## Metadata

**Confidence breakdown:**
- Service inventory: HIGH — derived directly from docker-compose.yml
- Manifest patterns: HIGH — standard K8s resources with well-documented APIs
- Underscore-to-hyphen mapping: HIGH — complete list derived from kong.yml and docker-compose.yml
- NodePort behavior on Docker Desktop: MEDIUM — standard K8s behavior; Docker Desktop may have quirks
- Worker self-healing timing: MEDIUM — depends on cluster load; estimated ~60s based on pika retry config

**Research date:** 2026-03-15
**Valid until:** 2026-04-15 (K8s APIs are stable; Docker Desktop version could shift behavior)
