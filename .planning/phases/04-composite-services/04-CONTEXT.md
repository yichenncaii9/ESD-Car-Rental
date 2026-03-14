# Phase 4: Composite Services - Context

**Gathered:** 2026-03-15
**Status:** Ready for planning

<domain>
## Phase Boundary

Implement the four composite Flask services (book_car, cancel_booking, report_issue, resolve_issue) by replacing Phase 1 stubs with real orchestration logic. Each composite calls atomic services + external wrappers via HTTP to complete the three user-facing scenarios. Async worker processing (Twilio SMS, activity_log) is Phase 5 — Phase 4 only publishes to RabbitMQ.

</domain>

<decisions>
## Implementation Decisions

### Wrapper implementations
- All three external wrappers use **real APIs in test/sandbox mode**: Stripe (test key), OpenAI (GPT call), Google Maps (reverse geocoding)
- API keys passed via environment variables in `.env` (already in .gitignore): `STRIPE_SECRET_KEY`, `OPENAI_API_KEY`, `GOOGLE_MAPS_API_KEY`
- **Each wrapper owns its own external SDK call** — composites never import stripe/openai/twilio directly; they POST to wrapper HTTP endpoints
- **Mock failover pattern** for stripe_wrapper (and ask user about openai_wrapper and twilio_wrapper when planning Phase 5): `try: real API call → except: return mock response with {"provider": "fallback", "intent_id": f"mock_{uuid.uuid4().hex}"}`. Same response shape either way — composite is unaware of which provider was used. Documents PSP failover architecture for markers.

### book_car orchestration order + failure modes
- **Step order**: validate driver → lock vehicle to "rented" → charge Stripe → create booking → return 201
- Lock vehicle **before** Stripe charge to prevent double-booking race condition
- Driver validation failure → **400** with upstream reason exposed (e.g. `{"status": "error", "message": "license expired"}`)
- Vehicle not available → **409 Conflict** `{"status": "error", "message": "Vehicle not available"}`
- Stripe charge failure → unlock vehicle, return 500 (no booking created)
- Stripe succeeds but booking_service fails → **best-effort rollback**: refund Stripe + unlock vehicle; if rollback itself fails, log it and still return 500
- Success → **201 Created** with `{ booking_id, status: "confirmed", payment_intent_id }`

### cancel_booking refund logic
- Fetch booking from booking_service; reject with 400 if already cancelled or status is not "confirmed"
- Compute hours before pickup: `(pickup_datetime - now).total_seconds() / 3600`
- Apply policy tiers from `GET /api/pricing/policy`: >24h → 100%, 1–24h → 50%, <1h → 0%
- Call stripe_wrapper refund, then set booking status "cancelled" + vehicle status "available"
- If Stripe refund fails: still cancel booking, set `refund_status: "pending_manual"` on booking document in Firestore
- Response (COMP-07): `{ booking_id, status: "cancelled", refund_amount, refund_status }` — refund_status is "processed" or "pending_manual"

### report_issue Phase A + B
- **Phase A (sync, in order)**: googlemaps_wrapper reverse geocode → openai_wrapper severity classify → report_service persist (one write with address + severity already known) → publish to RabbitMQ → return response
- **Phase B is inline** (not threaded) — RabbitMQ publish is fast (milliseconds); no reason to thread
- RabbitMQ message payload: full fields — `report_id, booking_id, vehicle_id, user_uid, severity, location, description` — so Phase 5 workers don't need to re-query Firestore
- If RabbitMQ publish fails: log server-side, return Phase A response anyway (report already persisted)
- Return: `{ report_id, status: "submitted", severity }`

### resolve_issue failure handling
- Call report_service to update resolution, then call twilio_wrapper to SMS driver
- If Twilio fails: update report with `sms_status: "unsent"` field (stored on report document), return success with sms_status flagged
- If Twilio succeeds: `sms_status: "sent"`

### Rollback philosophy
- Best-effort rollback throughout — log failures, never silently swallow
- Rollback failures are logged server-side; caller always gets 500 (never a misleading 200)
- `refund_status` and `sms_status` fields on Firestore documents are the audit trail for manual follow-up

### Claude's Discretion
- Exact inter-service call timeout values
- Exact RabbitMQ connection/channel setup pattern within report_issue
- googlemaps_wrapper route path and request/response shape (not yet defined)
- openai_wrapper prompt wording for severity classification

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- All 4 composite `app.py` stubs: identical Flask+CORS+Firestore-init scaffold — replace single route body only
- `requests` already in `composite/book_car/requirements.txt` — use for all inter-service HTTP calls
- stripe_wrapper: `POST /api/stripe/charge → { payment_intent_id }`, `POST /api/stripe/refund → { refund_id }`
- openai_wrapper: `POST /api/openai/evaluate → { severity }`
- atomic service ports: vehicle=5001, booking=5002, driver=5003, report=5004, pricing=5005

### Established Patterns
- Inter-service HTTP: `requests.post(f"http://{SERVICE_HOST}/api/...", json=body, timeout=5)`
- Error passthrough: check `r.status_code`, raise/return error with upstream message if non-2xx
- `{ "status": "error", "message": "..." }` shape on all error responses (locked in Phase 3)
- Booking required fields: `user_uid, vehicle_id, vehicle_type, pickup_datetime, hours, total_price, stripe_payment_intent_id`

### Integration Points
- Composite services: ports 6001–6004 (book_car, cancel_booking, report_issue, resolve_issue)
- All composite routes already registered in Kong (Phase 1) — no new Kong config needed
- RabbitMQ exchange "report_topic", routing key "report.new" — already declared in Phase 1

</code_context>

<specifics>
## Specific Ideas

- stripe_wrapper mock failover: `try: real Stripe call → except: {"provider": "fallback", "intent_id": f"mock_{uuid.uuid4().hex}"}` — document in README as "PSP failover (Stripe primary → mock secondary)" for markers
- Lock vehicle before Stripe charge specifically to prevent the double-booking race condition
- googlemaps → openai → report_service order ensures report document is written once, complete

</specifics>

<deferred>
## Deferred Ideas

- None — discussion stayed within Phase 4 scope

</deferred>

---

*Phase: 04-composite-services*
*Context gathered: 2026-03-15*
