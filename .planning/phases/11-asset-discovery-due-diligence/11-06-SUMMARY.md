---
phase: 11-asset-discovery-due-diligence
plan: 06
subsystem: llm, bot
tags: [dd-flags, type-guard, compare, stock-fundamentals]

requires:
  - phase: 11-asset-discovery-due-diligence
    provides: DD flags loading in decide_stage, /compare handler with format_compare_table
provides:
  - Type-safe DD flags loading preventing coroutine leak to LLM prompt
  - Clean 5-metric compare table without misleading Net Margin row
affects: []

tech-stack:
  added: []
  patterns:
    - "Type guard after async DB query to prevent mock/coroutine leakage"

key-files:
  created: []
  modified:
    - src/data/decide.py
    - src/bot/handlers/compare.py
    - src/report/formatter.py
    - tests/test_report/test_formatter_discovery.py

key-decisions:
  - "isinstance list guard after try/except (not inside) to catch all non-list types including coroutines"
  - "Remove net_margin from compare only; DD report sector benchmarking net_margin preserved (different data source)"

patterns-established:
  - "Type guard pattern: validate DB query results with isinstance before passing to downstream functions"

requirements-completed: [LLM-06, TBOT-10, DISC-01, DISC-02, DISC-03, DISC-04, DUED-01, DUED-02, DUED-03, DUED-04, TBOT-06, TBOT-11, REPT-07]

duration: 3min
completed: 2026-03-26
---

# Phase 11 Plan 06: Gap Closure Summary

**Type-safe DD flags loading with isinstance guard and 5-metric compare table without misleading Net Margin**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-26T06:40:18Z
- **Completed:** 2026-03-26T06:43:30Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- Fixed DD flags regression: isinstance guard prevents coroutine/non-list values from leaking to build_decision_prompt
- All 26 tests in test_decide.py pass (6 regressions restored)
- Removed misleading Net Margin column from /compare table (always showed dashes since StockFundamental lacks net_margin)
- Full test suite passes: 834 tests, 0 failures

## Task Commits

Each task was committed atomically:

1. **Task 1: Fix DD flags regression in decide.py** - `18079b0` (fix)
2. **Task 2: Remove net_margin from /compare table and formatter** - `556f597` (fix)

## Files Created/Modified
- `src/data/decide.py` - Added isinstance type guard after DD flags try/except block
- `src/bot/handlers/compare.py` - Removed net_margin keys from both data.append() dicts
- `src/report/formatter.py` - Removed Net Mgn row from metrics list, updated docstring
- `tests/test_report/test_formatter_discovery.py` - Removed net_margin from compare test fixtures

## Decisions Made
- Placed isinstance guard AFTER the try/except block (not inside) to catch all edge cases including the coroutine leak
- Preserved net_margin references in DD report sector benchmarking (format_dd_report) since that data comes from a different source than StockFundamental

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Phase 11 gap closure complete: all verification regressions fixed
- DD flags safely reach LLM prompt for stock assets with real DD data
- /compare table shows 5 clean metrics (P/E, P/B, ROE, D/E, Rev CAGR)
- Full test suite (834 tests) green with 0 failures

## Known Stubs

None - no stubs introduced.

## Self-Check: PASSED

---
*Phase: 11-asset-discovery-due-diligence*
*Completed: 2026-03-26*
