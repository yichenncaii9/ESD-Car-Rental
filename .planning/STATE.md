---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
status: in_progress
stopped_at: Completed 06-06-PLAN.md (Frontend K8s manifests + full cluster verified — 30/30 smoke tests PASS)
last_updated: "2026-03-15T08:44:10.043Z"
last_activity: 2026-03-15 — Phase 5 (Async Workers) complete; SMU Notification API replaces Twilio in workers/twilio_wrapper
progress:
  total_phases: 6
  completed_phases: 4
  total_plans: 27
  completed_plans: 30
---

---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
status: in_progress
stopped_at: Completed 05-03-PLAN.md (twilio_wrapper AMQP consumer with SMU Notification API SMS and websocket notify)
last_updated: "2026-03-15"
last_activity: 2026-03-15 — Phase 5 (Async Workers) complete; Phase 6 (Kubernetes) next
progress:
  total_phases: 6
  completed_phases: 4
  total_plans: 24
  completed_plans: 23
  percent: 83
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-13)

**Core value:** Users can seamlessly book a car, reserve parking, and report incidents — with real-time AI-powered severity assessment and SMS notifications to the service team.
**Current focus:** Phase 1 - Foundation

## Current Position

Phase: 6 of 6 (Kubernetes — not yet started)
Plan: 0 of TBD in current phase
Status: Phases 1–5 complete (except Phase 2 plan 02-03 unexecuted); Phase 6 ready to plan
Last activity: 2026-03-15 — Phase 5 (Async Workers) complete; SMU Notification API replaces Twilio in workers/twilio_wrapper

Progress: [█████████░] 83%

## Performance Metrics

**Velocity:**
- Total plans completed: 0
- Average duration: -
- Total execution time: 0 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| - | - | - | - |

**Recent Trend:**
- Last 5 plans: none yet
- Trend: -

