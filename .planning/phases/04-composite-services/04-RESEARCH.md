# Phase 4: Composite Services - Research

**Researched:** 2026-03-15
**Domain:** Flask composite service orchestration, Stripe/OpenAI/Google Maps SDK integration, pika RabbitMQ publish
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Wrapper implementations**
- All three external wrappers use real APIs in test/sandbox mode: Stripe (test key), OpenAI (GPT call), Google Maps (reverse geocoding)
- API keys passed via environment variables in `.env` (already in .gitignore): `STRIPE_SECRET_KEY`, `OPENAI_API_KEY`, `GOOGLE_MAPS_API_KEY`
- Each wrapper owns its own external SDK call — composites never import stripe/openai/twilio directly; they POST to wrapper HTTP endpoints
- Mock failover pattern for stripe_wrapper: `try: real API call → except: return mock response with {"provider": "fallback", "intent_id": f"mock_{uuid.uuid4().hex}"}`. Same response shape either way.

**book_car orchestration order + failure modes**
- Step order: validate driver → lock vehicle to "rented" → charge Stripe → create booking → return 201
- Lock vehicle before Stripe charge to prevent double-booking race condition
- Driver validation failure → 400 with upstream reason exposed
- Vehicle not available → 409 Conflict
- Stripe charge failure → unlock vehicle, return 500 (no booking created)
- Stripe succeeds but booking_service fails → best-effort rollback: refund Stripe + unlock vehicle; if rollback itself fails, log it and still return 500
- Success → 201 Created with `{ booking_id, status: "confirmed", payment_intent_id }`

**cancel_booking refund logic**
- Fetch booking from booking_service; reject with 400 if already cancelled or status is not "confirmed"
- Compute hours before pickup: `(pickup_datetime - now).total_seconds() / 3600`
- Apply policy tiers from `GET /api/pricing/policy`: >24h → 100%, 1–24h → 50%, <1h → 0%
- Call stripe_wrapper refund, then set booking status "cancelled" + vehicle status "available"
- If Stripe refund fails: still cancel booking, set `refund_status: "pending_manual"` on booking document in Firestore
- Response (COMP-07): `{ booking_id, status: "cancelled", refund_amount, refund_status }`

**report_issue Phase A + B**
- Phase A (sync, in order): googlemaps_wrapper reverse geocode → openai_wrapper severity classify → report_service persist → publish to RabbitMQ → return response
- Phase B is inline (not threaded) — RabbitMQ publish is fast (milliseconds)
- RabbitMQ message payload: full fields — `report_id, booking_id, vehicle_id, user_uid, severity, location, description`
- If RabbitMQ publish fails: log server-side, return Phase A response anyway
- Return: `{ report_id, status: "submitted", severity }`

**resolve_issue failure handling**
- Call report_service to update resolution, then call twilio_wrapper to SMS driver
- If Twilio fails: update report with `sms_status: "unsent"` field, return success with sms_status flagged
- If Twilio succeeds: `sms_status: "sent"`

**Rollback philosophy**
- Best-effort rollback throughout — log failures, never silently swallow
- Rollback failures are logged server-side; caller always gets 500
- `refund_status` and `sms_status` fields on Firestore documents are the audit trail

### Claude's Discretion
- Exact inter-service call timeout values
- Exact RabbitMQ connection/channel setup pattern within report_issue
- googlemaps_wrapper route path and request/response shape (not yet defined — currently stub at `POST /api/maps/geocode`)
- openai_wrapper prompt wording for severity classification

