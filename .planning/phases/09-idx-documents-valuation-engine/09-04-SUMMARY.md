---
phase: 09-idx-documents-valuation-engine
plan: 04
subsystem: pipeline
tags: [valuation, idx-docs, pipeline-wiring, telegram-alerts, qoq-detection, cross-validation]

# Dependency graph
requires:
  - phase: 09-01
    provides: FinancialDoc and FinancialData ORM models, migration 008
  - phase: 09-02
    provides: LLM doc parser (parse_financial_doc)
  - phase: 09-03
    provides: ValuationEngine class with DCF, peer comparison, NVT/TVL proxies
provides:
  - ValuationEngine wired into analyze_stage engine list with tvl_data injection
  - IDX doc fetch+parse integrated into ingest stage with Telegram alert on failure
  - Cross-validation of PDF-extracted vs yfinance financial data
  - QoQ ratio change detection with configurable thresholds (max 2 alerts)
  - Financial data loading functions (_load_financial_data, _load_peer_data)
affects: [daily-report, bot-commands, pipeline]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "QoQ alert detection with frozen dataclass and configurable thresholds"
    - "Cross-validation comparing PDF-extracted data vs yfinance market data"
    - "Telegram alert pattern for IDX scraper failures via httpx"

key-files:
  created:
    - tests/test_data/test_pipeline_wiring.py
  modified:
    - src/data/ingest.py
    - src/data/analyze.py
    - src/engines/valuation.py
    - tests/test_engines/test_valuation.py

key-decisions:
  - "Period string normalization uses space-to-dash conversion (Q3 2025 -> Q3-2025)"
  - "Cross-validation compares revenue and net_profit with 10% threshold"
  - "QoQ detection returns max 2 alerts sorted by change magnitude descending"
  - "Margin QoQ thresholds use absolute pp difference; revenue/debt use percentage change"

patterns-established:
  - "QoQ alert pattern: frozen dataclass with is_percentage_point flag for margin vs absolute metrics"
  - "_fetch_and_parse_docs pattern: fetch -> alert on failure -> parse pending -> create FinancialData rows"

requirements-completed: [VALN-05]

# Metrics
duration: 6min
completed: 2026-03-25
---

# Phase 09 Plan 04: Pipeline Wiring Summary

**IDX doc fetch+parse wired into ingest stage with Telegram alerts, ValuationEngine wired into analyze_stage with tvl_data injection, cross-validation, and QoQ ratio change detection**

## Performance

- **Duration:** 6 min
- **Started:** 2026-03-25T12:05:54Z
- **Completed:** 2026-03-25T12:12:00Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments
- ValuationEngine wired into _get_engines_for_asset with financial_data, peer_data, nvt_data, tvl_data params
- IDX doc fetch+parse integrated into ingest_stage for stock assets with Telegram alert on failure (D-05)
- Cross-validation flags >10% discrepancy between PDF-extracted and yfinance financial data
- QoQ ratio change detection with configurable thresholds returns max 2 most significant alerts
- All 36 tests pass (12 pipeline wiring + 5 QoQ + 19 existing valuation)

## Task Commits

Each task was committed atomically:

1. **Task 1 (RED): Pipeline wiring tests** - `7c9dc31` (test)
2. **Task 1 (GREEN): Wire IDX doc fetch+parse, ValuationEngine, cross-validation** - `c39477b` (feat)
3. **Task 2 (RED): QoQ ratio change detection tests** - `2076bb8` (test)
4. **Task 2 (GREEN): QoQ detection implementation** - `341b542` (feat)

## Files Created/Modified
- `src/data/ingest.py` - Added _fetch_and_parse_docs with Telegram alert, fetch_idx_docs + parse_financial_doc imports
- `src/data/analyze.py` - Added _load_financial_data, _load_peer_data, _cross_validate; wired ValuationEngine into engine list
- `src/engines/valuation.py` - Added QOQ_THRESHOLDS, QoQAlert dataclass, detect_qoq_changes function
- `tests/test_data/test_pipeline_wiring.py` - 12 tests covering pipeline wiring behaviors
- `tests/test_engines/test_valuation.py` - 5 QoQ detection tests added

## Decisions Made
- Period string normalization: "Q3 2025" -> "Q3-2025" via space-to-dash replacement
- Cross-validation compares revenue and net_profit fields with 10% threshold
- QoQ thresholds: 3pp for margins, 10% for revenue/profit, 15% for debt/cashflow/capex
- Max 2 QoQ alerts per asset sorted by change magnitude (most significant first)
- Margin QoQ uses absolute pp difference; non-margin metrics use percentage change

## Deviations from Plan

None - plan executed exactly as written.

## Known Stubs

None - all functions fully implemented with data sources wired.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- All Phase 9 Plans 01-04 (Wave 1 + Wave 2 first plan) complete
- Ready for Plan 05 (integration testing / E2E if applicable)
- ValuationEngine fully wired, financial docs pipeline operational

---
*Phase: 09-idx-documents-valuation-engine*
*Completed: 2026-03-25*
