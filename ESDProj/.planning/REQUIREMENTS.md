# Requirements: ESD Rental Car Service

**Defined:** 2026-03-13
**Core Value:** Users can book a car, cancel a booking with refund, and report incidents — backed by cancellation policy enforcement, AI severity assessment, and SMS notifications

## v1 Requirements

### Infrastructure

- [x] **INFRA-01**: Docker Compose brings up all 18 containers cleanly on `docker-compose up` (1 frontend, 1 kong, 1 rabbitmq, 4 composite, 5 atomic, 1 websocket_server, 3 wrappers, 2 workers)
- [x] **INFRA-02**: All services are on a shared Docker network "rental-net"
- [x] **INFRA-03**: RabbitMQ management UI accessible at port 15672
- [x] **INFRA-04**: Kong admin API accessible at port 8001, proxy at port 8000
- [x] **INFRA-05**: .env.example documents all required API keys
- [x] **INFRA-06**: .gitignore excludes firebase-service-account.json and .env

### Frontend

- [ ] **FE-01**: Vue.js 3 (Vite) app serves on port 8080
- [ ] **FE-02**: User can log in and sign up via Firebase Auth (email/password)
- [ ] **FE-03**: Firebase JWT is attached to every API request via Axios interceptor
- [ ] **FE-04**: Router has routes for Login, BookCar, CancelBooking, ReportIncident, ServiceDashboard
- [ ] **FE-05**: Google Maps JS SDK renders map in BookCar and ReportIncident views
- [ ] **FE-06**: All API calls route through Kong at /api/* (not direct to services)

### API Gateway (Kong)

- [x] **KONG-01**: Kong routes /api/book-car to composite_book_car:6001
- [x] **KONG-02**: Kong routes /api/cancel-booking to composite_cancel_booking:6002
- [x] **KONG-03**: Kong routes /api/report-issue to composite_report_issue:6003
- [x] **KONG-04**: Kong routes /api/resolve-issue to composite_resolve_issue:6004
- [x] **KONG-05**: Kong routes /api/vehicles to vehicle_service:5001
- [x] **KONG-06**: Kong routes /api/bookings to booking_service:5002
- [ ] **KONG-07**: Kong routes /api/drivers to driver_service:5003
- [x] **KONG-08**: Kong routes /api/reports to report_service:5004
- [x] **KONG-09**: Kong routes /api/pricing to pricing_service:5005
- [ ] **KONG-10**: Kong jwt plugin validates Firebase JWT on all routes
- [x] **KONG-11**: Kong cors and rate-limiting plugins enabled

### Composite Services

- [ ] **COMP-01**: book_car POST /book-car orchestrates driver_service (license check) → vehicle_service → pricing_service → booking_service → stripe_wrapper and returns a confirmed booking
- [ ] **COMP-02**: book_car handles Stripe payment failure with vehicle unlock + booking cancellation rollback
- [ ] **COMP-03**: cancel_booking POST /cancel-booking fetches booking from booking_service and rejects if status is active trip or already cancelled
- [ ] **COMP-04**: cancel_booking calculates refund amount via pricing_service using cancellation policy (full refund >24hrs before pickup, 50% if 1–24hrs, $0 if <1hr)
- [ ] **COMP-05**: cancel_booking calls stripe_wrapper to process refund, then calls booking_service to set status "cancelled" and vehicle_service to set vehicle status "available"
- [ ] **COMP-06**: cancel_booking handles Stripe refund failure gracefully — booking is still cancelled, refund flagged as "pending_manual" in Firestore
- [ ] **COMP-07**: cancel_booking returns `{ booking_id, status: "cancelled", refund_amount, refund_status }` — refund_status is "processed" or "pending_manual"
- [ ] **COMP-08**: report_issue POST /report-issue Phase A (sync): booking_service check → googlemaps_wrapper reverse geocode → openai_wrapper HTTP call (severity classification) → report_service persist
- [ ] **COMP-09**: report_issue Phase B (async): publishes to RabbitMQ "report_topic" exchange with key "report.new" (includes severity from openai_wrapper)
- [ ] **COMP-10**: report_issue returns `{ report_id, status: "submitted", severity }` after Phase A; Phase B publishes asynchronously
- [ ] **COMP-11**: resolve_issue POST /resolve-issue calls report_service (update resolution) → Twilio SMS to driver; handles Twilio failure gracefully (update report, flag SMS unsent)

### Atomic Services

- [ ] **VEH-01**: vehicle_service GET /vehicles returns list of available vehicles with filters
- [ ] **VEH-02**: vehicle_service GET /vehicles/<id> returns single vehicle
- [ ] **VEH-03**: vehicle_service PUT /vehicles/<id>/status updates vehicle status in Firestore
- [ ] **BOOK-01**: booking_service POST /bookings creates booking in Firestore
- [ ] **BOOK-02**: booking_service GET /bookings/<id> returns booking
- [ ] **BOOK-03**: booking_service GET /bookings/user/<uid>/active returns active booking for user
- [ ] **BOOK-04**: booking_service GET /bookings/user/<uid> returns all bookings for user
- [ ] **BOOK-05**: booking_service PUT /bookings/<id>/status updates booking status
- [ ] **DRV-01**: driver_service GET /drivers/<uid> returns driver record from Firestore
- [ ] **DRV-02**: driver_service POST /drivers/validate checks license number + expiry and returns `{ valid: true/false, reason? }`
- [ ] **RPT-01**: report_service POST /reports creates incident report in Firestore
- [ ] **RPT-02**: report_service GET /reports/<id> returns report
- [ ] **RPT-03**: report_service PUT /reports/<id>/evaluation updates with AI diagnosis
- [ ] **RPT-04**: report_service PUT /reports/<id>/resolution updates with team resolution
- [ ] **RPT-05**: report_service GET /reports/pending returns all pending reports for service dashboard
- [ ] **PRICE-01**: pricing_service GET /pricing returns all pricing rules (hardcoded: sedan $12.50/hr, suv $18/hr, van $15/hr)
- [ ] **PRICE-02**: pricing_service GET /pricing/calculate returns calculated price (query: vehicle_type, hours)

### AMQP Workers

- [ ] **WORK-01**: twilio_wrapper subscribes to "twilio_queue" bound to "report_topic" with key "report.new"
- [ ] **WORK-02**: twilio_wrapper sends SMS to service team via Twilio API (severity already persisted in Phase A)
- [ ] **WORK-03**: twilio_wrapper HTTP POSTs `{ report_id, event: "sms_sent" }` to websocket_server after SMS is sent
- [ ] **WORK-04**: twilio_wrapper HTTP POSTs update payload to websocket_server after SMS is sent
- [ ] **WORK-05**: activity_log subscribes to "activity_queue" bound to "report_topic" with key "report.new"
- [ ] **WORK-06**: activity_log persists event to Firestore for audit trail and HTTP POSTs update payload to websocket_server
- [ ] **WORK-07**: Both workers have pika retry logic (RabbitMQ may not be ready at startup)

### WebSocket

- [ ] **WS-01**: websocket_server runs on port 6100, Flask-SocketIO, part of the 17-container stack
- [ ] **WS-02**: Vue.js frontend connects to websocket_server via Socket.IO on load of ReportIncident view
- [ ] **WS-03**: websocket_server exposes a POST /notify endpoint that accepts an update payload and emits a Socket.IO event to connected clients
- [ ] **WS-04**: When a Scenario 3 async event completes (twilio_wrapper or activity_log finishes), websocket_server pushes the update to the frontend without polling

### Data & Seeding

- [ ] **DATA-01**: seed_data.py creates 10 vehicles (sedan/suv/van) with SG plate numbers in Firestore
- [ ] **DATA-02**: seed_data.py creates sample driver records with license number + expiry in Firestore
- [ ] **DATA-03**: seed_data.py skips documents that already exist (idempotent)

### Kubernetes

- [ ] **K8S-01**: Every service has a Kubernetes Deployment + Service + ConfigMap manifest (k8s/ directory)
- [ ] **K8S-02**: RabbitMQ runs as a Kubernetes StatefulSet with persistent volume
- [ ] **K8S-03**: Kong runs as a standalone Kubernetes pod or Ingress controller, routing all /api/* paths
- [ ] **K8S-04**: firebase-service-account.json stored as a Kubernetes Secret, mounted read-only into all Firestore-connected pods
- [ ] **K8S-05**: All .env values migrated to Kubernetes ConfigMaps (non-sensitive) and Secrets (API keys)
- [ ] **K8S-06**: docker-compose.yml is preserved and functional for local development
- [ ] **K8S-07**: All three scenarios (book-car, cancel-booking, report-issue) work end-to-end in the Kubernetes cluster

## v2 Requirements

### Notifications

- **NOTF-01**: In-app real-time notifications for booking status changes
- **NOTF-02**: Email notifications via SendGrid for booking confirmations

### Enhancements

- **ENH-01**: Admin dashboard for vehicle fleet management
- **ENH-02**: Booking history with search and filter
- **ENH-03**: Multi-language support (EN/ZH)

## Out of Scope

| Feature | Reason |
|---------|--------|
| MySQL/PostgreSQL container | Firestore is the database; no SQL needed |
| OutSystems container | Hosted externally; placeholder Flask service used locally |
| Mobile app | Web-first for university project scope |
| OAuth (Google, GitHub) | Firebase email/password sufficient for v1 |
| parking_service | Removed — cancel_booking replaced reserve_parking as Scenario 2 |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| INFRA-01 | Phase 1 - Foundation | Complete |
| INFRA-02 | Phase 1 - Foundation | Complete |
| INFRA-03 | Phase 1 - Foundation | Complete |
| INFRA-04 | Phase 1 - Foundation | Complete |
| INFRA-05 | Phase 1 - Foundation | Complete |
| INFRA-06 | Phase 1 - Foundation | Complete |
| KONG-01 | Phase 1 - Foundation | Complete |
| KONG-02 | Phase 1 - Foundation | Complete |
| KONG-03 | Phase 1 - Foundation | Complete |
| KONG-04 | Phase 1 - Foundation | Complete |
| KONG-05 | Phase 1 - Foundation | Complete |
| KONG-06 | Phase 1 - Foundation | Complete |
| KONG-07 | Phase 1 - Foundation | Pending |
| KONG-08 | Phase 1 - Foundation | Complete |
| KONG-09 | Phase 1 - Foundation | Complete |
| KONG-10 | Phase 1 - Foundation | Pending |
| KONG-11 | Phase 1 - Foundation | Complete |
| DATA-01 | Phase 1 - Foundation | Pending |
| DATA-02 | Phase 1 - Foundation | Pending |
| DATA-03 | Phase 1 - Foundation | Pending |
| DRV-01 | Phase 3 - Atomic Services | Pending |
| DRV-02 | Phase 3 - Atomic Services | Pending |
| FE-01 | Phase 2 - Frontend | Pending |
| FE-02 | Phase 2 - Frontend | Pending |
| FE-03 | Phase 2 - Frontend | Pending |
| FE-04 | Phase 2 - Frontend | Pending |
| FE-05 | Phase 2 - Frontend | Pending |
| FE-06 | Phase 2 - Frontend | Pending |
| VEH-01 | Phase 3 - Atomic Services | Pending |
| VEH-02 | Phase 3 - Atomic Services | Pending |
| VEH-03 | Phase 3 - Atomic Services | Pending |
| BOOK-01 | Phase 3 - Atomic Services | Pending |
| BOOK-02 | Phase 3 - Atomic Services | Pending |
| BOOK-03 | Phase 3 - Atomic Services | Pending |
| BOOK-04 | Phase 3 - Atomic Services | Pending |
| BOOK-05 | Phase 3 - Atomic Services | Pending |
| RPT-01 | Phase 3 - Atomic Services | Pending |
| RPT-02 | Phase 3 - Atomic Services | Pending |
| RPT-03 | Phase 3 - Atomic Services | Pending |
| RPT-04 | Phase 3 - Atomic Services | Pending |
| RPT-05 | Phase 3 - Atomic Services | Pending |
| PRICE-01 | Phase 3 - Atomic Services | Pending |
| PRICE-02 | Phase 3 - Atomic Services | Pending |
| COMP-01 | Phase 4 - Composite Services | Pending |
| COMP-02 | Phase 4 - Composite Services | Pending |
| COMP-03 | Phase 4 - Composite Services | Pending |
| COMP-04 | Phase 4 - Composite Services | Pending |
| COMP-05 | Phase 4 - Composite Services | Pending |
| COMP-06 | Phase 4 - Composite Services | Pending |
| COMP-07 | Phase 4 - Composite Services | Pending |
| COMP-08 | Phase 4 - Composite Services | Pending |
| COMP-09 | Phase 4 - Composite Services | Pending |
| COMP-10 | Phase 4 - Composite Services | Pending |
| COMP-11 | Phase 4 - Composite Services | Pending |
| WORK-01 | Phase 5 - Async Workers | Pending |
| WORK-02 | Phase 5 - Async Workers | Pending |
| WORK-03 | Phase 5 - Async Workers | Pending |
| WORK-04 | Phase 5 - Async Workers | Pending |
| WORK-05 | Phase 5 - Async Workers | Pending |
| WORK-06 | Phase 5 - Async Workers | Pending |
| WORK-07 | Phase 5 - Async Workers | Pending |
| WS-01 | Phase 1 - Foundation (container) / Phase 5 - Async Workers (integration) | Pending |
| WS-02 | Phase 2 - Frontend | Pending |
| WS-03 | Phase 5 - Async Workers | Pending |
| WS-04 | Phase 5 - Async Workers | Pending |
| K8S-01 | Phase 6 - Kubernetes | Pending |
| K8S-02 | Phase 6 - Kubernetes | Pending |
| K8S-03 | Phase 6 - Kubernetes | Pending |
| K8S-04 | Phase 6 - Kubernetes | Pending |
| K8S-05 | Phase 6 - Kubernetes | Pending |
| K8S-06 | Phase 6 - Kubernetes | Pending |
| K8S-07 | Phase 6 - Kubernetes | Pending |

**Coverage:**
- v1 requirements: 63 total (added DRV-01, DRV-02, KONG-07/drivers, DATA-02/driver seed; container count 18; Scenario 3 Phase A/B flow corrected)
- Mapped to phases: 63
- Unmapped: 0 ✓

---
*Requirements defined: 2026-03-13*
*Last updated: 2026-03-13 — conflicts resolved against proposal PDF*
*Last updated: 2026-03-13 after roadmap creation*
