---
phase: 05-async-workers
plan: "03"
subsystem: workers
tags:
  - twilio
  - amqp
  - pika
  - sms
  - rabbitmq
  - websocket
dependency_graph:
  requires:
    - 05-01 (websocket_server /notify endpoint)
    - report_topic exchange declared by composite/report_issue
    - driver_service GET /api/drivers/{uid}
  provides:
    - SMS to service team on every report.new message
    - SMS to driver (when phone available)
    - POST to websocket_server /notify with event:sms_sent
  affects:
    - workers/twilio_wrapper (replaces Phase 1 stub entirely)
tech_stack:
  added:
    - twilio (Twilio Python SDK in requirements.txt)
  patterns:
    - pika BlockingConnection consumer with connect_with_retry exponential backoff
    - mock failover: try Twilio SDK -> except -> mock_<uuid> fallback
    - non-fatal driver phone fetch (requests.get, failure logged and skipped)
    - always-ACK in finally block
key_files:
  created: []
  modified:
    - workers/twilio_wrapper/app.py
    - workers/twilio_wrapper/requirements.txt
decisions:
  - twilio import placed inside send_sms try block so ImportError (missing/invalid SDK) triggers mock fallback automatically
  - TWILIO_SERVICE_TEAM guard: SMS only sent if env var is set, allowing local dev without credentials
  - driver_service:5003 host sourced from DRIVER_SERVICE_HOST env var with default fallback
metrics:
  duration: "3 min"
  completed_date: "2026-03-15"
  tasks_completed: 2
  files_modified: 2
---

# Phase 5 Plan 03: twilio_wrapper AMQP Consumer Summary

**One-liner:** pika AMQP consumer on twilio_queue sending Twilio SMS (with mock fallover) to service team and driver, then POSTing sms_sent event to websocket_server.

## What Was Built

Replaced the Phase 1 stub (`while True: time.sleep(60)`) in `workers/twilio_wrapper/app.py` with a fully functional pika BlockingConnection consumer. When a `report.new` message arrives on `twilio_queue`:

1. Service team SMS sent to `TWILIO_SERVICE_TEAM_NUMBER` with incident details (report_id, vehicle_id, severity, location). If Twilio credentials are missing or the API fails, a `mock_<uuid>` SID is returned with provider `fallback`.
2. Driver phone number fetched via `GET http://driver_service:5003/api/drivers/{user_uid}`. If the fetch fails or returns no phone, the step is skipped with a non-fatal log — processing continues.
3. Driver SMS sent with acknowledgement message if phone was obtained.
4. POST to `websocket_server:6100/notify` with `{report_id, event: "sms_sent", severity, message}` — websocket failure is non-fatal (logged, not re-raised).
5. Message is ACKed in `finally` block regardless of any step outcome.

`connect_with_retry` uses exponential backoff (2^attempt seconds) for up to 5 attempts before raising.

## Commits

| Task | Commit | Description |
|------|--------|-------------|
| Task 1 | 1c3866e | chore(05-03): add twilio SDK to twilio_wrapper requirements |
| Task 2 | e501d78 | feat(05-03): implement twilio_wrapper AMQP consumer with SMS and websocket notify |

## Deviations from Plan

None - plan executed exactly as written.

## Self-Check: PASSED

- workers/twilio_wrapper/app.py: FOUND (110 lines, pika consumer)
- workers/twilio_wrapper/requirements.txt: FOUND (pika, requests, twilio)
- Commit 1c3866e: FOUND
- Commit e501d78: FOUND