### Deferred Ideas (OUT OF SCOPE)
- None — discussion stayed within Phase 4 scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| COMP-01 | book_car POST /book-car orchestrates driver_service → vehicle_service → pricing_service → booking_service → stripe_wrapper and returns confirmed booking | Covered by atomic service API audit + orchestration pattern |
| COMP-02 | book_car handles Stripe payment failure with vehicle unlock + booking cancellation rollback | Covered by rollback pattern + stripe_wrapper mock failover |
| COMP-03 | cancel_booking POST /cancel-booking fetches booking and rejects if status is active trip or already cancelled | Covered by booking_service API audit (PUT /bookings/<id>/status) |
| COMP-04 | cancel_booking calculates refund amount via pricing_service cancellation policy | Covered by pricing_service GET /pricing/policy tiers |
| COMP-05 | cancel_booking calls stripe_wrapper refund, sets booking status "cancelled", vehicle status "available" | Covered by stripe/vehicle/booking API audit |
| COMP-06 | cancel_booking handles Stripe refund failure — booking cancelled, refund flagged "pending_manual" | Covered by Firestore partial-update pattern |
| COMP-07 | cancel_booking returns `{ booking_id, status, refund_amount, refund_status }` | Locked response shape |
| COMP-08 | report_issue Phase A: booking check → googlemaps_wrapper → openai_wrapper → report_service persist | Covered by wrapper stub audit + report_service schema |
| COMP-09 | report_issue Phase B: publish to RabbitMQ "report_topic" exchange with key "report.new" | Covered by pika publish pattern |
| COMP-10 | report_issue returns `{ report_id, status: "submitted", severity }` after Phase A | Locked response shape |
| COMP-11 | resolve_issue calls report_service → twilio_wrapper SMS; handles Twilio failure gracefully | Covered by report_service resolution endpoint + twilio wrapper stub |
</phase_requirements>

---

## Summary

Phase 4 replaces four Flask stub `app.py` files with real orchestration logic, and upgrades three wrapper stubs (stripe_wrapper, openai_wrapper, googlemaps_wrapper) from Phase 1 placeholders to real SDK calls with mock failover. All atomic service HTTP APIs are already complete from Phase 3 and verified via smoke tests. The composite services call those APIs using `requests` (already in all `requirements.txt`) with a consistent `requests.post/put/get(url, json=body, timeout=N)` pattern and check `r.status_code` for non-2xx errors.

The RabbitMQ publish in `report_issue` is inline (no threading) using `pika` with a direct connection, `channel.basic_publish()` on the `report_topic` exchange with routing key `report.new`. The `pika` library is not yet in `composite/report_issue/requirements.txt` and must be added. The twilio_wrapper in Phase 4 scope is only called via HTTP by `resolve_issue` — its AMQP consumer role is Phase 5. However, the `twilio_wrapper` currently lives under `workers/` (AMQP consumer stub) — Phase 4 requires a separate HTTP Flask wrapper for the SMS call from `resolve_issue`. This is a gap to resolve.

The mock failover pattern (Stripe primary → mock PSP fallback) must be documented in stripe_wrapper's README as "PSP failover architecture" for academic markers. The same try/except pattern applies to openai_wrapper and googlemaps_wrapper per Claude's Discretion.

**Primary recommendation:** Implement composites in this order — stripe_wrapper (real SDK + mock failover) → openai_wrapper → googlemaps_wrapper → book_car → cancel_booking → report_issue → resolve_issue. Add pika to report_issue requirements. Resolve the twilio_wrapper HTTP endpoint gap before resolve_issue implementation.

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| flask | >=3.0 | HTTP server for composite services | Already in all `requirements.txt` |
| flask-cors | latest | CORS headers | Already in all `requirements.txt` |
| requests | latest | Inter-service HTTP calls | Already in all composite `requirements.txt` |
| stripe | latest | Stripe Python SDK (stripe_wrapper only) | Official SDK, test mode support |
| openai | latest | OpenAI Python SDK (openai_wrapper only) | Official SDK |
| googlemaps | latest | Google Maps Python client (googlemaps_wrapper only) | Official client library |
| pika | latest | RabbitMQ publish via AMQP (report_issue composite) | Already in workers `requirements.txt` |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| uuid | stdlib | Generate mock intent IDs in failover branches | Inside wrapper mock fallback |
| datetime | stdlib | Pickup time delta calculation in cancel_booking | Refund tier computation |
| firebase-admin | latest | Firestore audit field updates (refund_status, sms_status) | Direct Firestore writes not needed — atomic services handle persistence; composites call atomics via HTTP |

**Note:** Composites do NOT directly write to Firestore in normal flow — they call atomic service HTTP endpoints. The only exception is if a direct Firestore patch is needed for `refund_status`/`sms_status` fields on booking/report documents, since the atomic service `PUT /bookings/<id>/status` only updates `status` (not arbitrary fields). See Architecture Patterns for the resolution.

### Installation additions needed

