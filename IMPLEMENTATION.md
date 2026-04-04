# ESD Car Rental — Implementation Reference

## Verified Architecture (as-coded)

> Corrections vs. original description:
> - **Twilio replaced** by SMU OutSystems Swagger API (`smuedu-dev.outsystemsenterprise.com/.../SendSMS`)
> - `driver_service` is port **5003** (not 5006)
> - `activity_log` is a pure AMQP worker — no HTTP port, writes directly to Firestore
> - `stripe_wrapper` is port **6202**, `openai_wrapper` **6200**, `googlemaps_wrapper` **6201**, `notification_wrapper` HTTP **6203**
> - `book_car` orchestrates **5** services (driver + vehicle + pricing + stripe + booking), not 4
> - Two SMS paths exist: **async** (workers→SMU) for new incidents, **sync** (HTTP wrapper→SMU) for resolutions

---

## Port Map

```
FRONTEND
  Vue.js (Vite)          :8080

API GATEWAY
  Kong (DB-less)         :8000  →  routes to composites

COMPOSITE SERVICES
  book_car               :6001
  cancel_booking         :6002
  report_issue           :6003
  resolve_issue          :6004

WEBSOCKET SERVER
  websocket_server       :6100  (Flask-SocketIO)

ATOMIC SERVICES
  vehicle_service        :5001
  booking_service        :5002
  driver_service         :5003
  report_service         :5004
  pricing_service        :5005

WRAPPER SERVICES (HTTP)
  openai_wrapper         :6200
  googlemaps_wrapper     :6201
  stripe_wrapper         :6202
  notification_wrapper   :6203  ← SMU Swagger API (replaces Twilio)

WORKERS (AMQP only, no HTTP port)
  notification_wrapper   (worker) — consumes notification_queue
  activity_log           (worker) — consumes activity_queue

INFRASTRUCTURE
  rabbitmq               :5672 (AMQP), :15672 (mgmt)
  Kong                   :8000 (proxy), :8001 (admin)
```

---

## Service Interaction Diagrams

### S1 — Book Car (`POST /api/book-car`)

```
Vue.js
  │  POST /api/book-car  (JWT in header)
  ▼
Kong :8000
  │  validates JWT (RS256, Firebase public key)
  │  rate-limits (60 req/min)
  ▼
book_car :6001
  │
  ├─ 1. GET  driver_service:5003  /api/drivers/{user_uid}
  │         → fetch driver record, extract license_number
  │
  ├─ 2. POST driver_service:5003  /api/drivers/validate
  │         → validate license (expiry, suspension)
  │
  ├─ 3. GET  vehicle_service:5001  /api/vehicles/{vehicle_id}
  │         → check status == "available"
  │
  ├─ 4. PUT  vehicle_service:5001  /api/vehicles/{vehicle_id}/status  {"status":"rented"}
  │         → lock vehicle (prevent double-booking)
  │
  ├─ 5. GET  pricing_service:5005  /api/pricing/calculate?vehicle_type=&hours=
  │         → compute total_price
  │         [rollback: PUT vehicle → "available" on failure]
  │
  ├─ 6. POST stripe_wrapper:6202  /api/stripe/charge  {"amount":..., "currency":"sgd"}
  │         → create payment intent, get payment_intent_id
  │         [rollback: PUT vehicle → "available" on failure]
  │
  └─ 7. POST booking_service:5002  /api/bookings
            → create booking record
            [rollback on failure: POST stripe/refund + PUT vehicle → "available"]

  Returns: { booking_id, payment_intent_id, status:"confirmed" }
```

---

### S2 — Cancel Booking (`POST /api/cancel-booking`)

```
Vue.js
  │  POST /api/cancel-booking  (JWT in header)
  ▼
Kong :8000
  ▼
cancel_booking :6002
  │
  ├─ 1. GET  booking_service:5002  /api/bookings/{booking_id}
  │         → fetch booking, verify status == "confirmed"
  │
  ├─ 2. [local] compute hours_before_pickup from pickup_datetime
  │
  ├─ 3. GET  pricing_service:5005  /api/pricing/policy
  │         → fetch cancellation tiers
  │         → calculate refund_percent (e.g. >24h → 100%, else 0%)
  │
  ├─ 4. POST stripe_wrapper:6202  /api/stripe/refund
  │         → issue refund (if refund_amount > 0)
  │         → on failure: marks refund_status = "pending_manual" in Firestore directly
  │
  ├─ 5. PUT  booking_service:5002  /api/bookings/{booking_id}/status  {"status":"cancelled"}
  │
  └─ 6. PUT  vehicle_service:5001  /api/vehicles/{vehicle_id}/status  {"status":"available"}

  Returns: { booking_id, status:"cancelled", refund_amount, refund_status }
```

