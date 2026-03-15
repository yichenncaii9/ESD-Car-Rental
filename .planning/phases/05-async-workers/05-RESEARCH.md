# Phase 5: Async Workers - Research

**Researched:** 2026-03-15
**Domain:** pika AMQP consumers, Flask-SocketIO, Twilio SMS, firebase-admin Firestore writes
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**SMS message content — two recipients per incident event:**
1. Service team → `TWILIO_SERVICE_TEAM_NUMBER` env var
   - Body: `"[ESD Rental] New incident reported. Report: {report_id} | Vehicle: {vehicle_id} | Severity: {severity} | Location: {location}"`
2. Driver → phone fetched at processing time via `GET http://driver_service:5003/api/drivers/{user_uid}`
   - Body: `"[ESD Rental] Your incident report {report_id} has been received. Our team is reviewing it."`
- If driver phone fetch fails: log, skip driver SMS, still send to service team and POST to websocket_server

**activity_log Firestore schema:**
- Collection: `activity_log` (dedicated, not sub-collection)
- Doc ID: Firestore auto-generated (`.add()`)
- Fields: `report_id`, `event` (`"report.new"`), `timestamp` (`datetime.utcnow().isoformat()`), `severity`
- After Firestore write: POST `{ report_id, event: "activity_logged", severity, message: "Activity logged" }` to websocket_server

**websocket_server /notify → report_update emit shape:**
- POST /notify accepts: `{ report_id, event, severity, message }`
- Emit pattern:
  ```python
  socketio.emit("report_update", {
      **data,
      "id": data["report_id"]   # required — frontend findIndex matches r.id === data.id
  })
  ```
- The `id` field is CRITICAL — without it `findIndex` returns -1 and every update prepends orphan rows

**AMQP twilio_wrapper mock failover:** Same pattern as wrappers/twilio_wrapper (Phase 4). Try real Twilio SDK → except → `mock_{uuid}` with `provider:"fallback"`. Always completes and POSTs to websocket_server regardless of Twilio outcome. Applies to both service team SMS and driver SMS.

**Pika retry logic (WORK-07):** Workers have `depends_on: rabbitmq: condition: service_healthy` in docker-compose. Retry loop: exponential backoff, up to 5 attempts, then exit. Exact intervals are Claude's discretion.

### Claude's Discretion
- Exact pika retry backoff intervals and max attempt count
- Queue/binding declaration pattern (declare exchange+queue in worker or assume they exist)
- Exact Firestore timestamp field format
- Error message wording in SMS bodies

### Deferred Ideas (OUT OF SCOPE)
- None — discussion stayed within Phase 5 scope
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| WORK-01 | twilio_wrapper subscribes to "twilio_queue" bound to "report_topic" with key "report.new" | pika `basic_consume` on declared queue with topic exchange binding |
| WORK-02 | twilio_wrapper sends SMS to service team via Twilio API | Twilio SDK `client.messages.create()` with mock failover pattern from Phase 4 |
| WORK-03 | twilio_wrapper HTTP POSTs `{ report_id, event: "sms_sent" }` to websocket_server after SMS | `requests.post(WEBSOCKET_SERVER_URL + "/notify", ...)` pattern from established codebase |
| WORK-04 | twilio_wrapper HTTP POSTs full update payload to websocket_server after SMS | Same as WORK-03 — POST body includes `report_id, event, severity, message` |
| WORK-05 | activity_log subscribes to "activity_queue" bound to "report_topic" with key "report.new" | Same pika pattern as WORK-01, different queue name |
| WORK-06 | activity_log persists event to Firestore and POSTs update to websocket_server | `db.collection("activity_log").add(doc)` then `requests.post` — established Firestore pattern |
| WORK-07 | Both workers have pika retry logic for RabbitMQ startup race | Exponential backoff retry loop before entering `basic_consume` |
| WS-01 | websocket_server runs on port 6100, Flask-SocketIO, part of stack | Already running (Phase 1 container); needs /notify body upgrade only |
| WS-02 | Vue.js frontend connects to websocket_server via Socket.IO on ServiceDashboard load | Already implemented in Phase 2 — no frontend changes needed in Phase 5 |
| WS-03 | websocket_server POST /notify emits Socket.IO event to connected clients | Replace stub comment in `/notify` with `socketio.emit("report_update", {...})` |
| WS-04 | websocket_server pushes async event to frontend without polling | Socket.IO push model; no polling; activated by worker POST to /notify |
</phase_requirements>

