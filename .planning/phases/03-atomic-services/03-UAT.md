---
status: complete
phase: 03-atomic-services
source: [03-01-SUMMARY.md, 03-02-SUMMARY.md, 03-03-SUMMARY.md, 03-04-SUMMARY.md, 03-05-SUMMARY.md]
started: 2026-03-15T00:00:00Z
updated: 2026-03-15T00:10:00Z
---

## Current Test

[testing complete]

## Tests

### 1. Cold Start Smoke Test
expected: Kill any running containers. Run `docker compose up --build` from project root. All 5 atomic services start without crashing. Each /health endpoint returns 200.
result: pass

### 2. Smoke Test Script Exists
expected: `bash verify_phase3.sh` runs without syntax errors and prints 17+ named PASS/FAIL lines. Firestore FAILs are expected.
result: pass

### 3. Pricing Calculate - Valid Request
expected: `curl -s "http://localhost:5005/api/pricing/calculate?vehicle_type=sedan&hours=3"` returns HTTP 200 with JSON containing a `total` field. (pricing_service is on port 5005, not 5004; route is GET with query params not POST JSON)
result: pass

### 4. Pricing Calculate - Invalid Vehicle Type
expected: `curl -s "http://localhost:5005/api/pricing/calculate?vehicle_type=spaceship&hours=2"` returns HTTP 400 (invalid vehicle type rejected).
result: pass

### 5. Pricing Policy Endpoint
expected: `curl -s http://localhost:5005/api/pricing/policy` returns HTTP 200 with a JSON body describing the three-tier refund policy (24h=100%, 1h=50%, 0h=0%).
result: pass

### 6. Vehicle Service - List Vehicles
expected: `curl -s http://localhost:5001/api/vehicles` returns HTTP 200 with a JSON array, or 500 if Firestore API disabled — but the route must exist (no Flask 404).
result: pass

### 7. Vehicle Service - Update Status Route Exists
expected: `curl -s -X PUT "http://localhost:5001/api/vehicles/SOME-PLATE/status" -H "Content-Type: application/json" -d "{\"status\":\"available\"}"` returns 200, 404, or 500 — but NOT a Flask route-not-found 404.
result: pass

### 8. Booking Service - Create Booking Route Exists
expected: `curl -s -X POST http://localhost:5002/api/bookings -H "Content-Type: application/json" -d '{"user_uid":"u1","vehicle_id":"SBA1234A","vehicle_type":"sedan","pickup_datetime":"2026-03-15T10:00:00","hours":2,"total_price":50,"stripe_payment_intent_id":"pi_test"}'` returns 201 with booking ID.
result: pass

### 9. Booking Service - Active Booking Route Exists
expected: `curl -s http://localhost:5002/api/bookings/user/testuid/active` returns 200, 404 (no active booking), or 500 — NOT a wildcard routing bug 404.
result: pass

### 10. Driver Service - Validate Driver Route Exists
expected: `curl -s -X POST http://localhost:5003/api/drivers/validate -H "Content-Type: application/json" -d "{\"license_number\":\"SG123456\",\"uid\":\"testuid\"}"` returns HTTP 200 with a `valid` field, or 500 if Firestore disabled.
result: pass

### 11. Report Service - Create Report Route Exists
expected: `curl -s -X POST http://localhost:5004/api/reports -H "Content-Type: application/json" -d "{\"booking_id\":\"b1\",\"vehicle_id\":\"v1\",\"user_uid\":\"u1\",\"location\":\"SG\",\"description\":\"Test issue\"}"` returns 200/201, 400, or 500 — NOT a Flask 404. (report_service is on port 5004)
result: pass

### 12. Report Service - Pending Reports Route Exists
expected: `curl -s http://localhost:5004/api/reports/pending` returns 200 with a list or 500 if Firestore disabled — NOT a Flask routing collision with the wildcard /<report_id> route.
result: pass

## Summary

total: 12
passed: 12
issues: 0
pending: 0
skipped: 0

## Gaps

[none yet]
