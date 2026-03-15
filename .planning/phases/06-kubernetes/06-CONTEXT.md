# Phase 6: Kubernetes - Context

**Gathered:** 2026-03-15
**Status:** Ready for planning

<domain>
## Phase Boundary

Convert all 18 services from Docker Compose to Kubernetes manifests in a `k8s/` directory. Same Dockerfiles and Flask apps — different orchestration layer. Docker Compose is preserved and functional for local development (K8S-06). All three scenarios (book-car, cancel-booking, report-issue) must work end-to-end in the K8s cluster (K8S-07).

</domain>

<decisions>
## Implementation Decisions

### Target cluster
- **Docker Desktop Kubernetes** — local single-node cluster, shares the local Docker daemon
- All 18 services deployed (full stack, not demo-minimum) — satisfies K8S-01
- **default namespace** — no custom namespace needed; zero extra config
- **verify_phase6.sh** smoke test script included — consistent with verify_phase3.sh/verify_phase5.sh; validates all pods Running, Kong routing live, and end-to-end scenarios pass

### Kong routing approach
- Kong runs as a **standalone Deployment + Service** (not Kong Ingress Controller)
- Direct translation of Docker Compose Kong: same DB-less `kong.yml`, same ports, same plugins
- `kong.yml` mounted as a **ConfigMap** — structure, routes, and plugins unchanged
- **One required change:** upstream hostnames updated from underscore to hyphen (K8s DNS cannot use underscores):
  - `composite_book_car:6001` → `composite-book-car:6001`
  - `composite_cancel_booking:6002` → `composite-cancel-booking:6002`
  - etc. — find-and-replace only, not a rewrite
- Kong exposed via **NodePort on port 8000** — accessible at `localhost:8000` on Docker Desktop

### Image access strategy
- **imagePullPolicy: Never** on all Deployments — K8s uses locally-built images from Docker daemon, no registry needed
- Image naming convention: `esd-<service-name>:latest`
  - e.g. `esd-vehicle-service:latest`, `esd-composite-book-car:latest`, `esd-rabbitmq:latest`
  - Hyphenated names, `esd-` prefix to avoid collisions with pulled images
- **`scripts/build-images.sh`** — shell script that builds all 18 images in one command with correct tags

### Secrets and ConfigMap delivery
- **`scripts/setup-secrets.sh`** — sources `.env` automatically (`set -a; source .env; set +a`), then runs `kubectl create secret` commands for all sensitive values
- **Secrets (sensitive values):** API keys and credentials — `STRIPE_SECRET_KEY`, `OPENAI_API_KEY`, `GOOGLE_MAPS_API_KEY`, `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_FROM_NUMBER`, `TWILIO_SERVICE_TEAM_NUMBER`
- **firebase-service-account.json** stored as a separate K8s Secret (`kubectl create secret generic firebase-sa --from-file=firebase-service-account.json`), mounted read-only into all Firestore-connected pods at `/secrets/firebase-service-account.json`
- **ConfigMaps (non-sensitive values):** `FIREBASE_PROJECT_ID`, `RABBITMQ_HOST`, `RABBITMQ_PORT`, `WEBSOCKET_SERVER_URL`, `TWILIO_WRAPPER_HOST`, `PORT` per service — declared as YAML ConfigMaps in `k8s/`
- **Frontend VITE_* vars** baked into the image at build time (not runtime env) — `scripts/build-images.sh` passes them as `--build-arg` from `.env`
- No Secret YAML files committed to git; setup script is the single source of truth

### Claude's Discretion
- Exact replica count per Deployment (1 is appropriate for a university demo)
- RabbitMQ StatefulSet PVC size and storage class
- Liveness/readiness probe paths and intervals (can mirror existing Docker healthchecks: `/health` endpoints)
- Inter-service DNS resolution pattern in manifests (use K8s Service names as hostnames in env vars)
- Whether to split ConfigMaps per service or use shared ConfigMaps for common values (RABBITMQ_HOST etc.)

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `docker-compose.yml`: Complete service inventory with all ports, env vars, volume mounts, and healthcheck paths — direct translation guide for K8s Deployments
- `kong.yml`: DB-less Kong config — becomes a ConfigMap; only upstream hostname find-and-replace needed
- All service Dockerfiles: Unchanged — K8s uses the same images
- `scripts/` directory already exists for seed_data.py and verify scripts — add build-images.sh and setup-secrets.sh here

### Established Patterns
- All Firestore services mount `firebase-service-account.json` at `/secrets/firebase-service-account.json:ro` — same path must be preserved in K8s volume mounts
- Workers (twilio_wrapper, activity_log) have no exposed ports — ClusterIP or headless Service only
- pricing_service has no Firebase volume — no Secret mount needed for it
- `GOOGLE_APPLICATION_CREDENTIALS` env var points to `/secrets/firebase-service-account.json` in all Firestore services

### Integration Points
- All services currently communicate via Docker Compose service names (e.g. `vehicle_service:5001`) — must be updated to K8s Service names (e.g. `vehicle-service:5001`) in env vars across manifests
- Kong ConfigMap upstream URLs: underscore→hyphen conversion required (see decisions above)
- RabbitMQ: currently a regular Docker Compose service with a named volume — becomes a StatefulSet with PVC in K8s (K8S-02)

</code_context>

<specifics>
## Specific Ideas

- kong.yml upstream hostname change is a find-and-replace (underscore→hyphen), not a structural rewrite — the ConfigMap approach preserves all routes, plugins, and JWT config exactly
- `scripts/build-images.sh` should loop through all 18 service directories in order and tag with `esd-` prefix — one command to rebuild the full stack
- `scripts/setup-secrets.sh` sources `.env` so no manual copy-paste of API keys — same UX as `docker-compose up` which also reads `.env`

</specifics>

<deferred>
## Deferred Ideas

- None — discussion stayed within Phase 6 scope

</deferred>

---

*Phase: 06-kubernetes*
*Context gathered: 2026-03-15*
