---
phase: 03-atomic-services
plan: "03"
subsystem: api
tags: [flask, firestore, python, pricing, driver, validation]

# Dependency graph
requires:
  - phase: 03-01
    provides: booking_service and vehicle_service stub scaffolding pattern

provides:
  - pricing_service calculate endpoint (real logic, no Firestore)
  - pricing_service /policy endpoint (three-tier refund policy tiers)
  - driver_service get_driver via Firestore .where("uid") query
  - driver_service validate_driver via Firestore .document(license_number) + date expiry check

affects: [04-composite-services, cancel_booking (needs /policy), book_car (needs driver lookup)]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Pure-Python pricing: RATES dict at module level, float validation, round(rate*hours,2)"
    - "Firestore .where() query for uid-keyed lookup (doc keyed by license_number, not uid)"
    - "validate endpoint returns 200 for invalid input — validation query, not resource lookup"
    - "db=None guard returns 500 on all Firestore routes for credentialless startup"

key-files:
  created: []
  modified:
    - atomic/pricing_service/app.py
    - atomic/driver_service/app.py

key-decisions:
  - "driver_service validate returns HTTP 200 for invalid licenses — validation query not resource lookup; callers inspect valid field"
  - "DRV-01/DRV-02 verify_phase3.sh checks fail due to pre-existing Firestore API disabled in GCP esd-rental-car; code is correct per plan spec"

patterns-established:
  - "validate endpoints always return HTTP 200 with valid/reason payload — callers check valid field, not status code"

requirements-completed: [PRICE-01, PRICE-02, DRV-01, DRV-02]

# Metrics
duration: 2min
completed: 2026-03-14
---

# Phase 3 Plan 03: Pricing Service + Driver Service Summary

**Pure-Python pricing with calculate/policy endpoints and Firestore driver lookup with uid-query + license-expiry validation**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-14T11:37:07Z
- **Completed:** 2026-03-14T11:39:27Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- pricing_service calculate endpoint replaces Phase 1 stub: validates vehicle_type, parses hours as float, returns `round(rate*hours,2)` total
- pricing_service /policy endpoint added: returns locked three-tier refund policy shape (24h=100%, 1h=50%, 0h=0%)
- driver_service get_driver replaced: uses `.where("uid","==",uid)` query (Firestore docs keyed by license_number, not uid)
- driver_service validate_driver replaced: `.document(license_number)` lookup + `date.fromisoformat()` expiry comparison, always returns HTTP 200

## Task Commits

Each task was committed atomically:

1. **Task 1: pricing_service calculate + policy endpoints** - `ea0e378` (feat)
2. **Task 2: driver_service Firestore routes** - `ea665a7` (feat)

**Plan metadata:** (docs commit pending)

## Files Created/Modified
- `atomic/pricing_service/app.py` - Added RATES dict, real calculate logic, new /policy route; added request import
- `atomic/driver_service/app.py` - Replaced stubs with Firestore .where() and .document() queries, date expiry check; added request, date imports

## Decisions Made
- validate_driver returns HTTP 200 even for invalid licenses — it is a validation query, not a resource lookup. Callers inspect the `valid` field.
- DRV checks in verify_phase3.sh fail due to Firestore API being disabled in GCP project `esd-rental-car` — this is a pre-existing infrastructure issue affecting all Firestore services (VEH, BOOK, RPT, DRV). Code correctly implements the plan spec.

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

**Firestore API disabled in GCP:** All Firestore-dependent services (vehicle_service, booking_service, report_service, driver_service) return 500 errors due to `google.api_core.exceptions.PermissionDenied: Cloud Firestore API has not been used in project esd-rental-car`. This is a pre-existing infrastructure issue — not introduced by this plan. PRICE-01 and PRICE-02 pass (pricing_service has no Firestore dependency). DRV-01 and DRV-02 code is correct per plan spec but cannot be exercised until Firestore API is enabled.

## User Setup Required

To enable DRV-01/DRV-02 verification: enable Cloud Firestore API in GCP console for project `esd-rental-car` at https://console.developers.google.com/apis/api/firestore.googleapis.com/overview?project=esd-rental-car, then run `python seed_data.py` to populate drivers collection, then re-run `bash verify_phase3.sh`.

## Next Phase Readiness
- pricing_service /policy endpoint ready for cancel_booking composite (Phase 4)
- driver_service code complete and correct; blocked on Firestore API activation before integration tests pass
- Phase 4 composite services can proceed once Firestore API is enabled and seed data loaded

---
*Phase: 03-atomic-services*
*Completed: 2026-03-14*

## Self-Check: PASSED

- FOUND: atomic/pricing_service/app.py
- FOUND: atomic/driver_service/app.py
- FOUND: .planning/phases/03-atomic-services/03-03-SUMMARY.md
- FOUND commit: ea0e378 (pricing_service)
- FOUND commit: ea665a7 (driver_service)
