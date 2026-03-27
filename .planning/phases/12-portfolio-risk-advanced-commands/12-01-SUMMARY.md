---
phase: 12-portfolio-risk-advanced-commands
plan: 01
subsystem: risk-analytics
tags: [numpy, pandas, var, sharpe, sortino, correlation, stress-test, portfolio-risk]

requires:
  - phase: 11-discovery-due-diligence
    provides: IDX_SECTOR_MAP for sector concentration, DueDiligenceReport model pattern
provides:
  - src/risk/ module with 5 sub-modules for portfolio risk computation
  - PortfolioRiskSnapshot and BacktestResult ORM models
  - Alembic migration 014 for portfolio_risk_snapshots and backtest_results tables
affects: [12-02 (bot handler consumes risk functions), 12-03 (daily report pipeline hook)]

tech-stack:
  added: []
  patterns: [frozen-dataclass-result-pattern, pure-computation-module-no-db-imports]

key-files:
  created:
    - src/risk/__init__.py
    - src/risk/correlation.py
    - src/risk/var.py
    - src/risk/concentration.py
    - src/risk/stress.py
    - src/risk/metrics.py
    - src/db/migrations/versions/014_portfolio_risk.py
    - tests/test_risk/conftest.py
    - tests/test_risk/test_correlation.py
    - tests/test_risk/test_var.py
    - tests/test_risk/test_concentration.py
    - tests/test_risk/test_stress.py
    - tests/test_risk/test_metrics.py
  modified:
    - src/db/models.py

key-decisions:
  - "Frozen dataclasses for all result types (CorrelationResult, VaRResult, etc.) matching Signal pattern"
  - "Pure computation: src/risk/ has zero imports from src.db, src.pipeline, or src.llm"
  - "Equal-weight assumption for concentration and stress testing (no position sizing yet)"

patterns-established:
  - "Pure risk computation module: src/risk/ pattern for bot+pipeline consumption without cross-process imports"
  - "Result dataclass per sub-module: frozen dataclass with typed fields, round() on numeric outputs"

requirements-completed: [RISK-01, RISK-02, RISK-03, RISK-04, RISK-05]

duration: 6min
completed: 2026-03-27
---

# Phase 12 Plan 01: Portfolio Risk Computation Module Summary

**Five pure-computation risk analytics (correlation, VaR, concentration, stress test, Sharpe/Sortino) with frozen dataclass results, 2 new DB models, Alembic migration 014, and 37-test suite**

## Performance

- **Duration:** 6 min
- **Started:** 2026-03-27T10:42:11Z
- **Completed:** 2026-03-27T10:48:26Z
- **Tasks:** 2
- **Files modified:** 20

## Accomplishments
- NxN correlation matrix with high-pair detection (>0.8 threshold) and emoji heatmap HTML formatter
- Historical simulation VaR at 95%/99% daily+weekly, max drawdown with start/end dates, minimum 60-point guard
- Concentration analysis with sector grouping via IDX_SECTOR_MAP, IDR/USD currency split, equal-weight assumption
- Stress testing against 4 preset scenarios (COVID-19, crypto winter, taper tantrum, GFC) with weighted portfolio impact
- Sharpe and Sortino ratio computation with zero-volatility edge case handling
- PortfolioRiskSnapshot and BacktestResult ORM models with Alembic migration 014

## Task Commits

Each task was committed atomically:

1. **Task 1: DB models + Alembic migration 014 + test scaffolding** - `7d58def` (feat)
2. **Task 2: Portfolio risk computation modules (src/risk/)** - `b12c435` (feat)

## Files Created/Modified
- `src/risk/__init__.py` - Module exports for all 5 sub-modules
- `src/risk/correlation.py` - NxN correlation matrix + emoji heatmap formatter
- `src/risk/var.py` - Historical simulation VaR + max drawdown
- `src/risk/concentration.py` - Sector/currency/single-asset concentration
- `src/risk/stress.py` - 4 preset scenario stress tests
- `src/risk/metrics.py` - Sharpe and Sortino ratio computation
- `src/db/models.py` - Added PortfolioRiskSnapshot and BacktestResult models
- `src/db/migrations/versions/014_portfolio_risk.py` - Migration creating 2 tables
- `tests/test_risk/conftest.py` - Fixtures: sample_price_series, sample_assets, sample_price_data
- `tests/test_risk/test_correlation.py` - 8 tests for correlation module
- `tests/test_risk/test_var.py` - 7 tests for VaR module
- `tests/test_risk/test_concentration.py` - 7 tests for concentration module
- `tests/test_risk/test_stress.py` - 8 tests for stress module
- `tests/test_risk/test_metrics.py` - 7 tests for metrics module

## Decisions Made
- Frozen dataclasses for all result types matching existing Signal pattern in codebase
- Pure computation module: src/risk/ has zero imports from src.db, src.pipeline, or src.llm -- safe for both bot and pipeline processes
- Equal-weight assumption for concentration and stress testing (position sizing not yet available)
- VaR minimum 60 data points with ValueError guard per plan specification
- Weekly VaR uses 5-day rolling sum when sufficient data, falls back to sqrt(5) scaling

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed flaky test_annualized_return_positive test**
- **Found during:** Task 2
- **Issue:** sample_price_series with seed 42 produced negative mean returns despite 0.0005 drift specification, causing test assertion failure
- **Fix:** Changed test to use deterministic constant-return series [0.005]*252 instead of relying on random fixture
- **Files modified:** tests/test_risk/test_metrics.py
- **Verification:** All 37 tests pass
- **Committed in:** b12c435 (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** Trivial test fix. No scope creep.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- src/risk/ module ready for consumption by /portfolio bot handler (Plan 02) and daily report pipeline hook (Plan 03)
- All 5 computation functions are pure and process-safe
- 881 total tests passing including 37 new risk tests
