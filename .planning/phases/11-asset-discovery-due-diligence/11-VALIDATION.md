---
phase: 11
slug: asset-discovery-due-diligence
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-26
---

# Phase 11 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | pyproject.toml |
| **Quick run command** | `python -m pytest tests/ -x -q --timeout=30` |
| **Full suite command** | `python -m pytest tests/ --timeout=60` |
| **Estimated runtime** | ~45 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/ -x -q --timeout=30`
- **After every plan wave:** Run `python -m pytest tests/ --timeout=60`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 45 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 11-01-01 | 01 | 1 | DISC-01 | unit | `pytest tests/test_discovery/ -k stock_scanner` | ❌ W0 | ⬜ pending |
| 11-01-02 | 01 | 1 | DISC-02 | unit | `pytest tests/test_discovery/ -k crypto_scanner` | ❌ W0 | ⬜ pending |
| 11-01-03 | 01 | 1 | DISC-03 | unit | `pytest tests/test_discovery/ -k ranking` | ❌ W0 | ⬜ pending |
| 11-02-01 | 02 | 1 | DUED-01 | unit | `pytest tests/test_due_diligence/ -k sector` | ❌ W0 | ⬜ pending |
| 11-02-02 | 02 | 1 | DUED-02 | unit | `pytest tests/test_due_diligence/ -k ownership` | ❌ W0 | ⬜ pending |
| 11-02-03 | 02 | 1 | DUED-03 | unit | `pytest tests/test_due_diligence/ -k management` | ❌ W0 | ⬜ pending |
| 11-03-01 | 03 | 2 | TBOT-06 | unit | `pytest tests/test_bot/ -k discover` | ❌ W0 | ⬜ pending |
| 11-03-02 | 03 | 2 | TBOT-11 | unit | `pytest tests/test_bot/ -k duediligence` | ❌ W0 | ⬜ pending |
| 11-03-03 | 03 | 2 | TBOT-10 | unit | `pytest tests/test_bot/ -k compare` | ❌ W0 | ⬜ pending |
| 11-04-01 | 04 | 2 | LLM-06 | unit | `pytest tests/test_llm/ -k dd_flags` | ❌ W0 | ⬜ pending |
| 11-04-02 | 04 | 2 | REPT-07 | unit | `pytest tests/test_report/ -k opportunities` | ❌ W0 | ⬜ pending |
| 11-04-03 | 04 | 2 | DISC-04 | unit | `pytest tests/test_report/ -k discovery_section` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_discovery/` — test stubs for DISC-01 through DISC-04
- [ ] `tests/test_due_diligence/` — test stubs for DUED-01 through DUED-04
- [ ] `tests/test_bot/test_discover.py` — test stubs for TBOT-06
- [ ] `tests/test_bot/test_duediligence.py` — test stubs for TBOT-11
- [ ] `tests/test_bot/test_compare.py` — test stubs for TBOT-10

*Existing test infrastructure (pytest, conftest.py) covers framework needs.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| IDX disclosure scraping works with live data | DUED-02 | Depends on idx.co.id availability | Run `python -m src.data.due_diligence --test BBCA` and verify ownership data |
| yfinance bulk download handles rate limits | DISC-01 | Depends on Yahoo Finance rate limits | Run discovery scanner with full IHSG list, verify no 429 errors |
| CoinGecko top 100 fetch works | DISC-02 | Depends on CoinGecko API availability | Run crypto scanner, verify 100 results returned |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 45s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
