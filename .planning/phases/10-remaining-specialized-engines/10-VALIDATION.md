---
phase: 10
slug: remaining-specialized-engines
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-25
---

# Phase 10 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x |
| **Config file** | pyproject.toml `[tool.pytest.ini_options]` |
| **Quick run command** | `python -m pytest tests/ -x -q --timeout=30` |
| **Full suite command** | `python -m pytest tests/ -v --timeout=60` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/ -x -q --timeout=30`
- **After every plan wave:** Run `python -m pytest tests/ -v --timeout=60`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 10-01-01 | 01 | 1 | ENGN-04 | unit | `pytest tests/test_engines/test_ml_engine.py` | ❌ W0 | ⬜ pending |
| 10-01-02 | 01 | 1 | ENGN-04 | unit | `pytest tests/test_engines/test_ml_training.py` | ❌ W0 | ⬜ pending |
| 10-02-01 | 02 | 1 | ENGN-06 | unit | `pytest tests/test_engines/test_onchain_engine.py` | ❌ W0 | ⬜ pending |
| 10-03-01 | 03 | 1 | ENGN-08 | unit | `pytest tests/test_engines/test_behavioral_engine.py` | ❌ W0 | ⬜ pending |
| 10-03-02 | 03 | 1 | ENGN-11 | unit | `pytest tests/test_engines/test_network_engine.py` | ❌ W0 | ⬜ pending |
| 10-03-03 | 03 | 1 | ENGN-14 | unit | `pytest tests/test_engines/test_emerging_engine.py` | ❌ W0 | ⬜ pending |
| 10-04-01 | 04 | 1 | ENGN-07 | unit | `pytest tests/test_engines/test_options_engine.py` | ❌ W0 | ⬜ pending |
| 10-04-02 | 04 | 1 | ENGN-10 | unit | `pytest tests/test_engines/test_altdata_engine.py` | ❌ W0 | ⬜ pending |
| 10-04-03 | 04 | 1 | ENGN-13 | unit | `pytest tests/test_engines/test_gametheory_engine.py` | ❌ W0 | ⬜ pending |
| 10-05-01 | 05 | 2 | ALL | integration | `pytest tests/test_pipeline/test_15_engines.py` | ❌ W0 | ⬜ pending |
| 10-05-02 | 05 | 2 | ALL | memory | `pytest tests/test_pipeline/test_memory_budget.py` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_engines/` — test stubs for all 8 new engines
- [ ] `tests/test_pipeline/test_15_engines.py` — integration test stub for full engine suite
- [ ] `tests/test_pipeline/test_memory_budget.py` — memory budget verification stub

*Existing pytest infrastructure covers framework and fixtures.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| ONNX model training | ENGN-04 | Requires historical data and training time | Run training CLI script, verify ONNX model outputs |
| DeFiLlama API availability | ENGN-06 | External API may be rate-limited | Verify TVL data returned for BTC, ETH, SOL |
| /scorecard 15-engine display | ALL | Visual formatting check | Run /scorecard, verify all 15 engines listed with correct status |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
