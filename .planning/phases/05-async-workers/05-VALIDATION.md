---
phase: 5
slug: async-workers
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-15
---

# Phase 5 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Manual curl/HTTP testing + docker-compose logs observation |
| **Config file** | none — no automated test suite; Wave 0 creates verify script |
| **Quick run command** | `curl -sf http://localhost:6100/health` |
| **Full suite command** | `docker-compose logs twilio_wrapper activity_log websocket_server --tail=50` |
| **Estimated runtime** | ~10 seconds |

---

## Sampling Rate

- **After every task commit:** Run `curl -sf http://localhost:6100/health`
- **After every plan wave:** Run `docker-compose logs twilio_wrapper activity_log websocket_server --tail=50`
- **Before `/gsd:verify-work`:** All smoke tests pass + manual end-to-end test in ServiceDashboard
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 5-01-01 | 01 | 1 | WS-01, WS-03 | smoke | `curl -sf http://localhost:6100/health` | ❌ W0 | ⬜ pending |
| 5-01-02 | 01 | 1 | WS-03, WS-04 | smoke | `curl -X POST http://localhost:6100/notify -H "Content-Type: application/json" -d '{"report_id":"r1","event":"sms_sent","severity":"high","message":"test"}'` | ❌ W0 | ⬜ pending |
| 5-02-01 | 02 | 2 | WORK-05, WORK-06 | smoke | `docker-compose logs activity_log \| grep "Waiting for messages"` | ❌ W0 | ⬜ pending |
| 5-02-02 | 02 | 2 | WORK-06 | smoke | `docker-compose logs activity_log \| grep "Firestore write"` | ❌ W0 | ⬜ pending |
| 5-03-01 | 03 | 3 | WORK-01, WORK-02 | smoke | `docker-compose logs twilio_wrapper \| grep "Waiting for messages"` | ❌ W0 | ⬜ pending |
| 5-03-02 | 03 | 3 | WORK-02, WORK-03 | smoke | `docker-compose logs twilio_wrapper \| grep "Service team SMS sent"` | ❌ W0 | ⬜ pending |
| 5-03-03 | 03 | 3 | WORK-07 | smoke | `docker-compose logs twilio_wrapper \| grep "Connected to RabbitMQ"` | ❌ W0 | ⬜ pending |
| 5-e2e | all | final | WS-02, WS-04 | manual | Open ServiceDashboard, submit report, observe row update without page reload | manual-only | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `scripts/verify_phase5.sh` — shell script with curl smoke tests for WS-01, WS-03, WORK-01 through WORK-07 via log inspection
- [ ] No framework install needed — bash + curl available in all environments

*Note: Existing infrastructure covers websocket_server health check. Workers have no existing test framework.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Real-time push to ServiceDashboard without polling | WS-02, WS-04 | Browser Socket.IO client cannot be automated via curl | 1. Open ServiceDashboard in browser 2. Submit a new incident report 3. Observe that the row updates in-place without page reload |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
