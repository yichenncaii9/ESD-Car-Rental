---
phase: 03-atomic-services
plan: "02"
subsystem: vehicle_service
tags: [firestore, flask, atomic-service, tdd]
dependency_graph:
  requires: ["03-01"]
  provides: ["vehicle_service Firestore read/write", "GET /api/vehicles", "GET /api/vehicles/<id>", "PUT /api/vehicles/<id>/status"]
  affects: ["frontend BookCarView", "composite book_car (Phase 4)", "composite cancel_booking (Phase 4)"]
tech_stack:
  added: []
  patterns: ["Firestore document stream", "db.collection().stream()", "db.collection().document(id).get()", "doc_ref.update()"]
key_files:
  created: ["atomic/vehicle_service/test_app.py"]
  modified: ["atomic/vehicle_service/app.py"]
decisions:
  - "vehicle doc returns plate_number from doc.to_dict() directly — plate_number is a field in the document data, no need to inject doc.id separately"
  - "GET /api/vehicles returns all vehicles regardless of status — frontend filters client-side"
  - "db=None guard returns 500 on all three routes — allows container startup without credentials during dev"
metrics:
  duration: "~3 minutes"
  completed: "2026-03-14"
  tasks_completed: 1
  files_changed: 2
---

# Phase 3 Plan 02: Vehicle Service Firestore Routes Summary

**One-liner:** Replaced Phase 1 stubs in vehicle_service/app.py with real Firestore read/write using db.collection("vehicles").stream(), .document(id).get(), and doc_ref.update().

## What Was Built

Three Flask routes in `atomic/vehicle_service/app.py` now perform real Firestore operations:

- **GET /api/vehicles** — streams all documents from the `vehicles` collection, returns `[{"id": doc.id, ...doc.to_dict()}]`
- **GET /api/vehicles/<vehicle_id>** — fetches a single document by plate number (natural key), returns 404 if not found
- **PUT /api/vehicles/<vehicle_id>/status** — validates `status` field (400 if missing), checks document exists (404 if not), calls `doc_ref.update({"status": new_status})`

All three routes guard `db is None` with a 500 response, allowing container startup without Firebase credentials.

## TDD Results

| Phase | Result |
|-------|--------|
| RED   | 13 tests written, all failing against Phase 1 stubs |
| GREEN | All 13 tests pass after implementation |

Tests use `unittest.mock` to patch Firestore — no real credentials required for unit tests.

## Verification Status

**Unit tests:** 13/13 PASS (mock-based, run locally)

**verify_phase3.sh VEH-01, VEH-02, VEH-03:** BLOCKED — Cloud Firestore API is disabled in GCP project `esd-rental-car`. The container starts healthy (`/health` returns 200) but Firestore calls return `403 SERVICE_DISABLED`.

**To unblock runtime verification:**
1. Enable Firestore API: https://console.developers.google.com/apis/api/firestore.googleapis.com/overview?project=esd-rental-car
2. Run `python3 seed_data.py` (once, from project root, with `firebase-service-account.json` present)
3. Re-run `bash verify_phase3.sh 2>&1 | grep -E "PASS|FAIL: VEH"`

## Deviations from Plan

**1. [Auth Gate] Firestore API disabled in GCP project**
- **Found during:** Task 1 verification
- **Issue:** `google.api_core.exceptions.PermissionDenied: 403 Cloud Firestore API has not been used in project esd-rental-car`
- **Fix:** Code is correct — this is a GCP console activation step, not a code fix
- **Impact:** verify_phase3.sh VEH checks cannot pass until API is enabled and seed data is loaded
- **Action required:** Enable Firestore API in GCP console, run seed_data.py

**2. Flask install in local venv**
- **Found during:** TDD RED phase
- **Issue:** Local venv at `/Applications/MAMP/htdocs/y2s2/.venv` did not have Flask installed — needed for running unit tests locally
- **Fix:** `pip3 install flask flask-cors` — one-time local setup, no project files changed

## Decisions Made

- `GET /api/vehicles` returns all vehicles without status filtering — BookCarView filters client-side (consistent with Phase 2 frontend decision)
- `doc.to_dict()` for vehicle documents already contains `plate_number` as a field, so no need to inject `doc.id` into the response separately for `GET /api/vehicles/<id>` — only `GET /api/vehicles` (list) adds `"id": doc.id` for convenience
- `db=None` guard returns 500 rather than falling through to the Firestore call, giving a clear error in development without credentials

## Self-Check

### Files created/modified
- `atomic/vehicle_service/app.py` — FOUND (modified with Firestore routes)
- `atomic/vehicle_service/test_app.py` — FOUND (created, 13 unit tests)

### Commits
- `8354bfc` test(03-02): add failing tests for vehicle_service Firestore routes
- `3cc5f90` feat(03-02): implement vehicle_service Firestore routes

## Self-Check: PASSED