---

## Summary

Phase 5 is a pure implementation phase — all scaffolding, ports, env vars, and patterns are already established in earlier phases. The three code files requiring changes are small and well-defined: `workers/twilio_wrapper/app.py` (Phase 1 stub, ~15 lines), `workers/activity_log/app.py` (identical stub), and `websocket_server/app.py` (Phase 1 stub, ~30 lines with one stub comment to replace).

The technical content is a classic AMQP fan-out consumer pattern using pika's `BlockingConnection`. Two independent queues (`twilio_queue`, `activity_queue`) bind to the same `report_topic` exchange with the same routing key (`report.new`), so both workers receive every incident event published by `composite/report_issue`. Each worker processes its message independently and HTTP-POSTs a notify payload to `websocket_server:6100/notify`, which then emits a `report_update` Socket.IO event to all connected frontend clients.

The most critical implementation detail is the `"id": data["report_id"]` field in the websocket_server emit — this is what allows `ServiceDashboardView`'s `findIndex` to match existing rows. The second highest-risk item is the pika retry loop: workers must not crash if RabbitMQ is still initializing despite `depends_on: service_healthy`, because the healthcheck only guarantees the management port is open, not that the AMQP port is fully ready for connections.

**Primary recommendation:** Replace the three stubs in sequence — websocket_server first (no external deps), then activity_log, then twilio_wrapper. This lets /notify be verified before workers try to call it.

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pika | latest (in requirements.txt) | Python AMQP 0-9-1 client for RabbitMQ | Standard Python RabbitMQ client; already in both worker requirements.txt |
| flask-socketio | latest (in requirements.txt) | Socket.IO server on Flask | Already in websocket_server/requirements.txt; Phase 1 stub uses it |
| flask | >=3.0 | HTTP server for /notify endpoint | Already in websocket_server/requirements.txt |
| twilio | latest (implicit via SDK) | Send SMS via Twilio REST API | Already used in wrappers/twilio_wrapper Phase 4 — same pattern |
| firebase-admin | latest (in requirements.txt) | Firestore writes for activity_log | Already in workers/activity_log/requirements.txt |
| requests | latest (in requirements.txt) | HTTP POST to websocket_server | Already in both worker requirements.txt |

### No new dependencies required
All libraries are already declared in the existing requirements.txt files. Phase 5 installs nothing new.

---

## Architecture Patterns

### Overall Data Flow
```
composite/report_issue
  └─ pika.BlockingConnection → publish to "report_topic" exchange, key "report.new"
        │
        ├─ workers/twilio_wrapper (queue: "twilio_queue")
        │     ├─ fetch driver phone: GET driver_service:5003/api/drivers/{user_uid}
        │     ├─ Twilio SDK: send SMS to service team (mock failover)
        │     ├─ Twilio SDK: send SMS to driver (mock failover, non-fatal on phone fetch fail)
        │     └─ requests.post websocket_server:6100/notify {report_id, event:"sms_sent", ...}
        │
        └─ workers/activity_log (queue: "activity_queue")
              ├─ db.collection("activity_log").add({report_id, event, timestamp, severity})
              └─ requests.post websocket_server:6100/notify {report_id, event:"activity_logged", ...}

websocket_server:6100/notify
  └─ socketio.emit("report_update", {**data, "id": data["report_id"]})
        └─ ServiceDashboardView socket.on("report_update") → update or prepend row
```

