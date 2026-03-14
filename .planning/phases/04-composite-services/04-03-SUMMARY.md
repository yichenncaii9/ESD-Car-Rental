---
phase: 04-composite-services
plan: "03"
subsystem: external-api-wrappers
tags: [openai, googlemaps, wrapper, mock-fallback, severity-classification, reverse-geocoding]
dependency_graph:
  requires: [04-01]
  provides: [openai_wrapper real GPT-3.5-turbo evaluate endpoint, googlemaps_wrapper real reverse geocode endpoint]
  affects: [composite/report_issue]
tech_stack:
  added: [openai SDK (openai.OpenAI), googlemaps SDK (googlemaps.Client)]
  patterns: [mock failover — try real API, except return fallback with provider=fallback]
key_files:
  modified:
    - wrappers/openai_wrapper/app.py
    - wrappers/googlemaps_wrapper/app.py
decisions:
  - "googlemaps imported inside try block so import failure triggers mock fallback automatically"
  - "openai_wrapper validates GPT response is low/medium/high; clamps to medium if unexpected text returned"
  - "googlemaps_wrapper returns coordinate string '{lat},{lng}' as fallback address — usable by openai_wrapper as location context"
metrics:
  duration: "56s"
  completed_date: "2026-03-14"
  tasks_completed: 2
  files_modified: 2
---

# Phase 04 Plan 03: External API Wrappers (OpenAI + Google Maps) Summary

**One-liner:** Replaced Phase 1 stubs with real OpenAI GPT-3.5-turbo severity classification and Google Maps reverse geocoding, both with mock failover returning provider=fallback.

## What Was Built

### openai_wrapper (port 6200)

`POST /api/openai/evaluate` now calls `client.chat.completions.create` with GPT-3.5-turbo. A system prompt instructs the model to classify vehicle incident severity as exactly one of: `low`, `medium`, or `high`. The user message contains the incident description and address. `temperature=0` ensures deterministic output; `max_tokens=10` limits the response to a single word. The response is validated — if GPT returns anything other than the three expected values, it is clamped to `medium` as a safe default.

Mock fallback: any exception (invalid API key, network error, model overload) returns `{"status":"ok","severity":"medium","provider":"fallback"}`.

### googlemaps_wrapper (port 6201)

`POST /api/maps/geocode` now calls `gmaps.reverse_geocode((float(lat), float(lng)))` and returns `results[0]["formatted_address"]`. Input validation returns HTTP 400 if `lat` or `lng` is missing. The `googlemaps` library is imported inside the `try` block so an import failure (e.g., missing package) also falls through to mock.

Mock fallback: any exception returns `{"status":"ok","address":"{lat},{lng}","provider":"fallback"}`. The coordinate string is a usable fallback — `report_issue` composite passes it to openai_wrapper as location context.

## Commits

| Task | Commit | Description |
|------|--------|-------------|
| 1    | 07b6eb6 | feat(04-03): implement openai_wrapper with GPT-3.5-turbo severity classification and mock fallback |
| 2    | d9c301a | feat(04-03): implement googlemaps_wrapper with real reverse geocoding and mock fallback |

## Verification

- Both files pass `python3 -m py_compile` syntax check
- Both files contain `fallback` and `provider` in jsonify responses
- No Phase 1 stub code remains in either file
- Docker compose endpoints verified structurally (live test requires valid API keys)

## Deviations from Plan

None — plan executed exactly as written.

## Self-Check: PASSED

- `/Applications/MAMP/htdocs/y2s2/ESD/ESDProj/wrappers/openai_wrapper/app.py` — exists, syntax OK, fallback present
- `/Applications/MAMP/htdocs/y2s2/ESD/ESDProj/wrappers/googlemaps_wrapper/app.py` — exists, syntax OK, fallback present
- Commit 07b6eb6 — verified in git log
- Commit d9c301a — verified in git log
