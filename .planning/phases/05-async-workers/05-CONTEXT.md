# Phase 5: Async Workers - Context

**Gathered:** 2026-03-15
**Status:** Ready for planning

<domain>
## Phase Boundary

Replace Phase 1 stubs in `workers/twilio_wrapper` and `workers/activity_log` with real pika AMQP consumers, and upgrade `websocket_server/app.py` to emit Socket.IO `report_update` events to the frontend. `openai_wrapper` is HTTP-only (already built in Phase 4 — not touched here). `wrappers/twilio_wrapper` HTTP service is also already done in Phase 4 — this phase only concerns `workers/twilio_wrapper` (AMQP consumer).

</domain>

<decisions>
## Implementation Decisions

### SMS message content
- **Two recipients per incident event:**
  1. **Service team** → `TWILIO_SERVICE_TEAM_NUMBER` env var (already in docker-compose)
     - Body: `"[ESD Rental] New incident reported. Report: {report_id} | Vehicle: {vehicle_id} | Severity: {severity} | Location: {location}"`
  2. **Driver** → phone number fetched at processing time via `GET http://driver_service:5003/api/drivers/{user_uid}` (not in RabbitMQ payload — worker makes the extra HTTP call)
     - Body: `"[ESD Rental] Your incident report {report_id} has been received. Our team is reviewing it."`
- If driver phone fetch fails: log the error, skip the driver SMS, still send to service team and POST to websocket_server

### activity_log Firestore schema
- **Collection:** `activity_log` (dedicated collection, not a sub-collection under reports)
- **Doc ID:** Firestore auto-generated (`.add()`)
- **Fields:** `report_id`, `event` (`"report.new"`), `timestamp` (server time — `datetime.utcnow().isoformat()`), `severity`
- After writing to Firestore, POST `{ report_id, event: "activity_logged", severity, message: "Activity logged" }` to websocket_server

### websocket_server /notify → report_update emit shape
- **POST /notify accepts:** `{ report_id, event, severity, message }` (from both workers)
- **Socket.IO emit pattern:**
  ```python
  socketio.emit("report_update", {
      **data,
      "id": data["report_id"]   # required — frontend matches on r.id
  })
  ```
- The `id` field is critical: `ServiceDashboardView` line 97 matches `r.id === data.report_id || r.id === data.id`. Without `id`, `findIndex` returns -1 and every update prepends an orphan row instead of updating in-place.
- The `status: "pending"` field can be included in the worker POST body if needed; websocket_server spreads it through without mapping.

### AMQP twilio_wrapper mock failover
- Same pattern as `wrappers/twilio_wrapper` HTTP service (Phase 4):
  ```python
  try:
      # real Twilio SDK call
      msg = client.messages.create(...)
      message_sid = msg.sid
      provider = "twilio"
  except Exception as e:
      print(f"[twilio_wrapper] Twilio failed, using mock: {e}")
      message_sid = f"mock_{uuid.uuid4().hex}"
      provider = "fallback"
  ```
- Worker always completes and POSTs to websocket_server regardless of Twilio outcome
- Applies to both the service team SMS and the driver SMS sends

### Pika retry logic (WORK-07)
- Already decided in Phase 1 setup: workers have `depends_on: rabbitmq: condition: service_healthy` in docker-compose
- Pika retry loop: exponential backoff, retry up to 5 times before exiting — Claude's discretion on exact implementation

### Claude's Discretion
- Exact pika retry backoff intervals and max attempt count
- Queue/binding declaration pattern (whether to declare exchange+queue in the worker or assume they exist from docker-compose)
- Exact Firestore timestamp field format
- Error message wording in SMS bodies

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `workers/twilio_wrapper/app.py`: Phase 1 stub with EXCHANGE_NAME, RABBITMQ_HOST/PORT env vars already set — replace `while True: sleep(60)` with real pika consumer loop
- `workers/activity_log/app.py`: Same Phase 1 stub pattern — identical scaffold to twilio_wrapper worker
- `websocket_server/app.py`: Phase 1 stub already has Flask-SocketIO, CORS, `/notify` route, and `on_connect` handler — only the `/notify` body needs updating (remove stub comment, add `socketio.emit`)
- `wrappers/twilio_wrapper/app.py`: Real Twilio SDK + mock failover already implemented (Phase 4) — copy the try/except pattern directly

### Established Patterns
- AMQP: exchange `report_topic`, routing key `report.new` (Phase 1, locked)
- Socket.IO event name: `report_update` (Phase 2, locked)
- RabbitMQ message payload fields: `report_id, booking_id, vehicle_id, user_uid, severity, location, description` (Phase 4, locked)
- Mock failover shape: `{ "status": "ok", "message_sid": f"mock_{uuid}", "provider": "fallback" }` (Phase 4, locked)
- Inter-service HTTP: `requests.post(f"http://{HOST}:{PORT}/api/...", json=body, timeout=5)` (Phase 3/4, established)
- Error body shape: `{ "status": "error", "message": "..." }` (Phase 3, locked)

### Integration Points
- `workers/twilio_wrapper` → calls `driver_service:5003` to fetch driver phone, then `twilio_wrapper_http:6203` (or direct SDK), then `websocket_server:6100/notify`
- `workers/activity_log` → writes to Firestore (`activity_log` collection), then `websocket_server:6100/notify`
- `websocket_server:6100/notify` ← receives POSTs from both workers, emits `report_update` to connected Vue.js clients
- `WEBSOCKET_SERVER_URL` env var already set in docker-compose for both workers: `http://websocket_server:6100`

</code_context>

<specifics>
## Specific Ideas

- websocket_server emit must include `"id": data["report_id"]` — without it, `ServiceDashboardView` `findIndex` returns -1 and creates orphan rows instead of updating in-place
- Driver phone fetch failure is non-fatal: log, skip driver SMS, continue with service team SMS and websocket notify
- Both workers should use the `WEBSOCKET_SERVER_URL` env var (already in docker-compose) for the POST /notify call

</specifics>

<deferred>
## Deferred Ideas

- None — discussion stayed within Phase 5 scope

</deferred>

---

*Phase: 05-async-workers*
*Context gathered: 2026-03-15*