### Pattern 1: Pika AMQP Consumer with Retry Loop

**What:** Connect to RabbitMQ with exponential backoff on startup, declare exchange + queue + binding, then enter `basic_consume` blocking loop.

**When to use:** All AMQP workers that start before RabbitMQ AMQP port is fully ready.

```python
# Source: established pattern from composite/report_issue/app.py + CONTEXT.md decision
import pika
import time
import json

RABBITMQ_HOST = os.environ.get("RABBITMQ_HOST", "rabbitmq")
RABBITMQ_PORT = int(os.environ.get("RABBITMQ_PORT", 5672))
EXCHANGE_NAME = "report_topic"
QUEUE_NAME = "twilio_queue"      # or "activity_queue" for activity_log worker
ROUTING_KEY = "report.new"

def connect_with_retry(max_attempts=5):
    for attempt in range(1, max_attempts + 1):
        try:
            connection = pika.BlockingConnection(
                pika.ConnectionParameters(host=RABBITMQ_HOST, port=RABBITMQ_PORT, heartbeat=60)
            )
            print(f"[worker] Connected to RabbitMQ on attempt {attempt}")
            return connection
        except Exception as e:
            wait = 2 ** attempt   # 2, 4, 8, 16, 32 seconds
            print(f"[worker] RabbitMQ not ready (attempt {attempt}/{max_attempts}): {e}. Retrying in {wait}s")
            if attempt == max_attempts:
                raise
            time.sleep(wait)

def main():
    connection = connect_with_retry()
    channel = connection.channel()
    channel.exchange_declare(exchange=EXCHANGE_NAME, exchange_type="topic", durable=True)
    channel.queue_declare(queue=QUEUE_NAME, durable=True)
    channel.queue_bind(queue=QUEUE_NAME, exchange=EXCHANGE_NAME, routing_key=ROUTING_KEY)
    channel.basic_qos(prefetch_count=1)
    channel.basic_consume(queue=QUEUE_NAME, on_message_callback=callback)
    print(f"[worker] Waiting for messages on {QUEUE_NAME}...")
    channel.start_consuming()

if __name__ == "__main__":
    main()
```

### Pattern 2: Message Callback with ACK

**What:** Process message, always `basic_ack` to remove from queue (even on partial failure).

```python
# Source: pika consumer pattern (WORK-01, WORK-05)
def callback(ch, method, properties, body):
    try:
        data = json.loads(body)
        process(data)
    except Exception as e:
        print(f"[worker] Error processing message: {e}")
    finally:
        ch.basic_ack(delivery_tag=method.delivery_tag)
```

**Critical:** Always ACK even on error — un-ACKed messages re-queue indefinitely and cause worker restart loops.

### Pattern 3: websocket_server /notify Emit

**What:** Accept POST, spread payload into Socket.IO emit, add required `id` field.

```python
# Source: CONTEXT.md locked decision (ServiceDashboardView line 97 match logic)
@app.route("/notify", methods=["POST"])
def notify():
    data = request.get_json() or {}
    socketio.emit("report_update", {
        **data,
        "id": data.get("report_id")   # REQUIRED — frontend findIndex uses r.id
    })
    return jsonify({"status": "ok"}), 200
```

### Pattern 4: Firestore Write in Worker (activity_log)

**What:** Non-Flask service initializing firebase-admin and writing directly (no HTTP endpoint needed).

```python
# Source: established pattern from atomic/report_service/app.py — same firebase-admin init
import firebase_admin
from firebase_admin import credentials, firestore as fs
import datetime

try:
    cred = credentials.Certificate(
        os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "/secrets/firebase-service-account.json")
    )
    firebase_admin.initialize_app(cred)
    db = fs.client()
except Exception as e:
    print(f"[activity_log] Firestore init failed: {e}")
    db = None

# In callback:
if db:
    db.collection("activity_log").add({
        "report_id": data.get("report_id"),
        "event":     "report.new",
        "timestamp": datetime.datetime.utcnow().isoformat(),
        "severity":  data.get("severity"),
    })
```

