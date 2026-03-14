# Roadmap: ESD Rental Car Service

## Overview

The project builds a 18-container microservices system delivering three user-facing scenarios: book a car (sync orchestration with Stripe), cancel a booking with refund (cancellation policy + Stripe refund), and report incidents (sync + async with AI evaluation, SMS, and real-time WebSocket push). Services are organized in SOA layers: composite/, atomic/, workers/, wrappers/, frontend/. Phases follow the natural dependency chain: infrastructure must exist before services run, atomic services must exist before composites can orchestrate them, AMQP workers depend on composite services publishing events, and Kubernetes migration comes last once all scenarios work on Docker Compose.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [x] **Phase 1: Foundation** - Docker Compose scaffold, Kong gateway, RabbitMQ, and seed data (completed 2026-03-13)
- [ ] **Phase 2: Frontend** - Vue.js 3 app with Firebase Auth, Google Maps, and Kong-routed API calls
- [ ] **Phase 3: Atomic Services** - Five atomic Flask microservices (vehicle, booking, driver, report, pricing)
- [ ] **Phase 4: Composite Services** - Four composite orchestration services covering all three user scenarios
- [ ] **Phase 5: Async Workers** - AMQP workers for Twilio SMS and WebSocket real-time push; openai_wrapper is HTTP
- [ ] **Phase 6: Kubernetes** - Convert all 18 services to Kubernetes manifests for production deployment

## Phase Details

### Phase 1: Foundation
**Goal**: The full infrastructure is running — all 18 containers start cleanly, Kong routes all 9 upstreams, RabbitMQ is ready, and Firestore is seeded with demo data. Services are organized in SOA layers (composite/, atomic/, workers/, wrappers/, frontend/). JWT validation is deferred to Phase 2 (KONG-10).
**Depends on**: Nothing (first phase)
**Requirements**: INFRA-01, INFRA-02, INFRA-03, INFRA-04, INFRA-05, INFRA-06, KONG-01, KONG-02, KONG-03, KONG-04, KONG-05, KONG-06, KONG-08, KONG-09, KONG-11, DATA-01, DATA-02
**Deferred to Phase 2**: KONG-10 (JWT plugin on Kong routes — deferred per CONTEXT.md locked decision; Firebase tokens not available until Phase 2 frontend exists)
**Success Criteria** (what must be TRUE):
  1. Running `docker-compose up` starts all 18 containers without errors and all healthchecks pass
  2. The RabbitMQ management UI is reachable at http://localhost:15672
  3. The Kong admin API responds at http://localhost:8001 and the proxy at http://localhost:8000 forwards a test request to the correct upstream
  4. All 9 Kong routes are open (no JWT validation) — JWT auth added in Phase 2
  5. Running `seed_data.py` populates Firestore with 10 vehicles and sample driver records, and a second run does not create duplicates
**Plans**: 5 plans

Plans:
- [ ] 01-01-PLAN.md — Wave 0: verify_phase1.sh smoke test script + .gitignore + .env.example
- [ ] 01-02-PLAN.md — Wave 1: docker-compose.yml for all 18 containers on rental-net
- [ ] 01-03-PLAN.md — Wave 1: kong.yml DB-less config with 9 routes, CORS, rate-limiting
- [ ] 01-04-PLAN.md — Wave 1: Flask stub services for composite (4) + atomic (5) layers
- [ ] 01-05-PLAN.md — Wave 1: Flask stubs for workers/wrappers/websocket_server + frontend placeholder + seed_data.py

