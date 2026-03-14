# Phase 3: Atomic Services - Context

**Gathered:** 2026-03-14
**Status:** Ready for planning

<domain>
## Phase Boundary

Replace the Phase 1 stubs in all 5 atomic services (vehicle_service, booking_service, driver_service, report_service, pricing_service) with real Firestore read/write logic. Every documented REST endpoint must be functional and tested against Firestore. Composite service orchestration is out of scope — that's Phase 4.

</domain>

<decisions>
## Implementation Decisions

### Booking data model
- Time/duration stored as `pickup_datetime` (ISO timestamp) + `hours` (numeric) — no `return_datetime` field; simpler math for pricing (hourly rates already known)
- `stripe_payment_intent_id` stored at booking creation time — composite charges Stripe first, then POSTs to booking_service with the intent ID included in the body
- Booking status lifecycle: `confirmed` → `cancelled` or `completed` (three states only)
- Firestore collection: `bookings`
- Required POST /bookings body fields: `user_uid`, `vehicle_id`, `vehicle_type`, `pickup_datetime`, `hours`, `total_price`, `stripe_payment_intent_id`

### Firestore document IDs
- Booking and report documents use Firestore **auto-generated IDs** via `.add()` — not caller-provided
- POST /bookings returns `{ booking_id, status, message }` — composite stores the returned ID for follow-up calls
- POST /reports returns `{ report_id, status, message }` — same pattern; report_issue composite returns `report_id` to frontend (per COMP-10)
- Existing collections use natural keys: `vehicles` (doc ID = plate_number), `drivers` (doc ID = license_number)

### Cancellation policy endpoint (pricing_service)
- New endpoint: `GET /api/pricing/policy` — added to pricing_service (no new Kong route needed; existing /api/pricing route covers all sub-paths)
- Returns machine-readable tiered refund policy:
  ```json
  {
    "tiers": [
      { "hours_before": 24, "refund_percent": 100 },
      { "hours_before": 1, "refund_percent": 50 },
      { "hours_before": 0, "refund_percent": 0 }
    ]
  }
  ```
- cancel_booking composite (Phase 4) calls this endpoint, computes refund amount itself using `hours_before` pickup

### HTTP error format
- Standard HTTP status codes — never return 200 with an error body
- Consistent error body shape across all services:
  - `404` → `{ "status": "error", "message": "Booking not found" }`
  - `400` → `{ "status": "error", "message": "Missing required field: uid" }`
  - `500` → `{ "status": "error", "message": "<exception detail>" }` (full exception exposed for debugging)
- Success responses keep the existing `{ "status": "ok", "data": ... }` shape from stubs

### Driver validation logic
- `POST /api/drivers/validate` checks two conditions:
  1. Driver record exists in Firestore (by `license_number`)
  2. `license_expiry` date is in the future
- Returns `{ valid: false, reason: "driver not found" }` or `{ valid: false, reason: "license expired" }` on failure
- Returns `{ valid: true }` on success

### Claude's Discretion
- Exact Firestore field names for report documents (report_id, booking_id, vehicle_id, location, description, severity, status, created_at, resolved_at)
- `GET /api/reports/pending` filter — reports where `status` is not "resolved" (or equivalent field Claude determines)
- `GET /api/pricing/calculate` query param names (`vehicle_type`, `hours`) and rounding behavior
- `GET /api/vehicles` filter behavior — return all vehicles or only `status == "available"` (Claude's call based on frontend needs)
- Error messages exact wording

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- All 5 `app.py` stubs: Firestore init pattern with try/except already in place — just replace stub route bodies with real logic
- `seed_data.py`: Defines exact vehicle and driver field schemas — use these as the Firestore document shape for read responses
- `atomic/vehicle_service/requirements.txt`: `flask>=3.0, flask-cors, firebase-admin, requests` — same requirements.txt for all Firestore services; pricing_service can drop `firebase-admin` and `requests`

### Established Patterns
- Firestore init: `credentials.Certificate(os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "/secrets/firebase-service-account.json"))` + `firebase_admin.initialize_app(cred)` + `db = fs.client()`
- Flask app pattern: `Flask(__name__)`, `CORS(app)`, routes at `/api/<resource>`, `app.run(host="0.0.0.0", port=int(os.environ.get("PORT", XXXX)))`
- All routes use `flask.request` for body/query params; response via `flask.jsonify()`
- Collection access: `db.collection("vehicles").document(plate_number).get()` — same pattern for bookings/reports with auto-IDs

### Integration Points
- Phase 4 composites call atomic services via HTTP (using invokes.py pattern from PlaceOrder)
- `booking_service` is the most-called atomic service — COMP-01, COMP-03, COMP-05 all depend on it
- `pricing_service GET /api/pricing/policy` is new — cancel_booking composite (COMP-04) will call it
- `driver_service POST /api/drivers/validate` is called first in book_car flow (COMP-01) — must return quickly

</code_context>

<specifics>
## Specific Ideas

- stripe_payment_intent_id is stored at booking creation (composite charges Stripe → then creates booking with intent ID already known)
- Driver validation is strict: both record existence AND license expiry are checked — expired license = rejected booking
- Cancellation policy tiers are a machine-readable list so Phase 4 composite can iterate without hardcoding thresholds

</specifics>

<deferred>
## Deferred Ideas

- None — discussion stayed within Phase 3 scope

</deferred>

---

*Phase: 03-atomic-services*
*Context gathered: 2026-03-14*