### Anti-Patterns to Avoid

- **Re-raising in AMQP callback without ACK:** Causes the message to stay in queue, worker crashes, message re-delivered on restart — infinite loop.
- **Missing `"id"` field in socketio.emit:** `ServiceDashboardView` `findIndex(r => r.id === data.id)` returns -1 every time, each event prepends a new orphan row instead of updating in-place.
- **Blocking `channel.start_consuming()` without retry:** If pika connects but RabbitMQ drops the connection later, the worker silently dies. `restart: unless-stopped` in docker-compose recovers it, but the retry loop is still necessary for startup.
- **Declaring exchange type inconsistently:** `report_issue` declares `exchange_type="topic"`. Workers must declare with the same type. If already declared with different type, pika raises `ChannelClosedByBroker`. Use `passive=True` to detect or just declare identically.
- **Calling Firestore in worker without `db is None` guard:** Worker crashes if firebase credentials are unavailable; `db is None` guard allows degraded operation.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| RabbitMQ message delivery | Custom TCP socket | pika.BlockingConnection | pika handles AMQP framing, heartbeat, acknowledgements |
| SMS delivery with retries | requests to Twilio REST | twilio.rest.Client | SDK handles auth header construction, retry, SID parsing |
| Real-time push to browser | Long-polling HTTP loop | Flask-SocketIO + Socket.IO client | Already wired in Phase 1/2 — just fill the stub |
| Firestore document creation | REST API calls to Firestore | firebase-admin `db.collection().add()` | SDK handles auth, retry, document ID generation |

---

## Common Pitfalls

### Pitfall 1: Un-ACKed Messages on Worker Error
**What goes wrong:** Worker raises an exception inside the callback before `basic_ack`. Message returns to queue. Worker restarts (docker restart policy). Message is re-delivered. Loop continues indefinitely.
**Why it happens:** pika treats un-ACKed messages as unprocessed when consumer disconnects.
**How to avoid:** Wrap callback body in `try/except/finally: ch.basic_ack(...)`.
**Warning signs:** RabbitMQ management UI shows messages stuck in "Unacked" state.

### Pitfall 2: Missing `id` in websocket emit
**What goes wrong:** `ServiceDashboardView` `findIndex` always returns -1. Every `report_update` event prepends a new duplicate row instead of updating the existing one.
**Why it happens:** Frontend matches `r.id === data.id` (line 97). websocket_server spreads `data` but `report_id` ≠ `id`.
**How to avoid:** Always include `"id": data.get("report_id")` in the emit payload.
**Warning signs:** Dashboard shows duplicate rows growing with each async event.

### Pitfall 3: exchange_type Mismatch on Re-declaration
**What goes wrong:** Worker declares `report_topic` exchange with wrong type (e.g., `direct`). pika raises `ChannelClosedByBroker: (406, "PRECONDITION_FAILED...")`.
**Why it happens:** RabbitMQ rejects re-declaration if exchange already exists with different type.
**How to avoid:** Use `exchange_type="topic"` consistently — matches the declaration in `composite/report_issue/app.py`.
**Warning signs:** Worker logs `ChannelClosedByBroker` immediately after connecting.

### Pitfall 4: Driver Phone Fetch Failure Blocks Service Team SMS
**What goes wrong:** Worker awaits driver phone fetch, gets 500/timeout, raises exception, never sends service team SMS or POSTs to websocket.
**Why it happens:** Linear code flow — exception propagates before service team SMS code runs.
**How to avoid:** Wrap driver fetch in separate `try/except`. Store result in variable, continue regardless. Service team SMS and websocket POST run unconditionally after.
**Warning signs:** Service team never receives SMS when driver_service is slow/down.

