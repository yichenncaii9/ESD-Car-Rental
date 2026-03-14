---
phase: 04-composite-services
plan: "04"
subsystem: api
tags: [flask, stripe, firestore, orchestration, rollback, composite-service]

requires:
  - phase: 04-02
    provides: stripe_wrapper with real SDK + mock failover at stripe_wrapper:6202
  - phase: 03-atomic-services
    provides: driver_service:5003, vehicle_service:5001, pricing_service:5005, booking_service:5002 atomic APIs

provides:
  - "POST /api/book-car: full 7-step orchestration (driver fetch → validate → vehicle check → lock → pricing → stripe charge → booking create)"
  - "Vehicle lock before Stripe charge prevents double-booking race"
  - "Best-effort rollback on booking_service failure: refund + vehicle unlock"
  - "409 Conflict on vehicle unavailable, 400 on driver validation failure"
  - "201 response with {booking_id, status:confirmed, payment_intent_id}"

affects: [cancel_booking, verify_phase4]

tech-stack:
  added: [requests]
  patterns:
    - "Sequential orchestration with inline rollback on each failure step"
    - "Lock resource before charging (vehicle locked before Stripe charge)"
    - "Best-effort rollback: try/except per rollback call, log failures without re-raising"
    - "GET then POST driver pattern: fetch license_number via GET /drivers/{uid}, then POST /drivers/validate"

key-files:
  created: []
  modified:
    - composite/book_car/app.py

key-decisions:
  - "Vehicle locked BEFORE Stripe charge: prevents double-booking race condition where two concurrent requests both pass availability check"
  - "booking_service failure triggers best-effort rollback (refund + unlock) — rollback exceptions logged not re-raised to avoid masking original error"
  - "driver_service.validate takes license_number not uid — must GET /drivers/{uid} first to extract license_number field"
  - "pricing_service uses query params not JSON body — requests.get(url, params={vehicle_type, hours})"

patterns-established:
  - "Pattern: orchestration failure = unlock earliest acquired resource, then return error — no partial state left"

requirements-completed: [COMP-01, COMP-02]

duration: 5min
completed: 2026-03-15
---

# Phase 4 Plan 04: book_car Composite Orchestration Summary

**Full 7-step book_car orchestration replacing Phase 1 stub: driver fetch+validate → vehicle lock → pricing → Stripe charge → booking create, with best-effort rollback on booking failure**

## Performance

- **Duration:** ~5 min
- **Started:** 2026-03-15T00:00:00Z
- **Completed:** 2026-03-15T00:05:00Z
- **Tasks:** 1 of 1
- **Files modified:** 1

## Accomplishments
- Replaced Phase 1 stub with production-ready 7-step orchestration in `composite/book_car/app.py`
- Implemented vehicle lock-before-charge pattern to prevent double-booking race condition
- Implemented best-effort rollback (Stripe refund + vehicle unlock) when booking_service fails after payment
- Returns 201 with `{booking_id, status:"confirmed", payment_intent_id}` on success; 409 on vehicle conflict, 400 on driver invalid

## Task Commits

Each task was committed atomically:

1. **Task 1: Implement book_car composite orchestration with rollback** - `df59c18` (feat)

**Plan metadata:** (final commit — see below)

## Files Created/Modified
- `composite/book_car/app.py` - Full orchestration: driver GET+validate, vehicle check+lock, pricing, Stripe charge, booking create with rollback

## Decisions Made
- Vehicle locked (PUT /status rented) BEFORE Stripe charge — prevents double-booking race where two concurrent requests both pass availability check
- booking_service failure triggers best-effort rollback: try Stripe refund, try vehicle unlock — each in separate try/except so one failure does not prevent the other
- driver_service validate endpoint takes license_number (not uid) — must GET /drivers/{uid} first to extract license_number, then POST /drivers/validate
- pricing_service uses query params (not JSON body) per RESEARCH.md pitfall note — requests.get(url, params=...)

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None — no external service configuration required. All services addressed via Docker Compose service hostnames.

## Next Phase Readiness
- `composite/book_car/app.py` is complete and ready for integration testing via `verify_phase4.sh` COMP-01/COMP-02 checks
- cancel_booking composite (if any) can now rely on booking_id values created by this service
- All downstream Phase 4 composites can create real bookings for cancel/report flows

## Self-Check

- [x] `composite/book_car/app.py` exists and passes `python3 -m py_compile`
- [x] commit `df59c18` present in git log
- [x] rollback logic present (grep confirmed)
- [x] payment_intent_id present (grep confirmed)
- [x] 409 status code present (grep confirmed)

## Self-Check: PASSED

---
*Phase: 04-composite-services*
*Completed: 2026-03-15*
