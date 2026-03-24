---
phase: 03-technical-engine-pipeline-shell
plan: 03
subsystem: engines
tags: [quantitative-engine, hurst, arima, pmdarima, momentum, mean-reversion, regime-detection]

# Dependency graph
requires:
  - phase: 03-technical-engine-pipeline-shell
    plan: 01
    provides: "BaseEngine ABC, Signal dataclass, test fixtures (sample_price_df_200/50/10/empty), indicator weight config"
provides:
  - "QuantitativeEngine with momentum (ROC 5/10/20), mean reversion (OU half-life + Z-score), and ARIMA forecast"
  - "Hurst exponent R/S analysis for regime detection"
  - "Regime-based component weighting (trending vs mean-reverting)"
  - "Graceful degradation with <200 trading days"
affects: [03-04-pipeline-shell]

# Tech tracking
tech-stack:
  added: []
  patterns: [Hurst R/S analysis, OU half-life via OLS, zone-to-score mapping, regime-based weighting]

key-files:
  created:
    - src/engines/quantitative.py
    - tests/test_engines/test_quantitative.py
  modified: []

key-decisions:
  - "Lazy import of pmdarima inside _arima_forecast to avoid loading heavy ML stack until needed"
  - "ARIMA weight redistributed to momentum/reversion when ARIMA is skipped"
  - "Regime thresholds at H>0.55 trending, H<0.45 mean-reverting (0.05 buffer around 0.5)"

patterns-established:
  - "Zone-to-score mapping: helper functions map indicator values to [-1,1] sub-scores"
  - "Regime-based weighting: Hurst exponent drives component weight allocation"
  - "Graceful degradation: check len(df) >= threshold, skip components, lower confidence via penalty"

requirements-completed: [ENGN-03]

# Metrics
duration: 3min
completed: 2026-03-24
---

# Phase 03 Plan 03: Quantitative Engine Summary

**QuantitativeEngine with momentum (ROC + Hurst regime), mean reversion (OU half-life + Z-score), and ARIMA forecast via pmdarima, with Hurst-driven regime detection adjusting component weights**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-24T07:58:39Z
- **Completed:** 2026-03-24T08:01:38Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- QuantitativeEngine computes 3 component scores: momentum (ROC 5/10/20 day), mean reversion (Z-score 20/50 day), and ARIMA 1-day forecast
- Hurst exponent via R/S analysis drives regime detection: trending (H>0.55) weights momentum 50%, mean-reverting (H<0.45) weights reversion 50%
- Graceful degradation: <200 days skips ARIMA/Hurst/OU, <25 days returns score=0/confidence=0
- 22 tests covering full data, degradation, regime weighting, helper functions, and exception handling

## Task Commits

Each task was committed atomically:

1. **Task 1: QuantitativeEngine with momentum, mean reversion, ARIMA, and regime detection** - `7038732` (feat)
2. **Task 2: Comprehensive unit tests for QuantitativeEngine** - `f46ba36` (test)

## Files Created/Modified
- `src/engines/quantitative.py` - QuantitativeEngine with _hurst_exponent, _ou_half_life, _arima_forecast, _roc_to_score, _zscore_to_score, _arima_to_score helpers
- `tests/test_engines/test_quantitative.py` - 22 unit tests across 7 test classes

## Decisions Made
- Lazy import of pmdarima inside _arima_forecast() to avoid loading heavy ML dependencies at module import time
- When ARIMA is skipped, its weight is redistributed proportionally to momentum and reversion components
- Regime detection uses 0.05 buffer around 0.5 (H>0.55 = trending, H<0.45 = mean-reverting) to avoid regime flipping on noise

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- QuantitativeEngine ready for pipeline integration in 03-04
- Both TechnicalEngine (03-02) and QuantitativeEngine (03-03) implement BaseEngine contract
- All 22 tests pass with 200-row, 50-row, 10-row, and empty DataFrames

---
*Phase: 03-technical-engine-pipeline-shell*
*Completed: 2026-03-24*
