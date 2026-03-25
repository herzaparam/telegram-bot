---
phase: 9
slug: idx-documents-valuation-engine
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-25
---

# Phase 9 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | pyproject.toml |
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
| 09-01-01 | 01 | 1 | IDXD-01 | unit | `pytest tests/test_data/test_idx_doc_fetcher.py -x` | W0 | pending |
| 09-02-01 | 02 | 1 | IDXD-02 | unit | `pytest tests/test_llm/test_doc_parser.py -x` | W0 | pending |
| 09-03-01 | 03 | 1 | VALN-01 | unit | `pytest tests/test_engines/test_valuation.py -k dcf` | W0 | pending |
| 09-03-02 | 03 | 1 | VALN-02 | unit | `pytest tests/test_engines/test_valuation.py -k peer` | W0 | pending |
| 09-03-03 | 03 | 1 | VALN-03 | unit | `pytest tests/test_engines/test_valuation.py -k "crypto or nvt or tvl"` | W0 | pending |
| 09-03-04 | 03 | 1 | VALN-04 | unit | `pytest tests/test_engines/test_valuation.py -k margin_of_safety` | W0 | pending |
| 09-04-01 | 04 | 2 | VALN-05 | unit | `pytest tests/test_data/test_pipeline_wiring.py -x` | W0 | pending |
| 09-04-02 | 04 | 2 | VALN-05 | unit | `pytest tests/test_engines/test_valuation.py -k qoq` | W0 | pending |
| 09-05-01 | 05 | 2 | TBOT-09 | unit | `pytest tests/test_bot/test_valuation_handler.py -x` | W0 | pending |
| 09-05-02 | 05 | 2 | TBOT-13 | unit | `pytest tests/test_bot/test_fundamentals_handler.py -x` | W0 | pending |
| 09-05-03 | 05 | 2 | REPT-03 | unit | `pytest tests/test_report/test_formatter_valuation.py -x` | W0 | pending |

*Status: pending / green / red / flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_data/test_idx_doc_fetcher.py` -- stubs for IDXD-01 (download + storage)
- [ ] `tests/test_llm/test_doc_parser.py` -- stubs for IDXD-02 (LLM extraction)
- [ ] `tests/test_engines/test_valuation.py` -- stubs for VALN-01..05 (DCF, peer, scenario, MoS, alerts, crypto proxy)
- [ ] `tests/test_data/test_pipeline_wiring.py` -- stubs for VALN-05 (pipeline wiring, fetch+parse+validate)
- [ ] `tests/test_bot/test_valuation_handler.py` -- stubs for TBOT-09 (/valuation handler)
- [ ] `tests/test_bot/test_fundamentals_handler.py` -- stubs for TBOT-13 (/fundamentals handler)
- [ ] `tests/test_report/test_formatter_valuation.py` -- stubs for REPT-03 (valuation summary formatting)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| IDX API download succeeds | IDXD-01 | External API, may 403 | Run fetcher against live idx.co.id, verify PDF downloaded |
| Bahasa Indonesia PDF parsing accuracy | IDXD-02 | LLM output quality | Compare extracted values against manually read PDF |
| /valuation Telegram response format | TBOT-09 | Bot interaction | Send /valuation BBCA in Telegram, verify response format |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 45s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
