---
phase: 03-technical-engine-pipeline-shell
plan: 04
subsystem: pipeline
tags: [analyze-stage, stage-func, pipeline-wiring, engine-integration, signal-storage]

# Dependency graph
requires:
  - phase: 03-technical-engine-pipeline-shell
    plan: 01
    provides: "BaseEngine ABC, Signal dataclass, SignalRepository with UPSERT"
  - phase: 03-technical-engine-pipeline-shell
    plan: 02
    provides: "TechnicalEngine with RSI/MACD/BB/EMA/OBV scoring"
  - phase: 03-technical-engine-pipeline-shell
    plan: 03
    provides: "QuantitativeEngine with momentum/mean-reversion/ARIMA"
provides:
  - "analyze_stage StageFunc wiring engines to pipeline"
  - "Pipeline main.py with stage_funcs dict (fetch + analyze)"
  - "End-to-end signal generation path: DB prices -> engines -> stored signals"
affects: [04-llm-decision, future-engine-additions]

# Tech tracking
tech-stack:
  added: []
  patterns: [stage-func-pattern, per-engine-error-isolation, gc-memory-release]

key-files:
  created:
    - src/data/analyze.py
    - tests/test_data/test_analyze.py
  modified:
    - src/pipeline/main.py

key-decisions:
  - "analyze_stage follows same StageFunc(session, asset) pattern as ingest_stage for consistency"
  - "Engine failures caught per-engine with _failed_signal fallback -- one crash does not block others"
  - "DataFrame released with del + gc.collect() after each asset to stay within 1GB RAM budget"

patterns-established:
  - "Stage wiring: stage_funcs dict in pipeline main.py maps stage names to StageFunc callables"
  - "Engine error isolation: try/except per engine, append _failed_signal on crash"
  - "Memory management: del df + gc.collect() after each asset's analysis completes"

requirements-completed: [ENGN-01, ENGN-03]

# Metrics
duration: 3min
completed: 2026-03-24
---

# Phase 03 Plan 04: Pipeline Shell Summary

**analyze_stage wiring TechnicalEngine and QuantitativeEngine into pipeline via StageFunc, with per-engine error isolation, signal batch storage, and gc-based memory release**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-24T08:05:15Z
- **Completed:** 2026-03-24T08:08:31Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- analyze_stage loads price data from DB, runs both engines sequentially, stores all signals via SignalRepository
- Pipeline main.py wires stage_funcs dict with "fetch" -> ingest_stage and "analyze" -> analyze_stage
- Engine failures are caught per-engine -- one engine crashing does not prevent others from running
- DataFrame memory released with del + gc.collect() after each asset
- 9 integration tests covering engine selection, failure isolation, empty data handling, gc verification
- Full test suite (210 tests) passes with zero regressions

## Task Commits

Each task was committed atomically:

1. **Task 1: Implement analyze_stage and wire into pipeline main** - `36e7eb7` (feat)
2. **Task 2: Integration tests for analyze_stage** - `0f9e510` (test)

## Files Created/Modified
- `src/data/analyze.py` - analyze_stage StageFunc with _load_price_dataframe, _get_engines_for_asset, _failed_signal helpers
- `src/pipeline/main.py` - Added stage_funcs dict wiring fetch and analyze stages to run_pipeline
- `tests/test_data/test_analyze.py` - 9 tests across TestGetEnginesForAsset, TestFailedSignal, TestAnalyzeStage

## Decisions Made
- analyze_stage follows same StageFunc(session, asset) pattern as ingest_stage for consistency
- Engine failures caught per-engine with _failed_signal fallback -- one crash does not block others
- DataFrame released with del + gc.collect() after each asset to stay within 1GB RAM budget

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- End-to-end signal generation path complete: price data in DB -> engines analyze -> signals stored in DB
- Pipeline can now run fetch + analyze stages in sequence via PipelineRunner
- Ready for LLM decision stage (Phase 04) to consume stored signals
- Adding new engines requires only: implement BaseEngine, add to _get_engines_for_asset list

---
*Phase: 03-technical-engine-pipeline-shell*
*Completed: 2026-03-24*
