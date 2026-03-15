---
phase: 05-async-workers
plan: 02
subsystem: api
tags: [pika, amqp, rabbitmq, firestore, firebase, workers, websocket]

requires:
  - phase: 05-01
    provides: websocket_server /notify endpoint and Phase 5 smoke test scaffold
  - phase: 04-composite-services
    provides: report_issue composite that publishes report.new to report_topic exchange

provides:
  - pika AMQP consumer on activity_queue bound to report_topic/report.new
  - Firestore writes to activity_log collection on every report.new event
  - Websocket notify POSTs to websocket_server:6100/notify after each Firestore write
  - connect_with_retry with exponential backoff (2^attempt seconds, up to 5 attempts)
  - Always-ACK pattern: basic_ack in finally block regardless of Firestore/websocket outcome

affects:
  - phase-05-async-workers (twilio_wrapper worker — same AMQP consumer pattern)
  - verify_phase5.sh smoke tests

tech-stack:
  added: []
  patterns:
    - "AMQP consumer pattern: connect_with_retry + callback with ACK-in-finally"
    - "Degraded-mode Firestore: db=None guard allows worker startup without Firebase credentials"

key-files:
  created: []
  modified:
    - workers/activity_log/app.py

key-decisions:
  - "activity_log always ACKs in finally block — message not requeued even if Firestore or websocket fails (audit trail is best-effort, not blocking)"
  - "Firestore init failure sets db=None allowing worker to continue in degraded mode"
  - "exchange_type=topic (not direct/fanout) — must match report_issue declaration exactly to avoid ChannelClosedByBroker"

patterns-established:
  - "AMQP worker pattern: connect_with_retry -> channel setup -> basic_consume -> start_consuming"
  - "Nested try/except for each downstream call (Firestore, websocket) — failure in one does not prevent the other"

requirements-completed: [WORK-05, WORK-06, WORK-07]

duration: 2min
completed: 2026-03-15
---

# Phase 5 Plan 02: activity_log AMQP Consumer Summary

**pika BlockingConnection consumer on activity_queue writing audit events to Firestore activity_log collection and notifying websocket_server on every report.new message**

## Performance

- **Duration:** ~2 min
- **Started:** 2026-03-15T03:18:18Z
- **Completed:** 2026-03-15T03:20:00Z
- **Tasks:** 1
- **Files modified:** 1

## Accomplishments
- Replaced Phase 1 stub (`while True: sleep(60)`) with full pika AMQP consumer
- Implemented connect_with_retry with exponential backoff: waits 2, 4, 8, 16, 32 seconds across up to 5 attempts
- On every `report.new` message: writes `{report_id, event, timestamp, severity}` to Firestore `activity_log` collection
- After Firestore write: POSTs `{report_id, event: "activity_logged", severity, message: "Activity logged"}` to websocket_server:6100/notify
- Always ACKs the message in `finally` block — no message requeue even if Firestore or websocket fails

## Task Commits

Each task was committed atomically:

1. **Task 1: Implement activity_log AMQP consumer with Firestore write and websocket notify** - `8c36ed6` (feat)

**Plan metadata:** (docs commit follows)

## Files Created/Modified
- `workers/activity_log/app.py` - Full pika AMQP consumer replacing Phase 1 stub; includes connect_with_retry, Firestore write, websocket POST, and ACK-in-finally pattern

## Decisions Made
- activity_log always ACKs in `finally` — audit trail is best-effort, message is not requeued if Firestore or websocket fails (avoids infinite requeue loops)
- Firestore init wrapped in try/except setting `db=None` on failure — worker starts in degraded mode without Firebase credentials
- `exchange_type="topic"` matches the declaration in `composite/report_issue/app.py` exactly to prevent `ChannelClosedByBroker` errors

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required beyond existing docker-compose env vars (RABBITMQ_HOST, WEBSOCKET_SERVER_URL, GOOGLE_APPLICATION_CREDENTIALS).

## Next Phase Readiness
- activity_log consumer is ready; on `docker-compose up` with RabbitMQ available, logs will show "Connected to RabbitMQ" then "Waiting for messages on activity_queue"
- When report_issue composite publishes a `report.new` message, activity_log will write to Firestore and notify websocket_server
- Phase 5 Plan 03 (twilio_wrapper AMQP consumer) can follow the same connect_with_retry + ACK-in-finally pattern established here

---
*Phase: 05-async-workers*
*Completed: 2026-03-15*