```bash
# stripe_wrapper — add to wrappers/stripe_wrapper/requirements.txt
stripe

# openai_wrapper — add to wrappers/openai_wrapper/requirements.txt
openai

# googlemaps_wrapper — add to wrappers/googlemaps_wrapper/requirements.txt
googlemaps

# report_issue composite — add to composite/report_issue/requirements.txt
pika
```

---

## Architecture Patterns

### Composite Service Structure

Each composite replaces only the route handler body. The Flask + CORS + Firestore-init scaffold is reused as-is. The Firestore client (`db`) is available in all four composites from Phase 1 scaffold — useful for direct Firestore partial updates (e.g., setting `refund_status` on a booking document when the atomic booking service's `PUT /status` endpoint doesn't support that field).

### Docker Compose Service Hostnames

All inter-service HTTP calls inside Docker use container_name as hostname:

| Target | Docker Hostname | Port |
|--------|----------------|------|
| vehicle_service | `vehicle_service` | 5001 |
| booking_service | `booking_service` | 5002 |
| driver_service | `driver_service` | 5003 |
| report_service | `report_service` | 5004 |
| pricing_service | `pricing_service` | 5005 |
| stripe_wrapper | `stripe_wrapper` | 6202 |
| openai_wrapper | `openai_wrapper` | 6200 |
| googlemaps_wrapper | `googlemaps_wrapper` | 6201 |
| twilio_wrapper | see gap note | — |
| websocket_server | `websocket_server` | 6100 |
| rabbitmq | `rabbitmq` | 5672 |

Service host env vars should be configurable so tests can override. Recommended pattern:
```python
VEHICLE_HOST = os.environ.get("VEHICLE_SERVICE_HOST", "vehicle_service:5001")
```

### Pattern 1: Inter-Service HTTP Call with Error Passthrough

```python
import requests

def call_service(url, method="post", json_body=None, timeout=5):
    try:
        if method == "post":
            r = requests.post(url, json=json_body, timeout=timeout)
        elif method == "put":
            r = requests.put(url, json=json_body, timeout=timeout)
        else:
            r = requests.get(url, timeout=timeout)
        if r.status_code >= 400:
            return None, r.status_code, r.json().get("message", "upstream error")
        return r.json(), r.status_code, None
    except requests.exceptions.RequestException as e:
        return None, 503, str(e)
```

### Pattern 2: Mock Failover Wrapper (stripe_wrapper example)

```python
import stripe
import uuid

stripe.api_key = os.environ.get("STRIPE_SECRET_KEY")

@app.route("/api/stripe/charge", methods=["POST"])
def charge():
    body = request.get_json(silent=True) or {}
    amount_cents = int(float(body.get("amount", 0)) * 100)
    currency = body.get("currency", "sgd")
    try:
        intent = stripe.PaymentIntent.create(
            amount=amount_cents,
            currency=currency,
            payment_method=body.get("payment_method", "pm_card_visa"),
            confirm=True,
            automatic_payment_methods={"enabled": True, "allow_redirects": "never"},
        )
        return jsonify({"status": "ok", "payment_intent_id": intent.id, "provider": "stripe"}), 200
    except Exception as e:
        print(f"[stripe_wrapper] Stripe API failed, using mock fallback: {e}")
        mock_id = f"mock_{uuid.uuid4().hex}"
        return jsonify({"status": "ok", "payment_intent_id": mock_id, "provider": "fallback"}), 200
```

Apply the same `try: real SDK → except: return mock` pattern to `openai_wrapper` and `googlemaps_wrapper`.

### Pattern 3: book_car Orchestration (COMP-01, COMP-02)

```
POST /api/book-car
  body: { user_uid, vehicle_id, vehicle_type, pickup_datetime, hours }

1. POST driver_service /api/drivers/validate { license_number }
   → valid=False  → 400 with reason
2. GET  vehicle_service /api/vehicles/<vehicle_id>
   → status != "available" → 409
3. PUT  vehicle_service /api/vehicles/<vehicle_id>/status { status: "rented" }
4. GET  pricing_service /api/pricing/calculate?vehicle_type=&hours=
5. POST stripe_wrapper  /api/stripe/charge { amount, currency }
   → failure → PUT vehicle status "available" → 500
6. POST booking_service /api/bookings { user_uid, vehicle_id, vehicle_type,
                                        pickup_datetime, hours, total_price,
                                        stripe_payment_intent_id }
   → failure → POST stripe_wrapper /api/stripe/refund (best-effort)
             → PUT vehicle status "available" (best-effort)
             → 500
7. return 201 { booking_id, status: "confirmed", payment_intent_id }
```

