---
phase: 12
slug: portfolio-risk-advanced-commands
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-27
---

# Phase 12 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.x with pytest-asyncio |
| **Config file** | `pyproject.toml` |
| **Quick run command** | `uv run pytest tests/ -x -q --timeout=30` |
| **Full suite command** | `uv run pytest tests/ -q --timeout=60` |
| **Estimated runtime** | ~45 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/ -x -q --timeout=30`
- **After every plan wave:** Run `uv run pytest tests/ -q --timeout=60`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 45 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 12-01-01 | 01 | 1 | RISK-01 | unit | `uv run pytest tests/test_risk/ -q` | ❌ W0 | ⬜ pending |
| 12-01-02 | 01 | 1 | RISK-02 | unit | `uv run pytest tests/test_risk/ -q` | ❌ W0 | ⬜ pending |
| 12-01-03 | 01 | 1 | RISK-03 | unit | `uv run pytest tests/test_risk/ -q` | ❌ W0 | ⬜ pending |
| 12-01-04 | 01 | 1 | RISK-04 | unit | `uv run pytest tests/test_risk/ -q` | ❌ W0 | ⬜ pending |
| 12-01-05 | 01 | 1 | RISK-05 | unit | `uv run pytest tests/test_risk/ -q` | ❌ W0 | ⬜ pending |
| 12-02-01 | 02 | 1 | TBOT-12 | unit | `uv run pytest tests/test_bot/ -q` | ❌ W0 | ⬜ pending |
| 12-02-02 | 02 | 1 | REPT-06 | unit | `uv run pytest tests/test_report/ -q` | ❌ W0 | ⬜ pending |
| 12-03-01 | 03 | 2 | TBOT-08 | unit | `uv run pytest tests/test_data/ -q` | ❌ W0 | ⬜ pending |
| 12-04-01 | 04 | 2 | FUND-01 | unit | `uv run pytest tests/test_bot/ -q` | ❌ W0 | ⬜ pending |
| 12-04-02 | 04 | 2 | FUND-02 | unit | `uv run pytest tests/test_bot/ -q` | ❌ W0 | ⬜ pending |
| 12-04-03 | 04 | 2 | FUND-03 | unit | `uv run pytest tests/test_bot/ -q` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_risk/` — new test directory for risk module
- [ ] `tests/test_risk/conftest.py` — fixtures with sample price DataFrames, mock watchlist
- [ ] `tests/test_risk/test_portfolio.py` — stubs for correlation, VaR, concentration, stress
- [ ] `tests/test_data/test_backtest.py` — stubs for backtest replay

*Existing infrastructure covers Telegram handler and report formatter testing.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| /portfolio Telegram output formatting | TBOT-12 | Requires visual check of heatmap rendering in Telegram | Send /portfolio in test chat, verify heatmap grid renders correctly |
| /backtest long-running progress | TBOT-08 | Requires timing check of LLM replay pipeline | Run /backtest BTC 7d, verify completion within reasonable time |
| Stress test scenario accuracy | RISK-05 | Historical drawdown data validation | Cross-check 2020 COVID drawdown % against known market data |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 45s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
