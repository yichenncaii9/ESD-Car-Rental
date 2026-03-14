---
phase: 4
slug: composite-services
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-15
---

# Phase 4 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | bash smoke tests (matching Phase 3 pattern: `verify_phase3.sh`) |
| **Config file** | none — standalone shell script |
| **Quick run command** | `bash verify_phase4.sh` |
| **Full suite command** | `bash verify_phase4.sh` |
| **Estimated runtime** | ~60 seconds |

---

## Sampling Rate

- **After every task commit:** Run `curl -sf http://localhost:6001/health && curl -sf http://localhost:6002/health && curl -sf http://localhost:6003/health && curl -sf http://localhost:6004/health`
- **After every plan wave:** Run `bash verify_phase4.sh`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 60 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 4-01-01 | 01 | 1 | COMP-01 | smoke | `curl -sf -X POST http://localhost:8000/api/book-car` | ❌ W0 | ⬜ pending |
| 4-01-02 | 01 | 1 | COMP-02 | smoke | `curl ... ; curl http://localhost:5001/api/vehicles/<id>` check status | ❌ W0 | ⬜ pending |
| 4-02-01 | 02 | 1 | COMP-03 | smoke | `curl -sf -X POST http://localhost:8000/api/cancel-booking` with cancelled booking_id | ❌ W0 | ⬜ pending |
| 4-02-02 | 02 | 1 | COMP-04 | smoke | Check `refund_amount` in cancel response | ❌ W0 | ⬜ pending |
| 4-02-03 | 02 | 1 | COMP-05 | smoke | GET booking + GET vehicle after cancel | ❌ W0 | ⬜ pending |
| 4-02-04 | 02 | 1 | COMP-06 | smoke | Trigger with invalid payment_intent_id | ❌ W0 | ⬜ pending |
| 4-02-05 | 02 | 1 | COMP-07 | smoke | JSON field check on response | ❌ W0 | ⬜ pending |
| 4-03-01 | 03 | 2 | COMP-08 | smoke | Check report document via GET /api/reports/<id> | ❌ W0 | ⬜ pending |
| 4-03-02 | 03 | 2 | COMP-09 | manual | Check RabbitMQ management UI at localhost:15672 | ❌ W0 | ⬜ pending |
| 4-03-03 | 03 | 2 | COMP-10 | smoke | JSON field check on report-issue response | ❌ W0 | ⬜ pending |
| 4-04-01 | 04 | 2 | COMP-11 | smoke | JSON field check + GET report | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `verify_phase4.sh` — full smoke test covering all COMP-01 through COMP-11
- [ ] `wrappers/twilio_wrapper/` HTTP Flask service on port 6203 — needed before resolve_issue tests can run
- [ ] `pika` added to `composite/report_issue/requirements.txt`

*Wave 0 must create these artifacts before any implementation tasks begin.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| RabbitMQ "report_topic" receives message after report-issue call | COMP-09 | RabbitMQ management UI inspection required | Check localhost:15672, verify "report_topic" exchange has pending message with routing key "report.new" |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
