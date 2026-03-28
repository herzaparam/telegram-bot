---
phase: 15
slug: prometheus-metrics-instrumentation
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-29
---

# Phase 15 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.0.2+ with pytest-asyncio (asyncio_mode=auto) |
| **Config file** | pyproject.toml [tool.pytest.ini_options] |
| **Quick run command** | `pytest tests/test_monitoring/ tests/test_data/test_ingest.py tests/test_data/test_analyze.py tests/test_bot/ -x -q` |
| **Full suite command** | `pytest` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/test_monitoring/ tests/test_data/test_ingest.py tests/test_data/test_analyze.py tests/test_bot/ -x -q`
- **After every plan wave:** Run `pytest`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 15-01-01 | 01 | 1 | MON-10 | unit | `pytest tests/test_data/test_ingest.py -x -q` | ✅ (needs new cases) | ⬜ pending |
| 15-01-02 | 01 | 1 | MON-10 | unit | `pytest tests/test_data/test_analyze.py -x -q` | ✅ (needs new cases) | ⬜ pending |
| 15-01-03 | 01 | 1 | MON-10 | unit | `pytest tests/test_data/test_ingest.py -x -q` | ✅ (needs new cases) | ⬜ pending |
| 15-01-04 | 01 | 1 | MON-09 | unit | `pytest tests/test_bot/ -x -q` | ✅ (needs new cases) | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Existing infrastructure covers all phase requirements. Test files for ingest, analyze, and bot already exist. New test cases will be added to existing files.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Grafana dashboards show non-empty panels | MON-09, MON-10 | Requires running Docker stack with Grafana | Start `docker compose -f docker-compose.prod.yml up`, run pipeline, check Grafana at :3000 |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
