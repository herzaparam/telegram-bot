---
phase: 11
slug: asset-discovery-due-diligence
status: draft
nyquist_compliant: true
wave_0_complete: true
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

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | Status |
|---------|------|------|-------------|-----------|-------------------|--------|
| 11-01-01 | 01 | 1 | DISC-01, DUED-01-04 | import | `python -c "from src.db.models import DiscoveryCandidate, OwnershipSnapshot, DueDiligenceReport; print('Models OK')" && python -c "from src.engines.valuation import IDX_SECTOR_MAP; assert len(IDX_SECTOR_MAP) >= 50; print('Sector map OK')"` | pending |
| 11-01-02 | 01 | 1 | DISC-01 | import | `python -c "import importlib.util; [importlib.util.spec_from_file_location('m', f).loader.exec_module(importlib.util.module_from_spec(importlib.util.spec_from_file_location('m', f))) for f in ['src/db/migrations/versions/012_discovery_candidates.py', 'src/db/migrations/versions/013_ownership_due_diligence.py']]"` | pending |
| 11-02-01 | 02 | 2 | DISC-01, DISC-02, DISC-03 | unit | `python -m pytest tests/test_data/test_discovery.py -x --tb=short` | pending |
| 11-03-01 | 03 | 2 | DUED-01, DUED-02, DUED-03, DUED-04 | unit | `python -m pytest tests/test_data/test_due_diligence.py tests/test_data/test_ownership_fetcher.py -x --tb=short` | pending |
| 11-04-01 | 04 | 3 | LLM-06, REPT-07 | unit | `python -m pytest tests/test_llm/test_prompts.py tests/test_report/test_formatter_discovery.py -x --tb=short` | pending |
| 11-04-02 | 04 | 3 | DISC-04, LLM-06 | import | `python -c "from src.pipeline.main import async_main; print('Pipeline import OK')" && python -c "from src.data.report import send_daily_report; import inspect; sig = inspect.signature(send_daily_report); assert 'discoveries' in sig.parameters; print('Report sig OK')"` | pending |
| 11-05-01 | 05 | 4 | TBOT-06, TBOT-10, TBOT-11 | import | `python -c "from src.bot.handlers.discover import discover_handler; from src.bot.handlers.duediligence import duediligence_handler; from src.bot.handlers.compare import compare_handler; print('All handlers importable')"` | pending |
| 11-05-02 | 05 | 4 | TBOT-06, TBOT-10, TBOT-11 | unit | `python -m pytest tests/test_bot/test_discover_handler.py tests/test_bot/test_dd_handler.py tests/test_bot/test_compare_handler.py -x --tb=short` | pending |

*Status: pending · green · red · flaky*

---

## Wave 0 Requirements

All plan tasks include concrete `<automated>` verification commands. No Wave 0 test scaffolding required -- tests are created as part of plan tasks themselves (Plans 02, 03, 04, 05 each create their own test files).

- [x] Wave 0 not needed -- all tasks self-contained with tests

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

- [x] All tasks have `<automated>` verify commands
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 not needed -- tests bundled in plan tasks
- [x] No watch-mode flags
- [x] Feedback latency < 45s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