---

### S3 — Report Issue (`POST /api/report-issue`)

Two-phase design: Phase A (sync HTTP chain) + Phase B (async AMQP fan-out)

```
Vue.js
  │  POST /api/report-issue  (JWT in header)
  ▼
Kong :8000
  ▼
report_issue :6003
  │
  │  ── PHASE A (synchronous) ──────────────────────────────────
  │
  ├─ 1. GET  booking_service:5002  /api/bookings/{booking_id}
  │         → validate booking exists
  │
  ├─ 2. POST googlemaps_wrapper:6201  /api/maps/geocode  {"lat":..., "lng":...}
  │         → reverse-geocode coordinates → human-readable address
  │         [fallback: use raw "lat,lng" string on failure]
  │
  ├─ 3. POST openai_wrapper:6200  /api/openai/evaluate  {"description":..., "address":...}
  │         → OpenAI Vision API → severity classification (low/medium/high)
  │         [fallback: severity = "medium" on failure]
  │
  ├─ 4. POST report_service:5004  /api/reports
  │         → persist report record → returns report_id
  │
  ├─ 5. PUT  report_service:5004  /api/reports/{report_id}/evaluation  {"severity":...}
  │         → attach severity to report
  │
  │  ── PHASE B (async, non-blocking) ──────────────────────────
  │
  └─ 6. PUBLISH → RabbitMQ  exchange="report_topic"  routing_key="report.new"
            payload: { report_id, booking_id, vehicle_id, user_uid, severity, location, description }

  Returns immediately (Phase A): { report_id, status:"submitted", severity }

  ── RabbitMQ fan-out ─────────────────────────────────────────

  report_topic (topic exchange)
    │
    ├─ routing_key "report.new" → notification_queue
    │     ▼
    │   notification_wrapper (WORKER)
    │     ├─ POST SMU SMS API → service team phone numbers
    │     │   https://smuedu-dev.outsystemsenterprise.com/.../SendSMS
    │     └─ POST websocket_server:6100  /notify  → emit "report_update" to frontend
    │
    └─ routing_key "report.new" → activity_queue
          ▼
        activity_log (WORKER)
          ├─ WRITE Firestore "activity_log" collection
          └─ POST websocket_server:6100  /notify  → emit "report_update" to frontend
```

---

### S4 — Resolve Issue (`POST /api/resolve-issue`)

```
Vue.js (admin/staff)
  │  POST /api/resolve-issue  (JWT in header)
  ▼
Kong :8000
  ▼
resolve_issue :6004
  │
  ├─ 1. PUT  report_service:5004  /api/reports/{report_id}/resolution  {"resolution":...}
  │         → mark report as resolved
  │
  └─ 2. POST notification_wrapper:6203  /api/notification/sms  {"to": driver_phone, "body":...}
            → notification_wrapper (HTTP wrapper) → SMU Swagger SMS API
            → on failure: marks sms_status = "unsent" in Firestore directly

  Returns: { report_id, status:"resolved", sms_status }
```

---

## Full System Connectivity Map

