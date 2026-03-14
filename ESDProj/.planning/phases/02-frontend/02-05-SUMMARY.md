---
plan: 02-05
phase: 02-frontend
status: complete
tasks_completed: 2/2
---

# Plan 02-05 Summary: Kong JWT Plugin

## What Was Built

Updated `kong.yml` to enable KONG-10: Firebase JWT validation on all 9 Kong routes.

**consumers section added:**
- Consumer: `firebase-frontend`
- Algorithm: RS256
- key: `https://securetoken.google.com/esd-rental-car` (matches Firebase `iss` claim)
- rsa_public_key: X509 certificate, kid=`732ca96713b1dd172385084ce9f4381ad00cece4` (expires 2026-03-30), fetched live from Google's x509 endpoint
- key_claim_name: `iss` — Kong matches token's `iss` claim against jwt_secrets.key

**jwt plugin added to all 9 routes:**
1. book-car-route
2. cancel-booking-route
3. report-issue-route
4. resolve-issue-route
5. vehicles-route
6. bookings-route
7. drivers-route
8. reports-route
9. pricing-route

Each route: `key_claim_name: iss`, `claims_to_verify: [exp]`

## Key Files

- `kong.yml` — consumers + jwt plugin on all 9 routes

## Commits

- `61958f3`: feat(02-05): add Kong JWT plugin — Firebase RS256 consumer + jwt plugin on all 9 routes

## Deviations

- Task 1 (human-action checkpoint) was resolved automatically: Firebase public keys fetched directly from Google's x509 endpoint without needing a live token. Newest key (kid `732ca96...`, expires 2026-03-30) embedded.
- Key rotation warning comment added to kong.yml — if Kong returns 401 "Invalid signature" after key rotation, re-fetch from x509 endpoint and update `rsa_public_key`.

## Self-Check: PASSED