**Driver validation note:** `driver_service POST /api/drivers/validate` requires `license_number` in the body. The composite must fetch the driver's license number first using `GET /api/drivers/<uid>` before calling validate. The `user_uid` is in the JWT (or passed in request body).

### Pattern 4: cancel_booking Orchestration (COMP-03 through COMP-07)

```
POST /api/cancel-booking
  body: { booking_id }

1. GET  booking_service /api/bookings/<booking_id>
   → not found → 404
   → status != "confirmed" → 400 {"message": "booking already cancelled or not confirmed"}
2. Compute hours_before_pickup from booking pickup_datetime vs utcnow()
3. GET  pricing_service /api/pricing/policy → tiers
   Apply tier: hours>24→100%, 1<hours<=24→50%, hours<=1→0%
   refund_amount = total_price * (percent / 100)
4. POST stripe_wrapper /api/stripe/refund { payment_intent_id, amount: refund_amount }
   → success: refund_status = "processed"
   → failure: refund_status = "pending_manual"
             (log error server-side)
5. PUT  booking_service /api/bookings/<booking_id>/status { status: "cancelled" }
6. If refund_status == "pending_manual":
     db.collection("bookings").document(booking_id).update({"refund_status": "pending_manual"})
7. GET  booking_service to find vehicle_id, then:
   PUT  vehicle_service /api/vehicles/<vehicle_id>/status { status: "available" }
8. return 200 { booking_id, status: "cancelled", refund_amount, refund_status }
```

**Key insight on `refund_status`:** The atomic `booking_service` `PUT /bookings/<id>/status` only updates the `status` field. To persist `refund_status: "pending_manual"`, the composite must use the Firestore `db` client directly (already available in scaffold) to do a partial update: `db.collection("bookings").document(booking_id).update({"refund_status": "pending_manual"})`.

### Pattern 5: report_issue Orchestration (COMP-08, COMP-09, COMP-10)

```
POST /api/report-issue
  body: { booking_id, vehicle_id, user_uid, lat, lng, description }

Phase A (sync):
1. GET  booking_service /api/bookings/<booking_id>  [optional validation]
2. POST googlemaps_wrapper /api/maps/geocode { lat, lng }
   → address string
3. POST openai_wrapper /api/openai/evaluate { description, address }
   → severity string ("low"/"medium"/"high")
4. POST report_service /api/reports {
     booking_id, vehicle_id, user_uid,
     location: address,  description, severity (update after create)
   }
   → report_id

Phase B (inline, after report created):
5. Publish to RabbitMQ:
   exchange="report_topic", routing_key="report.new"
   body=json.dumps({ report_id, booking_id, vehicle_id, user_uid,
                     severity, location: address, description })
   → failure: log, continue
6. return 200 { report_id, status: "submitted", severity }
```

**Report service schema note:** `report_service POST /api/reports` accepts: `booking_id, vehicle_id, user_uid, location, description`. It stores `severity=None` initially. The composite should call `PUT /api/reports/<id>/evaluation { severity }` after creation to update severity, OR pass severity to the create call if the service accepts extra fields (it does — `body` is used directly with `report_doc` construction, so extra fields are silently dropped). The current report_service only stores the 5 required fields + defaults. The evaluation update endpoint `PUT /reports/<id>/evaluation` is the correct way to set severity post-creation. Alternatively, consider whether the report_service should be updated to accept severity at creation time — this is simpler (one write). Check the existing schema: `report_service` creates the doc with `severity=None` then evaluation updates it. For Phase 4, the cleanest approach is: create report → immediately call evaluation endpoint to set severity. This avoids modifying the atomic service.

### Pattern 6: pika Inline Publish

