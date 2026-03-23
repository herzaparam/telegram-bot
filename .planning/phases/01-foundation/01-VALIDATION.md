---
phase: 1
slug: foundation
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-23
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.0.2 + pytest-asyncio 1.3.0 |
| **Config file** | None — Wave 0 must create `pyproject.toml [tool.pytest.ini_options]` |
| **Quick run command** | `uv run pytest tests/ -x -q` |
| **Full suite command** | `uv run pytest tests/ -v --tb=short` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/ -x -q`
- **After every plan wave:** Run `uv run pytest tests/ -v --tb=short`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 1-01-01 | 01 | 1 | DATA-04 | integration | `uv run pytest tests/test_pipeline/test_runner.py::test_restart_from_checkpoint -x` | ❌ W0 | ⬜ pending |
| 1-01-02 | 01 | 1 | DATA-04 | integration | `uv run pytest tests/test_pipeline/test_runner.py::test_resume_after_kill -x` | ❌ W0 | ⬜ pending |
| 1-01-03 | 01 | 1 | DATA-05 | unit | `uv run pytest tests/test_db/test_models.py::test_pipeline_runs_state_tracking -x` | ❌ W0 | ⬜ pending |
| 1-01-04 | 01 | 1 | DATA-05 | unit | `uv run pytest tests/test_db/test_models.py::test_pipeline_asset_runs -x` | ❌ W0 | ⬜ pending |
| 1-01-05 | 01 | 1 | DATA-06 | unit | `uv run pytest tests/test_pipeline/test_tiers.py::test_tier_failure_handling -x` | ❌ W0 | ⬜ pending |
| 1-01-06 | 01 | 1 | SC-1 | smoke | `docker compose -f docker-compose.prod.yml up -d && docker compose -f docker-compose.prod.yml ps` | Manual | ⬜ pending |
| 1-01-07 | 01 | 1 | SC-3 | unit | `uv run pytest tests/test_llm/test_client.py::test_fallback_returns_unavailable -x` | ❌ W0 | ⬜ pending |
| 1-01-08 | 01 | 1 | SC-5 | unit | `uv run pytest tests/test_db/test_models.py::test_decision_no_lookahead_bias -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `pyproject.toml [tool.pytest.ini_options]` — configure asyncio_mode = "auto"
- [ ] `tests/conftest.py` — shared fixtures (async db session, test settings, mock LLM)
- [ ] `tests/test_pipeline/test_runner.py` — covers DATA-04
- [ ] `tests/test_pipeline/test_tiers.py` — covers DATA-06
- [ ] `tests/test_db/test_models.py` — covers DATA-05, SC-5
- [ ] `tests/test_llm/test_client.py` — covers SC-3
- [ ] `tests/test_config.py` — covers settings loading
- [ ] Dev dependencies: `uv add --dev pytest pytest-asyncio`

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| docker compose up starts 3 services with health checks | SC-1 | Requires running Docker daemon | Run `docker compose -f docker-compose.prod.yml up -d`, verify all 3 services healthy with `docker compose ps` |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