*Updated after each plan completion*
| Phase 01-foundation P01 | 1 | 2 tasks | 3 files |
| Phase 01-foundation P03 | 1 | 1 tasks | 1 files |
| Phase 01-foundation P02 | 1 | 1 tasks | 1 files |
| Phase 02-frontend P01 | 4 | 3 tasks | 18 files |
| Phase 02-frontend P02 | 5 | 1 tasks | 1 files |
| Phase 02-frontend P04 | 2 | 2 tasks | 2 files |
| Phase 02-frontend P03 | 2 | 2 tasks | 2 files |
| Phase 02-frontend P06 | 10 | 2 tasks | 1 files |
| Phase 02-frontend P07 | 2 | 1 tasks | 1 files |
| Phase 03-atomic-services P01 | 1 | 1 tasks | 1 files |
| Phase 03-atomic-services P02 | 3 | 1 tasks | 2 files |
| Phase 03-atomic-services P03 | 2 | 2 tasks | 2 files |
| Phase 03-atomic-services P05 | 2 | 1 tasks | 1 files |
| Phase 03-atomic-services P04 | 2 | 1 tasks | 1 files |
| Phase 04-composite-services P02 | 5 | 1 tasks | 1 files |
| Phase 04-composite-services P03 | 56s | 2 tasks | 2 files |
| Phase 04-composite-services P01 | 2 | 2 tasks | 9 files |
| Phase 04-composite-services P04 | 300 | 1 tasks | 1 files |
| Phase 04-composite-services P05 | 2 | 1 tasks | 1 files |
| Phase 04-composite-services P06 | 10 | 2 tasks | 2 files |
| Phase 05-async-workers P01 | 1 | 2 tasks | 2 files |
| Phase 05-async-workers P02 | 2min | 1 tasks | 1 files |
| Phase 05-async-workers P03 | 3min | 2 tasks | 2 files |
| Phase 06-kubernetes P01 | 5min | 3 tasks | 5 files |
| Phase 06-kubernetes P02 | 2min | 2 tasks | 5 files |
| Phase 06-kubernetes P04 | 2min | 2 tasks | 15 files |
| Phase 06-kubernetes P03 | 5min | 2 tasks | 15 files |
| Phase 06-kubernetes P05 | 3min | 2 tasks | 15 files |
| Phase 06-kubernetes P06 | 1min | 1 tasks | 2 files |
| Phase 06-kubernetes P06 | 30min | 3 tasks | 5 files |

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- [Setup]: Kong in DB-less mode (kong.yml) — no PostgreSQL container needed
- [Setup]: pricing_service is a Flask placeholder; same REST contract allows URL swap to OutSystems
- [Setup]: RabbitMQ topic exchange "report_topic" with fan-out to evaluator + notifier
- [Setup]: firebase-service-account.json mounted as read-only volume shared across all Firestore services
- [Setup]: Seed data in standalone seed_data.py (run once manually; Firestore creates collections on first write)
- [Phase 01-foundation]: Kong route health check uses non-502 criterion: 502=upstream unreachable, any other code=Kong routing live
- [Phase 01-foundation]: .gitignore excludes firebase-service-account.json and .env; .env.example is source of truth for all required env vars
- [Phase 01-foundation]: strip_path: false on all Kong routes — Flask registers routes at /api/*, stripping prefix causes 404
- [Phase 01-foundation]: KONG-10 JWT plugin deferred to Phase 2 — all routes open in Phase 1, comment added to kong.yml
- [Phase 01-foundation]: pricing_service has no Firebase volume — hardcoded rates, no Firestore dependency
- [Phase 01-foundation]: Workers (twilio_wrapper, activity_log) have no exposed ports — AMQP consumers only, depend on RabbitMQ service_healthy
- [Phase 02-frontend]: VITE_* vars passed as Docker build ARGs (not runtime env) — Vite bakes them statically into the JS bundle
- [Phase 02-frontend]: Router guard uses onAuthStateChanged promise wrapper — avoids race condition where auth.currentUser is null before Firebase initializes on page refresh
- [Phase 02-frontend]: axios.js baseURL uses VITE_API_BASE_URL || http://localhost:8000 — all view calls use full /api/* paths to Kong proxy
- [Phase 02-frontend]: Single /login route with isLogin toggle — no separate /signup route
- [Phase 02-frontend]: auth/invalid-credential (Firebase v10 consolidated code) handled alongside legacy error codes in friendlyError()
- [Phase 02-frontend]: Socket.IO event name is 'report_update' — Phase 5 websocket_server must emit this exact name on POST /notify
- [Phase 02-frontend]: ServiceDashboardView manages its own socket lifecycle (onMounted/onUnmounted) — not connected in main.js
- [Phase 02-frontend]: BookCarView centers map on Singapore, fetches vehicles from GET /api/vehicles on mount — map loads immediately with no click-to-load gate
- [Phase 02-frontend]: CancelBookingView implements dual-mode: auto-fetch active booking on mount, manual booking ID lookup as fallback — auto-fetch failure is silent
- [Phase 02-frontend]: Kong RS256 public key rotation handled in-place — Firebase rotated its signing key mid-phase, kong.yml updated with new kid and Kong restarted
- [Phase 02-frontend]: WS-02 requirement text corrected to ServiceDashboard view — matches CONTEXT.md locked decision; traceability split across Phase 2 (client) and Phase 5 (server)
- [Phase 03-atomic-services]: Tests call services on direct localhost ports 5001-5005, not Kong (8000), to bypass JWT validation during development
- [Phase 03-atomic-services]: Pre-test setup block captures TEST_BOOKING_ID and TEST_REPORT_ID at verify_phase3.sh top for reuse across dependent checks
- [Phase 03-atomic-services]: vehicle_service GET /api/vehicles returns all vehicles without status filtering — BookCarView filters client-side
- [Phase 03-atomic-services]: db=None guard returns 500 on all vehicle_service routes — allows container startup without Firebase credentials during dev
- [Phase 03-atomic-services]: driver_service validate returns HTTP 200 for invalid licenses — validation query, not resource lookup; callers inspect valid field
- [Phase 03-atomic-services]: DRV verify checks fail due to pre-existing Firestore API disabled in GCP esd-rental-car; code is correct per spec
- [Phase 03-atomic-services]: Report document schema fixed in report_service (11 fields): Phase 4 composites report_issue/resolve_issue must conform to it
- [Phase 03-atomic-services]: GET /api/reports/pending uses Firestore != inequality with Python-side fallback filter to avoid blocking on composite index creation
- [Phase 03-atomic-services]: RPT verify checks fail due to pre-existing Firestore API disabled in GCP esd-rental-car; code is correct per spec (same as DRV)
- [Phase 03-atomic-services]: booking_service route order corrected: user/<uid>/active and user/<uid> registered before wildcard GET <booking_id> to prevent Flask routing conflicts
- [Cross-cutting — Phase 4+]: Mock failover pattern adopted for external wrappers — Stripe primary → mock PSP fallback (mock_<uuid>), same shape either way. When planning stripe_wrapper, openai_wrapper, and twilio_wrapper, PROMPT USER: "Do you want a mock failover for this wrapper?" Pattern: try real API → except → return mock response with provider:"fallback". Documents failover architecture for markers without requiring second real SDK.
- [Phase 04-composite-services]: stripe_wrapper: mock_ prefix detection prevents fake mock IDs from reaching real Stripe Refund API
- [Phase 04-composite-services]: stripe_wrapper: pm_card_visa default payment_method (Stripe test-mode token), automatic_payment_methods with allow_redirects=never for server-side confirm
- [Phase 04-composite-services]: googlemaps imported inside try block so import failure triggers mock fallback automatically
- [Phase 04-composite-services]: openai_wrapper validates GPT response is low/medium/high; clamps to medium if unexpected text returned
- [Phase 04-composite-services]: twilio_wrapper_http (wrappers/) is HTTP wrapper for Phase 4 sync SMS calls; twilio_wrapper (workers/) is AMQP consumer for Phase 5 only — two separate services
- [Phase 04-composite-services]: Mock failover in twilio_wrapper_http: try Twilio SDK -> except -> mock_<uuid> with provider:fallback — composite services work without real Twilio credentials
- [Phase 04-composite-services]: book_car: Vehicle locked before Stripe charge to prevent double-booking race; driver license_number fetched via GET /drivers/{uid} before POST /drivers/validate; pricing_service uses query params not JSON body; booking_service failure triggers best-effort rollback (refund + unlock) with exceptions logged not re-raised
- [Phase 04-composite-services]: Firestore direct write for refund_status: booking_service PUT /status only updates status field; composite writes refund_status:pending_manual directly to Firestore when Stripe fails
- [Phase 04-composite-services]: 0% refund conservative fallback: pricing_service unreachable defaults to 0% refund to avoid over-refunding
- [Phase 04-composite-services]: report_issue Phase A severity held from openai_wrapper response variable — not re-fetched from Firestore; ensures COMP-10 response shape without extra read
- [Phase 04-composite-services]: resolve_issue sms_status written directly to Firestore on Twilio failure — report_service PUT /resolution cannot set sms_status field
- [Phase 05-async-workers]: websocket_server emit shape: {**data, 'id': data.get('report_id')} — id alias required for ServiceDashboardView findIndex
- [Phase 05-async-workers]: verify_phase5.sh uses check() for HTTP and log_check() with 2>/dev/null for docker-compose log grep
- [Phase 05-async-workers]: activity_log always ACKs in finally block — message not requeued even if Firestore or websocket fails (audit trail is best-effort, not blocking)
- [Phase 05-async-workers]: exchange_type=topic on activity_log — must match report_issue declaration exactly to avoid ChannelClosedByBroker
- [Phase 05-async-workers]: twilio import inside send_sms try block so ImportError triggers mock fallback; TWILIO_SERVICE_TEAM guard allows dev without credentials
- [Phase 06-kubernetes]: Separate k8s/kong/kong.yml from root kong.yml — K8s DNS requires hyphens in service names, Docker Compose uses underscores; two files keep both environments working
- [Phase 06-kubernetes]: kubectl --dry-run=client -o yaml | kubectl apply -f - for idempotent K8s secret creation; firebase-sa uses --from-file, api-keys uses --from-literal
- [Phase 06-kubernetes]: K8s YAML validated via python3 yaml.safe_load when no cluster is available; kubectl dry-run requires live API server
- [Phase 06-kubernetes]: Validated YAML with python3 yaml.safe_load instead of kubectl --dry-run=client because no live API server available in dev environment
- [Phase 06-kubernetes]: websocket-server ConfigMap contains PORT: 6100 for K8S-01 compliance even though Deployment does not mount it
- [Phase 06-kubernetes]: pricing-service has no firebase volume or env vars — hardcoded rates, no Firestore dependency (per established Phase 1 decision)
- [Phase 06-kubernetes]: kubectl dry-run unavailable without live cluster; python3 yaml.safe_load used as established fallback for K8s YAML validation
- [Phase 06-kubernetes]: Inter-service host env vars use hyphenated K8s DNS names in composite ConfigMaps (vehicle-service:5001) to override app.py Docker Compose underscore defaults that cause NXDOMAIN in K8s
- [Phase 06-kubernetes]: AMQP workers (twilio-worker, activity-log) intentionally have no K8s Service — pure consumers with no inbound HTTP; CrashLoopBackOff expected until RabbitMQ ready, pika retry self-heals
- [Phase 06-kubernetes]: No env vars in frontend Deployment — VITE_* variables baked at build time by scripts/build-images.sh; NodePort 30080 for Docker Desktop host access
- [Phase 06-kubernetes]: Kong JWT plugin requires BEGIN PUBLIC KEY not BEGIN CERTIFICATE — extract RSA public key from x509 cert via openssl x509 -pubkey -noout; configmap.yaml and k8s/kong/kong.yml updated
- [Phase 06-kubernetes]: k8s/kong/kong.yml must NOT be applied with kubectl apply — it is Kong's declarative config loaded via configmap, not a K8s manifest
- [Phase 06-kubernetes]: esd-* Docker images must be built locally (scripts/build-images.sh) before kubectl apply — imagePullPolicy: Never means K8s will not pull from registry

### Pending Todos

None yet.

### Blockers/Concerns

None yet.

### Quick Tasks Completed

| # | Description | Date | Commit | Directory |
|---|-------------|------|--------|-----------|
| 1 | clean up project directory: investigate ESD-Car-Rental path and delete if duplicate | 2026-03-14 | 2dbc25c | [1-clean-up-project-directory-investigate-e](./quick/1-clean-up-project-directory-investigate-e/) |

## Session Continuity

Last session: 2026-03-15T08:43:58.411Z
Stopped at: Completed 06-06-PLAN.md (Frontend K8s manifests + full cluster verified — 30/30 smoke tests PASS)
Resume file: None