```python
import pika
import json

def publish_report_event(payload: dict):
    RABBITMQ_HOST = os.environ.get("RABBITMQ_HOST", "rabbitmq")
    RABBITMQ_PORT = int(os.environ.get("RABBITMQ_PORT", 5672))
    try:
        connection = pika.BlockingConnection(
            pika.ConnectionParameters(host=RABBITMQ_HOST, port=RABBITMQ_PORT)
        )
        channel = connection.channel()
        channel.exchange_declare(exchange="report_topic", exchange_type="topic", durable=True)
        channel.basic_publish(
            exchange="report_topic",
            routing_key="report.new",
            body=json.dumps(payload),
            properties=pika.BasicProperties(delivery_mode=2),  # persistent
        )
        connection.close()
    except Exception as e:
        print(f"[report_issue] RabbitMQ publish failed: {e}")
        # Do NOT re-raise — report already persisted; Phase A response still returned
```

### Pattern 7: resolve_issue Orchestration (COMP-11)

```
POST /api/resolve-issue
  body: { report_id, resolution, driver_phone? }

1. PUT  report_service /api/reports/<report_id>/resolution { resolution }
2. POST twilio_wrapper /api/twilio/sms { to, body }   [HTTP call to wrapper]
   → success: sms_status = "sent"
   → failure: sms_status = "unsent"
              db.collection("reports").document(report_id).update({"sms_status": "unsent"})
3. return 200 { report_id, status: "resolved", sms_status }
```

### Anti-Patterns to Avoid

- **Calling Stripe/OpenAI/Twilio SDK directly from composite:** Composites only POST to wrapper HTTP endpoints — wrappers own SDK calls.
- **Threading the RabbitMQ publish:** The decision is inline publish (no threads). `pika.BlockingConnection` is correct here.
- **Swallowing rollback failures silently:** Always log rollback errors; return 500 regardless of whether rollback succeeded.
- **Using requests.get() with json= parameter:** `requests.get()` ignores `json=` body; for query params use `params=`.
- **Assuming booking status field supports extra fields via atomic PUT endpoint:** The `PUT /bookings/<id>/status` endpoint only updates `status`. Use direct Firestore `db.update()` for `refund_status` and `sms_status`.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Stripe payment intents | Custom HTTP to Stripe API | `stripe` Python SDK | Handles auth, retries, error types |
| OpenAI chat completions | Raw `requests` to OpenAI | `openai` Python SDK | Token auth, streaming, structured responses |
| Google Maps reverse geocode | Raw `requests` to Maps API | `googlemaps` Python client | Handles URL encoding, API key auth |
| RabbitMQ publish | Raw socket AMQP | `pika` | AMQP protocol complexity |
| Cancellation policy calculation | Custom time-delta logic | Simple `datetime` arithmetic + policy tiers from pricing_service | Policy tiers already served by `GET /api/pricing/policy` |

---

## Common Pitfalls

### Pitfall 1: Driver Validate Requires license_number, Not uid

**What goes wrong:** Composite calls `POST /api/drivers/validate` with `{ uid }` and gets "Missing required field: license_number".
**Why it happens:** The driver_service validate endpoint takes `license_number` as its key lookup, not `uid`. The `uid` is what the frontend passes.
**How to avoid:** Call `GET /api/drivers/<uid>` first to fetch the driver record, extract `license_number`, then call validate.
**Warning signs:** 400 from driver_service with "Missing required field: license_number" in logs.

### Pitfall 2: booking_service PUT /status Only Updates Status Field

**What goes wrong:** Composite tries to set `refund_status: "pending_manual"` via `PUT /bookings/<id>/status { status: "cancelled", refund_status: "pending_manual" }` — the extra field is ignored.
**Why it happens:** The atomic service update code is `doc_ref.update({"status": new_status})` — only `status` key is written.
**How to avoid:** Use the Firestore `db` client directly in the composite: `db.collection("bookings").document(booking_id).update({"refund_status": "pending_manual"})`. The composite scaffold already initializes `db`.
**Warning signs:** `refund_status` always null in Firestore even after failed Stripe refund.

### Pitfall 3: Vehicle ID vs Plate Number Key Inconsistency

**What goes wrong:** book_car passes `vehicle_id` as a Firestore doc ID but vehicle_service uses plate numbers (e.g., "SBA1234A") as document IDs.
**Why it happens:** Phase 3 seeded vehicles with plate numbers as doc IDs. `GET /api/vehicles` returns `id` field = doc ID = plate number.
**How to avoid:** Treat `vehicle_id` as the plate number string throughout — it is the Firestore document ID for the vehicle collection.
**Warning signs:** 404 from `GET /api/vehicles/<vehicle_id>` when a valid vehicle exists.