### Pitfall 5: Flask-SocketIO `socketio.run()` vs. `app.run()`
**What goes wrong:** Using `app.run()` instead of `socketio.run()` breaks WebSocket upgrade — clients connect via HTTP polling only, latency increases.
**Why it happens:** Flask's dev server doesn't support WebSocket protocol upgrades; SocketIO wraps the WSGI app.
**How to avoid:** Already correct in the Phase 1 stub (`socketio.run(app, ...)`). Don't change it to `app.run()`.

---

## Code Examples

### twilio_wrapper Worker — Full Structure

```python
# workers/twilio_wrapper/app.py
# Source: CONTEXT.md locked decisions + Phase 4 wrappers/twilio_wrapper pattern
import os, json, uuid, time
import pika
import requests

RABBITMQ_HOST  = os.environ.get("RABBITMQ_HOST", "rabbitmq")
RABBITMQ_PORT  = int(os.environ.get("RABBITMQ_PORT", 5672))
WEBSOCKET_URL  = os.environ.get("WEBSOCKET_SERVER_URL", "http://websocket_server:6100")
DRIVER_HOST    = os.environ.get("DRIVER_SERVICE_HOST", "driver_service:5003")
TWILIO_ACCOUNT_SID     = os.environ.get("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN      = os.environ.get("TWILIO_AUTH_TOKEN")
TWILIO_FROM_NUMBER     = os.environ.get("TWILIO_FROM_NUMBER", "+15005550006")
TWILIO_SERVICE_TEAM    = os.environ.get("TWILIO_SERVICE_TEAM_NUMBER")
EXCHANGE_NAME  = "report_topic"
QUEUE_NAME     = "twilio_queue"
ROUTING_KEY    = "report.new"

def send_sms(to, body):
    try:
        from twilio.rest import Client
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        msg = client.messages.create(body=body, from_=TWILIO_FROM_NUMBER, to=to)
        return msg.sid, "twilio"
    except Exception as e:
        print(f"[twilio_wrapper] Twilio failed, using mock: {e}")
        return f"mock_{uuid.uuid4().hex}", "fallback"

def callback(ch, method, properties, body):
    try:
        data = json.loads(body)
        report_id  = data.get("report_id")
        vehicle_id = data.get("vehicle_id")
        severity   = data.get("severity")
        location   = data.get("location")
        user_uid   = data.get("user_uid")

        # Send to service team (always)
        if TWILIO_SERVICE_TEAM:
            msg = f"[ESD Rental] New incident reported. Report: {report_id} | Vehicle: {vehicle_id} | Severity: {severity} | Location: {location}"
            sid, provider = send_sms(TWILIO_SERVICE_TEAM, msg)
            print(f"[twilio_wrapper] Service team SMS sent: {sid} ({provider})")

        # Fetch driver phone and send (non-fatal on failure)
        try:
            r = requests.get(f"http://{DRIVER_HOST}/api/drivers/{user_uid}", timeout=5)
            if r.status_code == 200:
                driver_phone = r.json().get("phone_number")
                if driver_phone:
                    driver_msg = f"[ESD Rental] Your incident report {report_id} has been received. Our team is reviewing it."
                    sid2, provider2 = send_sms(driver_phone, driver_msg)
                    print(f"[twilio_wrapper] Driver SMS sent: {sid2} ({provider2})")
        except Exception as e:
            print(f"[twilio_wrapper] Driver phone fetch failed (non-fatal): {e}")

        # POST to websocket_server
        try:
            requests.post(f"{WEBSOCKET_URL}/notify",
                          json={"report_id": report_id, "event": "sms_sent",
                                "severity": severity, "message": "SMS notifications sent"},
                          timeout=5)
        except Exception as e:
            print(f"[twilio_wrapper] websocket notify failed: {e}")

    except Exception as e:
        print(f"[twilio_wrapper] callback error: {e}")
    finally:
        ch.basic_ack(delivery_tag=method.delivery_tag)
```

### activity_log Worker — Firestore Write + Notify

