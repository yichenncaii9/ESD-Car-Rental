---
phase: 04-composite-services
plan: "05"
subsystem: api
tags: [flask, firestore, stripe, cancel-booking, refund, orchestration]

# Dependency graph
requires:
  - phase: 04-02
    provides: stripe_wrapper with real SDK and mock failover; payment_intent_id on bookings
  - phase: 03-atomic-services
    provides: booking_service (GET /bookings/<id>, PUT /bookings/<id>/status), vehicle_service (PUT /vehicles/<id>/status), pricing_service (GET /pricing/policy)

provides:
  - cancel_booking composite service at port 6002 (POST /api/cancel-booking)
  - Policy-based refund computation using pricing_service tiers (>24h=100%, 1-24h=50%, <1h=0%)
  - Graceful Stripe failure path: refund_status=pending_manual written directly to Firestore

affects:
  - phase-05-realtime
  - kong-routes
  - verify_phase4.sh COMP-03 through COMP-07

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Firestore direct write for fields not supported by atomic service PUT endpoints
    - Conservative fallback on upstream failure (0% refund if pricing_service unavailable)
    - db is not None guard before Firestore writes (matches Phase 3 pattern)

key-files:
  created: []
  modified:
    - composite/cancel_booking/app.py

key-decisions:
  - "Firestore direct write for refund_status: booking_service PUT /status only updates status field; composite writes refund_status directly to Firestore when Stripe fails"
  - "0% refund conservative fallback: if pricing_service is unreachable, refund_percent defaults to 0 (safe for business, avoids over-refunding)"
  - "refund_status=processed for 0% refund tier: no Stripe call needed, nothing to refund, status is cleanly processed"

patterns-established:
  - "Firestore direct write pattern: use db.collection().document().update() for fields the atomic service cannot set"
  - "Graceful Stripe failure: catch all exceptions, set pending_manual, continue with booking cancellation and vehicle release"

requirements-completed: [COMP-03, COMP-04, COMP-05, COMP-06, COMP-07]

# Metrics
duration: 2min
completed: 2026-03-15
---

# Phase 4 Plan 05: cancel_booking Composite Summary

**cancel_booking orchestration with policy-based refund tiers from pricing_service, Stripe refund via stripe_wrapper, and Firestore direct write for pending_manual refund_status when Stripe fails**

## Performance

- **Duration:** ~2 min
- **Started:** 2026-03-14T18:36:16Z
- **Completed:** 2026-03-14T18:38:30Z
- **Tasks:** 1
- **Files modified:** 1

## Accomplishments

- Replaced Phase 1 stub with full cancel_booking orchestration covering COMP-03 through COMP-07
- Policy-based refund: fetches tiers from pricing_service, sorts descending by hours_before, picks first matching tier; defaults to 0% on failure
- Stripe refund attempted for non-zero amounts; success=processed, exception/non-200=pending_manual written directly to Firestore
- Booking set to cancelled via booking_service PUT /status; vehicle released to available unconditionally after refund attempt

## Task Commits

Each task was committed atomically:

1. **Task 1: Implement cancel_booking composite with policy-based refund and Firestore direct write** - `12b264c` (feat)

**Plan metadata:** (docs commit follows)

## Files Created/Modified

- `composite/cancel_booking/app.py` - Full cancel_booking orchestration: validates booking status, computes refund via pricing policy tiers, calls stripe_wrapper, cancels booking, writes refund_status to Firestore directly, releases vehicle

## Decisions Made

- Firestore direct write for refund_status: booking_service PUT /status only updates the `status` field; the composite writes `refund_status: pending_manual` directly to Firestore when Stripe fails — matches RESEARCH.md critical pattern
- Conservative 0% refund fallback when pricing_service is unreachable — avoids over-refunding on upstream failure
- refund_status=processed for 0% refund tier — nothing to refund via Stripe, but the refund "action" is fully resolved

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- cancel_booking composite is complete; COMP-03 through COMP-07 requirements satisfied
- docker-compose up with all services will allow verify_phase4.sh COMP checks to run
- Phase 5 realtime services can proceed; cancel_booking does not depend on websocket layer

---
*Phase: 04-composite-services*
*Completed: 2026-03-15*
