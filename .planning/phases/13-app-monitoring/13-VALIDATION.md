---
phase: 13
slug: app-monitoring
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-28
---

# Phase 13 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.x with pytest-asyncio |
| **Config file** | `pyproject.toml` |
| **Quick run command** | `python -m pytest tests/ -x -q --timeout=30` |
| **Full suite command** | `python -m pytest tests/ -q --timeout=60` |
| **Estimated runtime** | ~45 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/ -x -q --timeout=30`
- **After every plan wave:** Run `python -m pytest tests/ -q --timeout=60`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 45 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 13-01-01 | 01 | 1 | D-07,D-08 | unit | `pytest tests/test_metrics.py` | ❌ W0 | ⬜ pending |
| 13-01-02 | 01 | 1 | D-08 | unit | `pytest tests/test_metrics.py -k migration` | ❌ W0 | ⬜ pending |
| 13-02-01 | 02 | 1 | D-01,D-02,D-03 | unit | `pytest tests/test_alerting.py` | ❌ W0 | ⬜ pending |
| 13-02-02 | 02 | 1 | D-04 | unit | `pytest tests/test_health.py` | ❌ W0 | ⬜ pending |
| 13-03-01 | 03 | 2 | D-10,D-11,D-12 | unit | `pytest tests/test_error_tracking.py` | ❌ W0 | ⬜ pending |
| 13-03-02 | 03 | 2 | D-05,D-06 | unit | `pytest tests/test_monitoring.py` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_metrics.py` — stubs for pipeline metrics model, recording, and query
- [ ] `tests/test_alerting.py` — stubs for alert delivery, deduplication, triggers
- [ ] `tests/test_health.py` — stubs for expanded health endpoint
- [ ] `tests/test_error_tracking.py` — stubs for exception handlers
- [ ] `tests/test_monitoring.py` — stubs for missed-run detection

*Existing test infrastructure (pytest, conftest.py, aiosqlite fixtures) covers framework needs.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Telegram alert delivery | D-01 | Requires live Telegram bot token and chat | Send test alert via `/test-alert` command, verify message arrives |
| Missed-run detection | D-06 | Requires waiting for expected pipeline time to pass | Skip a pipeline run, verify bot sends missed-run alert |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 45s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
