---
phase: 04-composite-services
plan: "02"
subsystem: payments
tags: [stripe, flask, python, mock-failover, psp]

# Dependency graph
requires:
  - phase: 04-01
    provides: stripe library added to stripe_wrapper/requirements.txt

provides:
  - stripe_wrapper app.py with real Stripe PaymentIntent.create (test mode) + mock failover
  - stripe_wrapper app.py with real Stripe Refund.create + mock failover
  - mock_ prefix detection in refund endpoint to short-circuit fake IDs from real Stripe API
  - Consistent JSON response shape for charge and refund regardless of real vs fallback path

affects: [composite/book_car, composite/cancel_booking, phase-05-realtime]

# Tech tracking
tech-stack:
  added: [stripe Python SDK (used in app.py; already in requirements.txt from 04-01)]
  patterns: [PSP failover — try real Stripe SDK → except any exception → return mock_<uuid> with provider="fallback"]

key-files:
  created: []
  modified: [wrappers/stripe_wrapper/app.py]

key-decisions:
  - "pm_card_visa used as default payment_method — Stripe test-mode token that always succeeds"
  - "automatic_payment_methods enabled with allow_redirects=never — required for server-side confirm without return_url"
  - "mock_ prefix check in refund endpoint prevents sending fake IDs to real Stripe Refund.create API"
  - "provider field (stripe|fallback) in all responses documents PSP failover architecture for markers"
  - "Amount conversion: dollars → integer cents (Stripe requires cents) done in both endpoints"

patterns-established:
  - "PSP failover: try real Stripe SDK call → except Exception → return mock_<uuid> response with same JSON shape"
  - "Mock ID detection: startswith('mock_') short-circuits to mock response before calling real API"

requirements-completed: [COMP-01, COMP-02, COMP-05, COMP-06]

# Metrics
duration: 5min
completed: 2026-03-14
---

# Phase 4 Plan 02: stripe_wrapper Real Stripe SDK with Mock Failover Summary

**stripe_wrapper upgraded from Phase 1 stub to real Stripe PaymentIntent + Refund calls (test mode) with mock_uuid fallover — composites get consistent JSON shape regardless of Stripe availability**

## Performance

- **Duration:** ~5 min
- **Started:** 2026-03-14T18:31:21Z
- **Completed:** 2026-03-14T18:36:00Z
- **Tasks:** 1
- **Files modified:** 1

## Accomplishments
- Replaced Phase 1 stub (hardcoded `pi_stub_phase1`) with real `stripe.PaymentIntent.create` in test mode
- Real `stripe.Refund.create` with `payment_intent` + optional `amount` in cents
- Mock failover on any exception: returns `mock_<uuid>` or `mock_re_<uuid>` with `provider="fallback"`
- Mock ID short-circuit: refund detects `payment_intent_id.startswith("mock_")` and returns mock refund immediately without calling Stripe API
- `provider` field on all responses (`stripe` or `fallback`) documents PSP failover architecture

## Task Commits

Each task was committed atomically:

1. **Task 1: Implement stripe_wrapper with real Stripe SDK and mock failover** - `1878517` (feat)

## Files Created/Modified
- `wrappers/stripe_wrapper/app.py` - Real Stripe charge/refund with try/except mock failover; both endpoints return {status, payment_intent_id/refund_id, provider}

## Decisions Made
- `pm_card_visa` used as default payment_method — Stripe's built-in test-mode token, always succeeds without a real card
- `automatic_payment_methods={"enabled": True, "allow_redirects": "never"}` required for server-side `confirm=True` without a `return_url`
- mock_ prefix detection prevents sending mock IDs created by charge fallover to the real Stripe Refund API (which would reject them)
- Dollar-to-cents conversion: `int(round(amount_dollars * 100))` in both charge and refund for Stripe integer cents requirement
- `provider` field added to all responses for academic visibility into which path (real vs mock) was taken

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required
None - STRIPE_SECRET_KEY is already declared in docker-compose.yml env section (set to Stripe test-mode key). No additional configuration required.

## Self-Check

- [x] `wrappers/stripe_wrapper/app.py` written and verified
- [x] Python syntax check passed (`python3 -m py_compile`)
- [x] mock_ pattern present in both charge and refund handlers
- [x] provider field present in all jsonify() response calls
- [x] Commit 1878517 exists

## Next Phase Readiness
- stripe_wrapper now ready for composites: book_car (charge) and cancel_booking (refund) can call it at port 6202
- Both endpoints handle missing/bad Stripe credentials gracefully via mock fallover — composites always get a usable payment_intent_id
- Phase 4 Plan 03+ can proceed with composite service implementation against this wrapper

---
*Phase: 04-composite-services*
*Completed: 2026-03-14*