```
                        ┌─────────────────────────────────────────────────────┐
                        │               EXTERNAL SERVICES                      │
                        │  Firebase Auth   Firestore   OpenAI   Stripe   SMU  │
                        └────┬────────────────┬──────────┬────────┬──────┬───┘
                             │                │          │        │      │
┌─────────┐    JWT     ┌─────▼──────┐        │          │        │      │
│ Vue.js  │──────────►│   Kong     │        │          │        │      │
│ :8080   │◄──────────│   :8000    │        │          │        │      │
└─────────┘  response  └─────┬──────┘        │          │        │      │
  ▲ WebSocket                │               │          │        │      │
  │                   ┌──────┴───────┐       │          │        │      │
  │             ┌─────┴──┐    ┌──────┴──┐    │          │        │      │
  │             │book_car│    │cancel   │    │          │        │      │
  │             │ :6001  │    │_booking │    │          │        │      │
  │             └───┬────┘    │ :6002   │    │          │        │      │
  │                 │         └────┬────┘    │          │        │      │
  │          ┌──────┴──┐    ┌──────┴──┐     │          │        │      │
  │          │report   │    │resolve  │     │          │        │      │
  │          │_issue   │    │_issue   │     │          │        │      │
  │          │ :6003   │    │ :6004   │     │          │        │      │
  │          └────┬────┘    └────┬────┘     │          │        │      │
  │               │              │           │          │        │      │
  │    ┌──────────┼──────────────┼───┐       │          │        │      │
  │    │          │   ATOMICS    │   │       │          │        │      │
  │    │  ┌───────▼──┐ ┌────────▼─┐ │       │          │        │      │
  │    │  │vehicle   │ │booking   │ │       │          │        │      │
  │    │  │_service  │ │_service  │ │       │          │        │      │
  │    │  │ :5001    │ │ :5002    │ │       │          │        │      │
  │    │  └──────────┘ └──────────┘ │       │          │        │      │
  │    │  ┌──────────┐ ┌──────────┐ │       │          │        │      │
  │    │  │driver    │ │report    │ │       │          │        │      │
  │    │  │_service  │ │_service  │ │       │          │        │      │
  │    │  │ :5003    │ │ :5004    │ │       │          │        │      │
  │    │  └──────────┘ └──────────┘ │       │          │        │      │
  │    │  ┌──────────┐              │       │          │        │      │
  │    │  │pricing   │              │       │          │        │      │
  │    │  │_service  │              │       │          │        │      │
  │    │  │ :5005    │              │       │          │        │      │
  │    │  └──────────┘              │       │          │        │      │
  │    └────────────────────────────┘       │          │        │      │
  │                                         │          │        │      │
  │         WRAPPERS (HTTP)                 │          │        │      │
  │    ┌────────────────────────────────────┘          │        │      │
  │    │ openai_wrapper:6200 ──────────────────────────┘        │      │
  │    │ googlemaps_wrapper:6201 ── Google Maps API             │      │
  │    │ stripe_wrapper:6202 ───────────────────────────────────┘      │
  │    │ notification_wrapper:6203 ─────────────────────────────────── ┘
  │    └────────────────────────────────────┐
  │                                         │
  │         AMQP                            │
  │    report_issue:6003 ─PUBLISH──► RabbitMQ (report_topic exchange)
  │                                         │
  │                              ┌──────────┴────────────┐
  │                              │                       │
  │                    notification_queue        activity_queue
  │                              │                       │
  │                    notification_wrapper      activity_log
  │                    (WORKER)                  (WORKER)
  │                         │                       │
  │                         │── SMS via SMU API      │── Firestore write
  │                         │                       │
  └─────────────────── websocket_server:6100 ◄──────┘
                       Flask-SocketIO
                       POST /notify → emit "report_update"
```

---

## Data Stores per Service

| Service | Store | Collection / Notes |
|---|---|---|
| vehicle_service | Firestore | `vehicles` |
| booking_service | Firestore | `bookings` |
| driver_service | Firestore | `drivers` |
| report_service | Firestore | `reports` |
| pricing_service | OutSystems | hosted externally; Flask stub for local dev |
| activity_log (worker) | Firestore | `activity_log` |
| cancel_booking (composite) | Firestore | direct write for `refund_status:"pending_manual"` |
| resolve_issue (composite) | Firestore | direct write for `sms_status:"unsent"` |

---

## Kong JWT Validation

- Algorithm: **RS256**
- Firebase issues tokens with `iss = https://securetoken.google.com/{PROJECT_ID}`
- Kong matches `kid` in token header → consumer `firebase-frontend` → looks up `jwt_secrets.key`
- Keys rotate every ~7 days — update `rsa_public_key` in `kong.yml` when `401 Invalid signature` appears
- Rate limit: **60 req/min** per route (local policy)

---

## SMS Notification — Two Paths

| Trigger | Path | Provider |
|---|---|---|
| New incident reported (S3) | report_issue → RabbitMQ → notification_wrapper **worker** | SMU OutSystems Swagger API |
| Issue resolved (S4) | resolve_issue → notification_wrapper **HTTP wrapper** (:6203) | SMU OutSystems Swagger API |

Both fall back to a mock UUID response if the SMU API is unreachable.