```python
# workers/activity_log/app.py  (key sections)
# Source: CONTEXT.md locked decisions + report_service Firestore pattern
def callback(ch, method, properties, body):
    try:
        data = json.loads(body)
        report_id = data.get("report_id")
        severity  = data.get("severity")

        # Write to Firestore
        if db:
            db.collection("activity_log").add({
                "report_id": report_id,
                "event":     "report.new",
                "timestamp": datetime.datetime.utcnow().isoformat(),
                "severity":  severity,
            })
            print(f"[activity_log] Firestore write: report_id={report_id}")

        # POST to websocket_server
        try:
            requests.post(f"{WEBSOCKET_URL}/notify",
                          json={"report_id": report_id, "event": "activity_logged",
                                "severity": severity, "message": "Activity logged"},
                          timeout=5)
        except Exception as e:
            print(f"[activity_log] websocket notify failed: {e}")

    except Exception as e:
        print(f"[activity_log] callback error: {e}")
    finally:
        ch.basic_ack(delivery_tag=method.delivery_tag)
```

### websocket_server /notify — Minimal Change

```python
# websocket_server/app.py — only the /notify route changes from Phase 1 stub
# Source: CONTEXT.md locked decision on emit shape
@app.route("/notify", methods=["POST"])
def notify():
    data = request.get_json() or {}
    print(f"[websocket_server] /notify received: {data}")
    socketio.emit("report_update", {
        **data,
        "id": data.get("report_id")   # REQUIRED for ServiceDashboardView findIndex
    })
    return jsonify({"status": "ok"}), 200
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Phase 1 stub: `while True: time.sleep(60)` | Real pika consumer with retry | Phase 5 (this phase) | Workers actually process RabbitMQ events |
| Phase 1 stub: `/notify` returns hardcoded stub response | `/notify` calls `socketio.emit` | Phase 5 (this phase) | Real-time push to connected browsers |

---

## Open Questions

1. **twilio_wrapper worker: does `twilio` SDK need to be added to requirements.txt?**
   - What we know: `workers/twilio_wrapper/requirements.txt` currently only has `pika` and `requests`. The `twilio` package is NOT in it.
   - What's unclear: Is the mock failover pattern sufficient and should `twilio` be installed but expected to fail, or should requirements.txt be updated?
   - Recommendation: Add `twilio` to `workers/twilio_wrapper/requirements.txt`. The mock failover pattern requires the `from twilio.rest import Client` import to be inside `try` block so import failure itself triggers mock — but the package must be installed for any real SMS sends. Since `wrappers/twilio_wrapper` already has the same pattern, follow that precedent. The planner should include a task to add `twilio` to the worker requirements.txt.

2. **activity_log worker: firebase-admin is already in requirements.txt**
   - What we know: `workers/activity_log/requirements.txt` already has `pika`, `requests`, `firebase-admin`. No new dependencies needed.
   - Status: Non-issue — confirmed complete.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | Manual curl/HTTP testing + docker-compose logs observation |
| Config file | none — no automated test suite detected for workers |
| Quick run command | `curl -s -X POST http://localhost:6100/notify -H "Content-Type: application/json" -d '{"report_id":"test-001","event":"sms_sent","severity":"high","message":"test"}'` |
| Full suite command | `docker-compose logs twilio_wrapper activity_log websocket_server` after publishing a test message to RabbitMQ |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| WORK-01 | twilio_queue bound to report_topic/report.new | smoke | `docker-compose logs twilio_wrapper \| grep "Waiting for messages"` | ❌ Wave 0 |
| WORK-02 | SMS sent to service team | smoke | `docker-compose logs twilio_wrapper \| grep "Service team SMS sent"` | ❌ Wave 0 |
| WORK-03 | POST to websocket_server after SMS | smoke | `docker-compose logs twilio_wrapper \| grep "websocket notify"` | ❌ Wave 0 |
| WORK-04 | Full update payload in websocket POST | smoke | `docker-compose logs websocket_server \| grep "/notify received"` | ❌ Wave 0 |
| WORK-05 | activity_queue bound to report_topic/report.new | smoke | `docker-compose logs activity_log \| grep "Waiting for messages"` | ❌ Wave 0 |
| WORK-06 | Firestore write + websocket notify | smoke | `docker-compose logs activity_log \| grep "Firestore write"` | ❌ Wave 0 |
| WORK-07 | Pika retry on startup | smoke | `docker-compose logs twilio_wrapper \| grep "Connected to RabbitMQ"` | ❌ Wave 0 |
| WS-01 | websocket_server on port 6100 | smoke | `curl -sf http://localhost:6100/health` | ❌ Wave 0 |
| WS-03 | /notify emits Socket.IO event | unit | `curl -X POST http://localhost:6100/notify -H "Content-Type: application/json" -d '{"report_id":"r1","event":"sms_sent","severity":"high","message":"test"}'` | ❌ Wave 0 |
| WS-04 | Real-time push without polling | manual | Open ServiceDashboard, submit report, observe row update without page reload | manual-only |

