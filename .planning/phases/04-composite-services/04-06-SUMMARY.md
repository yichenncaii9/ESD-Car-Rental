---
phase: 04-composite-services
plan: 06
subsystem: api
tags: [flask, pika, rabbitmq, twilio, firestore, composite, orchestration]

# Dependency graph
requires:
  - phase: 04-01
    provides: "Flask scaffolds for report_issue and resolve_issue with Firestore init and env vars"
  - phase: 04-03
    provides: "googlemaps_wrapper:6201, openai_wrapper:6200, twilio_wrapper_http:6203 HTTP endpoints"

provides:
  - "POST /api/report-issue — full 5-step Phase A orchestration (booking → geocode → openai → persist → evaluation update) plus Phase B RabbitMQ publish"
  - "POST /api/resolve-issue — resolution update → Twilio SMS → Firestore sms_status direct write on failure"

affects: [05-event-processing, frontend]

# Tech tracking
tech-stack:
  added: [pika (RabbitMQ BlockingConnection), requests (HTTP composite calls)]
  patterns:
    - "Severity held from openai_wrapper response (not re-fetched from Firestore) to return in Phase A response"
    - "RabbitMQ publish inline after report persisted — try/except swallows failure so Phase A HTTP response always returns"
    - "Twilio failure sets sms_status=unsent in response + Firestore direct write (report_service PUT /resolution cannot set sms_status)"
    - "db is not None guard before Firestore writes — container can start without Firebase credentials"

key-files:
  modified:
    - composite/report_issue/app.py
    - composite/resolve_issue/app.py

key-decisions:
  - "report_issue Phase A steps: booking validate → geocode → openai classify → persist report → PUT evaluation — severity from openai response not Firestore"
  - "RabbitMQ publish failure is logged and NOT re-raised — COMP-09 publish is best-effort, Phase A response always succeeds"
  - "resolve_issue sms_status written to Firestore directly on Twilio failure — report_service PUT /resolution only sets resolution field, not sms_status"
  - "driver_phone is optional in resolve-issue — missing phone is not an error, sms_status set to unsent with log"

patterns-established:
  - "Composite service graceful degradation: external service failures set fallback values (severity=medium, sms_status=unsent) rather than erroring the whole request"
  - "Phase A/B pattern: sync HTTP path always completes; async publish (Phase B) failure never blocks Phase A response"

requirements-completed: [COMP-08, COMP-09, COMP-10, COMP-11]

# Metrics
duration: 10min
completed: 2026-03-15
---

# Phase 4 Plan 06: report_issue and resolve_issue Composite Services Summary

**5-step report_issue orchestration (booking → geocode → openai → persist → evaluation) with pika RabbitMQ publish, plus resolve_issue with Twilio SMS fallback and Firestore sms_status direct write**

## Performance

- **Duration:** ~10 min
- **Started:** 2026-03-15T00:00:00Z
- **Completed:** 2026-03-15T00:10:00Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- report_issue Phase A: geocodes coordinates via googlemaps_wrapper:6201, classifies severity via openai_wrapper:6200, persists to report_service:5004, then calls PUT /evaluation with held severity
- report_issue Phase B: pika.BlockingConnection publishes full payload to report_topic exchange (routing key report.new); failure is try/except swallowed and logged — Phase A response unaffected
- resolve_issue: PUT report_service /resolution → POST twilio_wrapper_http:6203 /api/twilio/sms → on failure writes sms_status=unsent directly to Firestore; returns {report_id, status:"resolved", sms_status} always

## Task Commits

1. **Task 1: report_issue composite orchestration** - `7c8dbe7` (feat)
2. **Task 2: resolve_issue composite with Twilio SMS and graceful failure** - `58c3d5a` (feat)

## Files Created/Modified

- `composite/report_issue/app.py` - Full 5-step Phase A orchestration + Phase B pika publish; replaced Phase 1 stub; port 6003
- `composite/resolve_issue/app.py` - resolve orchestration with Twilio HTTP call and Firestore sms_status fallback; replaced Phase 1 stub; port 6004

## Decisions Made

- Severity is held from the openai_wrapper response local variable and returned in Phase A — it is never re-fetched from Firestore. This avoids an extra read and matches COMP-10 spec.
- RabbitMQ publish is inline after report persisted (not threaded) — try/except ensures failure does not raise and Phase A response always returns.
- sms_status written directly to Firestore `reports` collection on Twilio failure — report_service does not expose an sms_status endpoint, so direct write is the only option.
- driver_phone is treated as optional rather than required — some flows may not include phone; missing phone logs a warning and sets sms_status=unsent but is not an error.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required beyond what was set up in Plan 01 (env vars: RABBITMQ_HOST, RABBITMQ_PORT, TWILIO_WRAPPER_HOST).

## Next Phase Readiness

- Scenario 3 sync path is complete end-to-end: report_issue composite handles COMP-08/09/10, resolve_issue handles COMP-11
- RabbitMQ message delivery to report_topic can be verified at localhost:15672 after docker-compose up
- Phase 5 event-processing workers (evaluator, notifier) can now consume from report_topic exchange with routing key report.new

---
*Phase: 04-composite-services*
*Completed: 2026-03-15*