### Pitfall 4: pika BlockingConnection Fails if RabbitMQ Not Ready

**What goes wrong:** `pika.BlockingConnection` raises `AMQPConnectionError` if RabbitMQ is not yet healthy.
**Why it happens:** Container startup ordering — report_issue composite starts before RabbitMQ is fully up.
**How to avoid:** Wrap the entire pika block in try/except (already designed). At Phase 4, inline publish — if it fails at startup time, the report is already persisted; the publish failure is logged and ignored.
**Warning signs:** First few report_issue calls after `docker-compose up` see "RabbitMQ publish failed" in logs but return 200 correctly.

### Pitfall 5: report_service severity Field Not Set at Creation Time

**What goes wrong:** Composite creates report first (severity=None) and then updates severity — but returns the wrong severity from the create response instead of the openai response.
**Why it happens:** `report_service POST /reports` returns `{ report_id }`, not severity. Composite must track severity from openai_wrapper response and return it in the final response, not from Firestore.
**How to avoid:** Hold `severity` variable from openai_wrapper response. After `POST /reports` → call `PUT /reports/<id>/evaluation { severity }`. Return `{ report_id, status: "submitted", severity }` using the held variable.
**Warning signs:** Response shows `severity: null` instead of the AI-classified value.

### Pitfall 6: twilio_wrapper HTTP Endpoint Gap

**What goes wrong:** `resolve_issue` tries to `POST http://twilio_wrapper:PORT/api/twilio/sms` — but the twilio_wrapper in `workers/twilio_wrapper/` is an AMQP consumer stub with no HTTP server, no Flask, no port.
**Why it happens:** twilio_wrapper lives under `workers/` as a Phase 5 AMQP consumer. Phase 4 needs it as an HTTP Flask wrapper so `resolve_issue` can call it synchronously.
**How to avoid:** Phase 4 must implement twilio_wrapper as an HTTP Flask service (similar to stripe_wrapper/openai_wrapper). This may require adding a new service entry in docker-compose.yml OR implementing twilio functionality directly within resolve_issue (which violates the locked decision that "composites never import twilio directly"). The cleanest resolution: create `wrappers/twilio_wrapper/` (separate from `workers/twilio_wrapper/`) as an HTTP Flask service on a new port (e.g., 6203), with mock failover.
**Warning signs:** Cannot connect to twilio_wrapper from resolve_issue — service doesn't exist as HTTP.

### Pitfall 7: pickup_datetime Parsing for Cancellation Policy

**What goes wrong:** `(pickup_datetime - now).total_seconds()` fails because `pickup_datetime` is a string from Firestore.
**Why it happens:** Firestore stores `pickup_datetime` as the string passed in at booking creation (e.g., "2027-06-01T10:00:00").
**How to avoid:** Parse with `datetime.fromisoformat(booking["pickup_datetime"])`. Both values must be timezone-naive (UTC) or both timezone-aware. Use `datetime.utcnow()` for `now` and parse the stored string as naive ISO.
**Warning signs:** `TypeError: unsupported operand type(s) for -: 'str' and 'datetime'`.

---

## Code Examples

Verified from existing codebase:

### Existing Inter-Service Pattern (from Phase 3 context)

```python
# Established pattern in composite requirements.txt — requests already present
r = requests.post(f"http://{SERVICE_HOST}/api/...", json=body, timeout=5)
if r.status_code != 200:
    return jsonify({"status": "error", "message": r.json().get("message", "upstream error")}), r.status_code
```

### Stripe SDK Charge (sandbox/test mode)

```python
import stripe
stripe.api_key = os.environ.get("STRIPE_SECRET_KEY")

intent = stripe.PaymentIntent.create(
    amount=3750,          # amount in cents
    currency="sgd",
    confirm=True,
    payment_method="pm_card_visa",   # test card in sandbox
    automatic_payment_methods={"enabled": True, "allow_redirects": "never"},
)
# intent.id is the payment_intent_id
```

### OpenAI Severity Classification

```python
from openai import OpenAI

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

def classify_severity(description: str, address: str) -> str:
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You are a vehicle incident severity classifier. Respond with one word: low, medium, or high."},
            {"role": "user", "content": f"Incident at {address}: {description}"}
        ],
        max_tokens=10,
    )
    return response.choices[0].message.content.strip().lower()
```