### Sampling Rate
- **Per task commit:** `curl -sf http://localhost:6100/health`
- **Per wave merge:** `docker-compose logs twilio_wrapper activity_log websocket_server --tail=50`
- **Phase gate:** All smoke tests pass + manual end-to-end test in ServiceDashboard before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `scripts/verify_phase5.sh` — shell script with curl smoke tests for WS-01, WS-03, WORK-01 through WORK-07 via log inspection
- [ ] No framework install needed — bash + curl available in all environments

---

## Sources

### Primary (HIGH confidence)
- Existing codebase files (read directly):
  - `workers/twilio_wrapper/app.py` — Phase 1 stub; confirmed env vars EXCHANGE_NAME, RABBITMQ_HOST/PORT
  - `workers/activity_log/app.py` — identical stub pattern
  - `websocket_server/app.py` — Flask-SocketIO, CORS, /notify stub, on_connect handler confirmed
  - `wrappers/twilio_wrapper/app.py` — mock failover try/except pattern confirmed
  - `composite/report_issue/app.py` — pika.BlockingConnection publish pattern confirmed; exchange declared as topic/durable
  - `atomic/report_service/app.py` — firebase-admin init try/except pattern; `db.collection().add()` confirmed
  - `frontend/src/views/ServiceDashboardView.vue` — line 97 `findIndex(r => r.id === data.report_id || r.id === data.id)` confirmed; event name `report_update` confirmed
  - `docker-compose.yml` — env vars WEBSOCKET_SERVER_URL, TWILIO_SERVICE_TEAM_NUMBER, RABBITMQ_HOST/PORT confirmed on both workers; `depends_on: rabbitmq: condition: service_healthy` confirmed
  - `workers/twilio_wrapper/requirements.txt` — `pika`, `requests` only (twilio SDK missing — open question above)
  - `workers/activity_log/requirements.txt` — `pika`, `requests`, `firebase-admin` confirmed
  - `websocket_server/requirements.txt` — `flask>=3.0`, `flask-cors`, `flask-socketio` confirmed
- `.planning/phases/05-async-workers/05-CONTEXT.md` — all locked decisions

### Secondary (MEDIUM confidence)
- None needed — all findings backed by direct code inspection

### Tertiary (LOW confidence)
- None

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all packages verified in existing requirements.txt files
- Architecture: HIGH — pika consumer pattern verified in composite/report_issue; Firestore pattern verified in atomic services; Socket.IO emit shape verified in CONTEXT.md + frontend source
- Pitfalls: HIGH — emit shape pitfall verified by reading ServiceDashboardView line 97; AMQP ACK pitfall is standard pika behavior

**Research date:** 2026-03-15
**Valid until:** 2026-04-15 (stable stack; pika, Flask-SocketIO, firebase-admin all stable libraries)