### Phase 2: Frontend
**Goal**: Users can open the web app, authenticate with Firebase, and navigate to all four views — with every API call passing through Kong with the JWT attached.
**Depends on**: Phase 1
**Requirements**: FE-01, FE-02, FE-03, FE-04, FE-05, FE-06, KONG-10
**Success Criteria** (what must be TRUE):
  1. The Vue.js app loads at http://localhost:8080 in a browser
  2. A user can sign up and log in with email/password via Firebase Auth; unauthenticated users are redirected to Login
  3. After login, the browser can navigate to BookCar, CancelBooking, ReportIncident, and ServiceDashboard routes
  4. Google Maps renders a map widget inside BookCar and ReportIncident views
  5. All outbound API calls in the browser use the /api/* prefix (Kong proxy), and the Authorization header contains the Firebase JWT
  6. Kong JWT plugin is enabled on all routes; valid Firebase JWTs pass, missing/invalid JWTs return 401
**Plans**: 6 plans

Plans:
- [ ] 02-01-PLAN.md — Wave 1: Vue 3 Vite scaffold, firebase.js, axios.js, router, auth store, NavBar, multi-stage Dockerfile
- [ ] 02-02-PLAN.md — Wave 2: LoginView with Firebase Auth login/signup toggle, inline errors, spinner
- [ ] 02-03-PLAN.md — Wave 2: BookCarView (GMapMap + vehicle markers) + CancelBookingView
- [ ] 02-04-PLAN.md — Wave 2: ReportIncidentView (GMapMap + geolocation + Places) + ServiceDashboardView (Socket.IO)
- [ ] 02-05-PLAN.md — Wave 2: Kong JWT plugin config (RS256 consumer + jwt plugin on all 9 routes)
- [ ] 02-06-PLAN.md — Wave 3: Browser verification checkpoint (all 6 success criteria)

### Phase 3: Atomic Services
**Goal**: Every atomic microservice is running and correctly reading from and writing to Firestore, with all documented REST endpoints functional.
**Depends on**: Phase 1
**Requirements**: VEH-01, VEH-02, VEH-03, BOOK-01, BOOK-02, BOOK-03, BOOK-04, BOOK-05, DRV-01, DRV-02, RPT-01, RPT-02, RPT-03, RPT-04, RPT-05, PRICE-01, PRICE-02
**Success Criteria** (what must be TRUE):
  1. GET /api/vehicles returns the 10 seeded vehicles; GET /api/vehicles/<id> returns a single vehicle; PUT /api/vehicles/<id>/status updates its status in Firestore
  2. POST /api/bookings creates a booking in Firestore; GET /api/bookings/user/<uid>/active returns that booking; PUT /api/bookings/<id>/status updates it
  3. GET /api/drivers/<uid> returns driver record; POST /api/drivers validates license number + expiry and returns `{ valid: true/false }`
  4. POST /api/reports creates an incident report; GET /api/reports/<id> returns it; PUT /api/reports/<id>/evaluation and PUT /api/reports/<id>/resolution update it; GET /api/reports/pending returns unresolved reports
  5. GET /api/pricing returns hardcoded rates (sedan $12.50/hr, suv $18/hr, van $15/hr); GET /api/pricing/calculate returns a calculated total for given type and hours
**Plans**: TBD

### Phase 4: Composite Services
**Goal**: All three user-facing scenarios execute end-to-end — a car can be booked and paid for, a booking can be cancelled with a policy-based Stripe refund, and an incident can be submitted — with correct rollback and error handling at each step.
**Depends on**: Phase 3
**Requirements**: COMP-01, COMP-02, COMP-03, COMP-04, COMP-05, COMP-06, COMP-07, COMP-08, COMP-09, COMP-10, COMP-11
**Success Criteria** (what must be TRUE):
  1. POST /api/book-car completes the full driver_service → vehicle → pricing → booking → stripe_wrapper flow and returns a confirmed booking; a Stripe failure triggers vehicle unlock and booking cancellation
  2. POST /api/cancel-booking applies cancellation policy (full refund >24hrs, 50% if 1–24hrs, $0 if <1hr), calls stripe_wrapper for refund, releases vehicle, and returns confirmation; a Stripe refund failure still cancels the booking and flags refund for manual processing
  3. POST /api/report-issue: Phase A persists report with geocoded location, calls openai_wrapper HTTP for severity, updates report, returns `{ report_id, status: "submitted", severity }`; Phase B publishes to RabbitMQ "report_topic" with routing key "report.new"
  4. twilio_wrapper (AMQP consumer) sends SMS to service team; activity_log (AMQP consumer) logs event; both POST to websocket_server which emits Socket.IO update to the connected frontend
  5. POST /api/resolve-issue updates the report resolution and sends a Twilio SMS to the driver; if Twilio fails, the report is still updated and flagged with SMS unsent
**Plans**: TBD

### Phase 5: Async Workers
**Goal**: After an incident is submitted and Phase A returns synchronously, the AMQP consumers process the event asynchronously — twilio_wrapper sends SMS, activity_log persists the audit event, and websocket_server pushes real-time updates to the frontend. openai_wrapper is HTTP-only (called in Phase A, not here).
**Depends on**: Phase 4
**Requirements**: WORK-01, WORK-02, WORK-03, WORK-04, WORK-05, WORK-06, WORK-07, WS-01, WS-02, WS-03, WS-04
**Success Criteria** (what must be TRUE):
  1. twilio_wrapper subscribes to "report_topic" with key "report.new", sends SMS to service team via Twilio, then HTTP POSTs to websocket_server
  2. activity_log subscribes to "report_topic" with key "report.new", persists audit event to Firestore, then HTTP POSTs to websocket_server
  3. websocket_server emits a Socket.IO event to the connected ReportIncident frontend client on receiving POST /notify
  4. Vue.js ReportIncident view connects to websocket_server on load and displays the real-time update when the event arrives
  5. Both AMQP consumers start successfully even if RabbitMQ is not yet ready at container startup (pika retry logic)
**Plans**: TBD

### Phase 6: Kubernetes
**Goal**: All 18 services run cleanly in a Kubernetes cluster using declarative manifests — same Dockerfiles and Flask apps as Docker Compose, just different orchestration. docker-compose.yml is preserved for local dev.
**Depends on**: Phase 5 (all 3 scenarios must work on Docker Compose first)
**Requirements**: K8S-01, K8S-02, K8S-03, K8S-04, K8S-05, K8S-06, K8S-07
**Success Criteria** (what must be TRUE):
  1. All 17 pods start cleanly in the Kubernetes cluster with no CrashLoopBackOff errors
  2. POST /api/book-car, /api/cancel-booking, and /api/report-issue all succeed end-to-end via Kong Ingress in the cluster
  3. firebase-service-account.json is stored as a Kubernetes Secret and mounted into pods — not present in any manifest YAML
  4. `docker-compose up` still works for local dev (unchanged)
**Plans**: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4 → 5

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Foundation | 3/5 | Complete    | 2026-03-13 |
| 2. Frontend | 0/6 | Not started | - |
| 3. Atomic Services | 0/TBD | Not started | - |
| 4. Composite Services | 0/TBD | Not started | - |
| 5. Async Workers | 0/TBD | Not started | - |
| 6. Kubernetes | 0/TBD | Not started | - |
