---
phase: 03-technical-engine-pipeline-shell
plan: 02
subsystem: engines
tags: [technical-analysis, rsi, macd, bollinger-bands, ema, obv, pandas-ta-classic, zone-mapping]

# Dependency graph
requires:
  - phase: 03-technical-engine-pipeline-shell
    provides: "BaseEngine ABC, Signal dataclass, test fixtures (sample_price_df_200/50/10/empty), indicator weight config"
provides:
  - "TechnicalEngine with full indicator computation (RSI, MACD, BB, EMA, OBV, volume ratio)"
  - "Zone mapping functions for score composition (_rsi_to_score, _macd_to_score, etc.)"
  - "compute_technical_indicators function for reusable indicator extraction"
  - "30 unit tests covering normal, degraded, and failure scenarios"
affects: [03-04-pipeline-shell, future-engine-implementations]

# Tech tracking
tech-stack:
  added: []
  patterns: [zone-mapping-score-composition, weighted-average-composite, graceful-degradation-with-skipped-tracking]

key-files:
  created:
    - src/engines/technical.py
    - tests/test_engines/test_technical.py
  modified: []

key-decisions:
  - "Zone thresholds: RSI <20/30/45/55/70/80 mapped to +0.9/+0.6/+0.2/0.0/-0.2/-0.6/-0.9"
  - "EMA weighting: shorter EMAs weighted more (9=0.30, 21=0.25, 50=0.20, 100=0.15, 200=0.10)"
  - "Confidence formula: (agreeing_indicators / 5) * (1.0 - skipped_penalty) where penalty is 0.1 per skipped indicator"
  - "Overall trend sub-score combines RSI 30%, EMA 40%, MACD 30%"
  - "pandas_ta_classic imported at module level to register .ta accessor on DataFrames"

patterns-established:
  - "Zone mapping: each indicator family has a private _X_to_score function returning [-0.9, +0.9]"
  - "Indicator computation separated into standalone compute_technical_indicators for testability"
  - "Graceful degradation: track skipped indicators in list, reduce confidence proportionally"
  - "Never-raise pattern: try/except wrapping analyze() returns score=0/confidence=0 with error in reasoning"

requirements-completed: [ENGN-01]

# Metrics
duration: 4min
completed: 2026-03-24
---

# Phase 03 Plan 02: TechnicalEngine Summary

**TechnicalEngine computing RSI(14/7), MACD(12/26/9), Bollinger(20,2sigma/1sigma), EMA(9/21/50/100/200), OBV, and volume ratio with zone-based scoring and weighted average composite**

## Performance

- **Duration:** 4 min
- **Started:** 2026-03-24T07:58:34Z
- **Completed:** 2026-03-24T08:02:49Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- TechnicalEngine implements full BaseEngine contract with all 5 indicator families
- Zone mapping converts raw indicator values to sub-scores via threshold-based functions
- Weighted average composite score using configurable weights from settings
- Confidence reflects signal agreement (how many indicators agree with composite direction) penalized by data quality (skipped indicators)
- Graceful degradation: with 10 rows, skips 8 indicators and returns confidence=0.1; with empty DataFrame returns score=0/confidence=0
- 30 comprehensive unit tests covering normal, degraded, edge case, and failure scenarios

## Task Commits

Each task was committed atomically:

1. **Task 1 (RED): Failing tests for TechnicalEngine** - `30cd09e` (test)
2. **Task 1 (GREEN): Implement TechnicalEngine** - `13cadd5` (feat)

## Files Created/Modified
- `src/engines/technical.py` - TechnicalEngine with compute_technical_indicators, 5 zone-mapping functions, weighted composite scoring (515 lines)
- `tests/test_engines/test_technical.py` - 30 unit tests across 7 test classes (256 lines)

## Decisions Made
- Zone thresholds chosen for RSI based on standard oversold/overbought levels (30/70) with finer gradations at 20/45/55/80
- EMA score weights shorter periods more heavily (9-day=30%, 200-day=10%) since shorter EMAs are more responsive
- Confidence formula uses 5 indicator groups (RSI, MACD, Bollinger, EMA, volume) for agreement counting
- Overall trend is a derived sub-score (not a direct indicator) combining RSI, EMA alignment, and MACD direction
- pandas_ta_classic must be imported at module level to register the .ta DataFrame accessor

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed pandas-ta-classic accessor registration**
- **Found during:** Task 1 (GREEN phase)
- **Issue:** DataFrame .ta accessor not available because pandas_ta_classic was not imported
- **Fix:** Added `import pandas_ta_classic as _ta` at module level to register accessor
- **Files modified:** src/engines/technical.py
- **Committed in:** 13cadd5

**2. [Rule 1 - Bug] Fixed volume scoring for bearish + low volume case**
- **Found during:** Task 1 (GREEN phase)
- **Issue:** _volume_to_score returned near-zero for bearish OBV with low volume ratio due to sign cancellation
- **Fix:** Simplified volume magnitude to always amplify OBV direction regardless of volume level
- **Files modified:** src/engines/technical.py
- **Committed in:** 13cadd5

**3. [Rule 1 - Bug] Fixed EMA minimum data threshold**
- **Found during:** Task 1 (GREEN phase)
- **Issue:** EMA(200) check required n >= 201 rows (period + 1) but EMA works with exactly period rows
- **Fix:** Changed threshold from `n >= period + 1` to `n >= period`
- **Files modified:** src/engines/technical.py
- **Committed in:** 13cadd5

---

**Total deviations:** 3 auto-fixed (3 bugs)
**Impact on plan:** All fixes necessary for correct indicator computation. No scope creep.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- TechnicalEngine ready for pipeline integration in 03-04
- Zone mapping pattern established for any future engines needing score composition
- compute_technical_indicators function can be reused or referenced by other analysis code

---
*Phase: 03-technical-engine-pipeline-shell*
*Completed: 2026-03-24*