### Google Maps Reverse Geocode

```python
import googlemaps

gmaps = googlemaps.Client(key=os.environ.get("GOOGLE_MAPS_API_KEY"))

def reverse_geocode(lat: float, lng: float) -> str:
    results = gmaps.reverse_geocode((lat, lng))
    if results:
        return results[0]["formatted_address"]
    return f"{lat},{lng}"
```

### Cancellation Policy Calculation

```python
from datetime import datetime

def calculate_refund(total_price: float, pickup_datetime_str: str, policy_tiers: list) -> float:
    pickup_dt = datetime.fromisoformat(pickup_datetime_str)
    now = datetime.utcnow()
    hours_before = (pickup_dt - now).total_seconds() / 3600
    # tiers from pricing_service are ordered: 24h→100%, 1h→50%, 0h→0%
    for tier in sorted(policy_tiers, key=lambda t: t["hours_before"], reverse=True):
        if hours_before > tier["hours_before"]:
            return round(total_price * tier["refund_percent"] / 100, 2)
    return 0.0
```

### Firestore Direct Partial Update (for refund_status / sms_status)

```python
# db is already initialized in the composite scaffold
db.collection("bookings").document(booking_id).update({
    "refund_status": "pending_manual"
})
```

---

## State of the Art

| Old Approach | Current Approach | Impact |
|--------------|------------------|--------|
| stripe_wrapper returns stub `pi_stub_phase1` | Real Stripe SDK with test key + mock failover | Composites get real payment_intent_id or documented mock ID |
| openai_wrapper returns hardcoded `"medium"` | Real OpenAI GPT-3.5 call with severity classification | Dynamic severity from incident description |
| googlemaps_wrapper returns `"Phase 1 stub"` address | Real Maps reverse geocode + mock failover | Real address stored on report document |
| twilio_wrapper: AMQP-only consumer in workers/ | HTTP Flask wrapper needed for Phase 4 + AMQP consumer for Phase 5 | Gap — must create wrappers/twilio_wrapper/ HTTP service |

---

## Open Questions

1. **twilio_wrapper HTTP service**
   - What we know: `workers/twilio_wrapper/` is an AMQP stub with no HTTP interface. `resolve_issue` needs to POST to it synchronously.
   - What's unclear: Should Phase 4 create a new `wrappers/twilio_wrapper/` HTTP Flask service (mirroring stripe_wrapper pattern) on port 6203? Or should resolve_issue call Twilio directly (violates locked decision)?
   - Recommendation: Create `wrappers/twilio_wrapper/` as HTTP Flask service on port 6203 with mock failover. The AMQP consumer in `workers/twilio_wrapper/` is Phase 5 only. Both can coexist as separate containers with different roles. Add to docker-compose.yml.

2. **book_car body: how does composite know the driver's license_number?**
   - What we know: `driver_service POST /validate` requires `license_number`. The frontend sends `user_uid`.
   - What's unclear: Is `license_number` sent in the POST /api/book-car request body, or must the composite look it up?
   - Recommendation: The composite fetches `GET /api/drivers/<uid>` first to get `license_number`, then validates. This is the correct pattern — composite orchestrates the lookup.

3. **report_issue: does composite need to validate the booking_id before creating a report?**
   - What we know: COMP-08 says "booking_service check" is part of Phase A.
   - What's unclear: Is this a strict gate (return 400 if booking not found) or informational?
   - Recommendation: Call `GET /api/bookings/<booking_id>` and return 400 if not found or not "confirmed". This mirrors the cancel_booking validation approach.

4. **Does stripe_wrapper refund need the original payment_intent_id or a charge_id?**
   - What we know: stripe_wrapper stub returns `refund_id` from `POST /api/stripe/refund`. The booking stores `stripe_payment_intent_id`.
   - What's unclear: Stripe's refund API can refund by PaymentIntent ID directly.
   - Recommendation: Pass `{ payment_intent_id, amount }` to stripe_wrapper refund. The wrapper calls `stripe.Refund.create(payment_intent=payment_intent_id, amount=amount_cents)`.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | bash smoke tests (matching Phase 3 pattern: `verify_phase3.sh`) |
