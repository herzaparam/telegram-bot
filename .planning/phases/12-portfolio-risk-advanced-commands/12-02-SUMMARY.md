---
phase: 12-portfolio-risk-advanced-commands
plan: 02
subsystem: bot-commands, report-pipeline
tags: [telegram-bot, portfolio-risk, sparkline, earnings-quality, dividends, var, correlation, stress-test]

requires:
  - phase: 12-portfolio-risk-advanced-commands
    provides: src/risk/ pure computation modules (correlation, VaR, concentration, stress, metrics)
  - phase: 11-asset-discovery-due-diligence
    provides: IDX_SECTOR_MAP, bot handler patterns, discovery section in report
provides:
  - /portfolio Telegram command with full risk analysis (correlation, VaR, concentration, stress, metrics)
  - Daily report portfolio risk snapshot section via format_portfolio_risk_snapshot
  - Pipeline hook _compute_daily_risk_snapshot with DB upsert
  - Enhanced /fundamentals with 5-year trends, earnings quality, dividend analysis
  - _sparkline text rendering helper
affects: [12-03 (backtest command may reuse sparkline helper)]

tech-stack:
  added: []
  patterns: [sparkline-text-rendering, enhanced-sections-stock-only-guard]

key-files:
  created:
    - src/bot/handlers/portfolio.py
    - tests/test_bot/test_portfolio_handler.py
    - tests/test_report/test_formatter_risk.py
  modified:
    - src/bot/main.py
    - src/report/formatter.py
    - src/data/report.py
    - src/pipeline/main.py
    - src/bot/handlers/fundamentals.py

key-decisions:
  - "Guard dividend_yield with isinstance check to handle None and MagicMock gracefully"
  - "Enhanced fundamentals sections only for stock assets; crypto gets informational note per D-17"
  - "Risk snapshot appended after discovery section in daily report with --- separator"

patterns-established:
  - "Text sparkline rendering: _SPARK_CHARS 10-level mapping for compact trend visualization"
  - "Enhanced handler sections: base dashboard + conditional enhanced sections with split_report"

requirements-completed: [TBOT-12, REPT-06, FUND-01, FUND-02, FUND-03]

duration: 7min
completed: 2026-03-27
---

# Phase 12 Plan 02: Bot Integration & Enhanced Fundamentals Summary

**/portfolio command with correlation heatmap, VaR, concentration, stress tests, and risk metrics; daily report risk snapshot; /fundamentals enhanced with sparkline 5-year trends, earnings quality, and dividend analysis**

## Performance

- **Duration:** 7 min
- **Started:** 2026-03-27T10:52:07Z
- **Completed:** 2026-03-27T10:59:00Z
- **Tasks:** 2
- **Files modified:** 9

## Accomplishments
- /portfolio command returns 5-section risk analysis: correlation heatmap, concentration breakdown, VaR (95%/99% daily/weekly + max drawdown), Sharpe/Sortino metrics, and 4-scenario stress tests
- Daily report pipeline computes risk snapshot post-pipeline, upserts PortfolioRiskSnapshot to DB, and passes to report formatter
- format_portfolio_risk_snapshot renders compact card with concentration, correlation alerts, VaR, and Sharpe/Sortino
- /fundamentals enhanced with format_five_year_trends (sparkline per ratio), format_earnings_quality (CF divergence detection), format_dividend_analysis (yield + FCF coverage)
- Text sparkline helper (_sparkline) with 10-level character mapping for compact trend visualization

## Task Commits

Each task was committed atomically:

1. **Task 1: /portfolio handler + daily report risk snapshot + pipeline hook** - `c5977cb` (feat)
2. **Task 2: Enhanced /fundamentals with 5-year trends, earnings quality, dividends** - `038a581` (feat)

## Files Created/Modified
- `src/bot/handlers/portfolio.py` - /portfolio command handler with full risk analysis
- `src/bot/main.py` - Registered portfolio_handler
- `src/report/formatter.py` - Added format_portfolio_risk_snapshot, _sparkline, format_earnings_quality, format_dividend_analysis, format_five_year_trends
- `src/data/report.py` - Added risk_snapshot parameter to send_daily_report
- `src/pipeline/main.py` - Added _compute_daily_risk_snapshot with DB upsert
- `src/bot/handlers/fundamentals.py` - Added enhanced sections (trends, earnings quality, dividends) for stock assets
- `tests/test_bot/test_portfolio_handler.py` - 4 tests for portfolio handler
- `tests/test_report/test_formatter_risk.py` - 4 tests for risk snapshot formatter

## Decisions Made
- Guard dividend_yield with isinstance(float/int) check to handle None and mock objects safely
- Enhanced fundamentals sections only shown for stock assets; crypto gets informational note per D-17
- Risk snapshot appended after discovery section in daily report with "---" separator
- Used split_report (not split_long_message which doesn't exist) for Telegram message splitting

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed dividend_yield MagicMock format error**
- **Found during:** Task 2
- **Issue:** Existing test uses MagicMock for StockFundamental; accessing .dividend_yield returns MagicMock which can't be formatted as float
- **Fix:** Added isinstance(fundamental.dividend_yield, (int, float)) guard before passing to format_dividend_analysis
- **Files modified:** src/bot/handlers/fundamentals.py
- **Verification:** All 889 tests pass
- **Committed in:** 038a581 (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** Trivial type guard. No scope creep.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- /portfolio and enhanced /fundamentals ready for user testing
- Pipeline risk snapshot computation active and storing to DB
- 889 total tests passing including 8 new tests
- Plan 03 (backtest) can proceed independently

---
*Phase: 12-portfolio-risk-advanced-commands*
*Completed: 2026-03-27*
