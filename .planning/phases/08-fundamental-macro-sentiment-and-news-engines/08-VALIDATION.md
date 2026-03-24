---
phase: 8
slug: fundamental-macro-sentiment-and-news-engines
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-24
---

# Phase 8 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | `pyproject.toml` |
| **Quick run command** | `python -m pytest tests/ -x -q --timeout=30` |
| **Full suite command** | `python -m pytest tests/ -v --timeout=60` |
| **Estimated runtime** | ~45 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/ -x -q --timeout=30`
- **After every plan wave:** Run `python -m pytest tests/ -v --timeout=60`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 45 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 08-01-01 | 01 | 1 | ENGN-02 | unit | `pytest tests/test_engines/test_fundamental.py -v` | ❌ W0 | ⬜ pending |
| 08-01-02 | 01 | 1 | ENGN-12 | unit | `pytest tests/test_engines/test_macro.py -v` | ❌ W0 | ⬜ pending |
| 08-01-03 | 01 | 1 | ENGN-05 | unit | `pytest tests/test_engines/test_sentiment.py -v` | ❌ W0 | ⬜ pending |
| 08-01-04 | 01 | 1 | ENGN-09 | unit | `pytest tests/test_engines/test_event.py -v` | ❌ W0 | ⬜ pending |
| 08-02-01 | 02 | 2 | NEWS-01, NEWS-02 | unit | `pytest tests/test_data/test_news_fetcher.py -v` | ❌ W0 | ⬜ pending |
| 08-02-02 | 02 | 2 | NEWS-03 | unit | `pytest tests/test_llm/test_news_analyzer.py -v` | ❌ W0 | ⬜ pending |
| 08-02-03 | 02 | 2 | NEWS-04 | unit | `pytest tests/test_report/test_news_section.py -v` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_engines/test_fundamental.py` — stubs for ENGN-02 (fundamental engine scoring)
- [ ] `tests/test_engines/test_macro.py` — stubs for ENGN-12 (macro engine scoring)
- [ ] `tests/test_engines/test_sentiment.py` — stubs for ENGN-05 (sentiment engine scoring)
- [ ] `tests/test_engines/test_event.py` — stubs for ENGN-09 (event engine scoring)
- [ ] `tests/test_data/test_news_fetcher.py` — stubs for NEWS-01, NEWS-02 (news fetching)
- [ ] `tests/test_llm/test_news_analyzer.py` — stubs for NEWS-03 (LLM news scoring)
- [ ] `tests/test_report/test_news_section.py` — stubs for NEWS-04 (news digest in report)

*Existing test infrastructure (pytest, conftest.py, aiosqlite fixtures) covers framework needs.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| yfinance .info returns valid data for .JK tickers | ENGN-02 | External API, rate-limited | Run `python -c "import yfinance; print(yfinance.Ticker('BBCA.JK').info.get('trailingPE'))"` |
| FRED API returns macro data | ENGN-12 | Requires API key | Run macro fetcher with valid FRED_API_KEY |
| RSS feeds return parseable XML | NEWS-01 | External feeds may change format | Run feedparser against live Kontan/CNBC/Bisnis URLs |
| Reddit PRAW returns posts | ENGN-05 | Requires Reddit API credentials | Run sentiment fetcher with valid Reddit credentials |
| Finnhub returns news articles | NEWS-02 | Requires API key | Run news fetcher with valid FINNHUB_API_KEY |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 45s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