| Config file | none — standalone shell script |
| Quick run command | `bash verify_phase4.sh` |
| Full suite command | `bash verify_phase4.sh` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| COMP-01 | POST /api/book-car returns 201 with booking_id | smoke | `curl -sf -X POST ... http://localhost:8000/api/book-car` | ❌ Wave 0 |
| COMP-02 | Stripe failure triggers vehicle unlock (vehicle status = available after failed charge) | smoke | `curl ... ; curl http://localhost:5001/api/vehicles/<id>` check status | ❌ Wave 0 |
| COMP-03 | Cancel already-cancelled booking returns 400 | smoke | `curl -sf -X POST ... http://localhost:8000/api/cancel-booking` with cancelled booking_id | ❌ Wave 0 |
| COMP-04 | Refund amount matches cancellation policy tier | smoke | Check `refund_amount` in cancel response | ❌ Wave 0 |
| COMP-05 | After cancel, booking status="cancelled" and vehicle status="available" | smoke | GET booking + GET vehicle after cancel | ❌ Wave 0 |
| COMP-06 | Stripe refund failure still cancels booking with refund_status="pending_manual" | smoke | Trigger with invalid payment_intent_id (if mock can be configured) | ❌ Wave 0 |
| COMP-07 | Cancel response shape: booking_id, status, refund_amount, refund_status | smoke | JSON field check on response | ❌ Wave 0 |
| COMP-08 | POST /api/report-issue persists report with geocoded address + severity | smoke | Check report document via GET /api/reports/<id> | ❌ Wave 0 |
| COMP-09 | RabbitMQ "report_topic" receives message after report-issue call | smoke/manual | Check RabbitMQ management UI at localhost:15672 | ❌ Wave 0 (manual) |
| COMP-10 | report-issue response: report_id, status="submitted", severity | smoke | JSON field check | ❌ Wave 0 |
| COMP-11 | POST /api/resolve-issue updates report and sends SMS; Twilio failure returns sms_status="unsent" | smoke | JSON field check + GET report | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `curl -sf http://localhost:6001/health && curl -sf http://localhost:6002/health && curl -sf http://localhost:6003/health && curl -sf http://localhost:6004/health`
- **Per wave merge:** `bash verify_phase4.sh`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `verify_phase4.sh` — full smoke test covering all COMP-01 through COMP-11
- [ ] `wrappers/twilio_wrapper/` HTTP Flask service — needed before resolve_issue tests can run

---

## Sources

### Primary (HIGH confidence)
- Direct code inspection: `composite/*/app.py`, `atomic/*/app.py`, `wrappers/*/app.py`, `workers/*/app.py` — verified actual implementation state
- `docker-compose.yml` — container names, ports, environment variable names, service dependencies
- `.env.example` — env var names for all API keys
- `atomic/booking_service/app.py` — confirmed `PUT /status` only updates `status` field (Firestore write hardcoded)
- `atomic/report_service/app.py` — confirmed 11-field schema, two separate update endpoints (evaluation, resolution)
- `atomic/pricing_service/app.py` — confirmed `GET /pricing/policy` tiers structure
- `atomic/driver_service/app.py` — confirmed validate takes `license_number`, GET by uid uses `.where()` query
- `04-CONTEXT.md` — all locked decisions and orchestration logic

### Secondary (MEDIUM confidence)
- Stripe Python SDK pattern: standard test-mode PaymentIntent creation with `pm_card_visa`
- OpenAI Python SDK: `client.chat.completions.create()` — current SDK v1.x pattern
- googlemaps Python client: `gmaps.reverse_geocode((lat, lng))` — official client library
- pika BlockingConnection + basic_publish pattern: well-established for simple one-shot publish

### Tertiary (LOW confidence)
- Exact Stripe PaymentIntent parameters for test-mode confirm=True flow — may need `return_url` or specific test card variant depending on SDK version

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries already in requirements.txt or directly identified from existing code
- Architecture: HIGH — all atomic service APIs verified by reading source; orchestration order locked in CONTEXT.md
- Pitfalls: HIGH — all identified from direct code inspection, not speculation
- twilio_wrapper HTTP gap: HIGH — confirmed by reading workers/twilio_wrapper/app.py (no Flask, no port)

**Research date:** 2026-03-15
**Valid until:** 2026-04-15 (stable stack; main risk is Stripe/OpenAI SDK minor version changes)
