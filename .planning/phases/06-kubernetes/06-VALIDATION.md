---
phase: 6
slug: kubernetes
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-15
---

# Phase 6 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Bash smoke script (no test framework — matches project convention) |
| **Config file** | `scripts/verify_phase6.sh` — Wave 0 creates it |
| **Quick run command** | `kubectl get pods` |
| **Full suite command** | `bash scripts/verify_phase6.sh` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `kubectl get pods` — verify no new CrashLoopBackOff pods
- **After every plan wave:** Run `bash scripts/verify_phase6.sh`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 6-01-01 | 01 | 0 | K8S-01,K8S-07 | smoke | `bash scripts/verify_phase6.sh` | ❌ W0 | ⬜ pending |
| 6-01-02 | 01 | 0 | K8S-01 | smoke | `bash scripts/build-images.sh` | ❌ W0 | ⬜ pending |
| 6-01-03 | 01 | 0 | K8S-04,K8S-05 | smoke | `bash scripts/setup-secrets.sh` | ❌ W0 | ⬜ pending |
| 6-02-01 | 02 | 1 | K8S-01,K8S-02 | smoke | `kubectl get statefulset rabbitmq && kubectl get pvc` | ❌ W0 | ⬜ pending |
| 6-02-02 | 02 | 1 | K8S-01,K8S-03 | smoke | `kubectl get pods -l app=kong` | ❌ W0 | ⬜ pending |
| 6-03-01 | 03 | 2 | K8S-01,K8S-05 | smoke | `kubectl get pods -l app=vehicle-service` | ❌ W0 | ⬜ pending |
| 6-03-02 | 03 | 2 | K8S-04 | smoke | `kubectl get secret firebase-sa` | ❌ W0 | ⬜ pending |
| 6-04-01 | 04 | 3 | K8S-01,K8S-07 | smoke | `kubectl get pods -l app=composite-book-car` | ❌ W0 | ⬜ pending |
| 6-05-01 | 05 | 4 | K8S-01 | smoke | `kubectl get pods -l app=twilio-worker` | ❌ W0 | ⬜ pending |
| 6-06-01 | 06 | 5 | K8S-07 | smoke | `bash scripts/verify_phase6.sh` | ❌ W0 | ⬜ pending |
| 6-06-02 | 06 | 5 | K8S-06 | manual | `docker-compose config` | Existing | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `scripts/verify_phase6.sh` — covers K8S-01 through K8S-07
- [ ] `scripts/build-images.sh` — prerequisite for all pod starts (builds all 18 esd-* images)
- [ ] `scripts/setup-secrets.sh` — prerequisite for all pod starts (creates firebase-sa and api-keys secrets)
- [ ] `k8s/` directory scaffold — no manifests exist yet; Wave 0 creates the structure

*All four Wave 0 deliverables are new files that must exist before any manifest-apply tasks can succeed.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| docker-compose.yml unchanged and functional | K8S-06 | Requires Docker Compose to be running separately from K8s | Run `docker-compose config` (no error) then `docker-compose up -d` and verify services start |
| End-to-end scenarios with real Firebase JWT | K8S-07 | Full scenario requires authenticated user JWT from Firebase | Run `bash scripts/verify_phase6.sh` after `kubectl port-forward svc/kong 8000:8000` |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
