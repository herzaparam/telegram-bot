---
phase: 10-remaining-specialized-engines
plan: 05
subsystem: engines
tags: [pipeline-wiring, analyze-stage, ingest-stage, scorecard, integration-test, 15-engines]

# Dependency graph
requires:
  - phase: 10-remaining-specialized-engines/01
    provides: "OnChainData, GitHubActivity ORM models, xgboost/pywt dependencies"
  - phase: 10-remaining-specialized-engines/02
    provides: "OptionsEngine, GameTheoryEngine, BehavioralEngine, NetworkEngine, EmergingMethodsEngine"
  - phase: 10-remaining-specialized-engines/03
    provides: "OnChainEngine, AlternativeDataEngine, onchain_fetcher, github_fetcher"
  - phase: 10-remaining-specialized-engines/04
    provides: "MLAIEngine with ONNX inference"
provides:
  - "All 15 engines wired into analyze_stage's _get_engines_for_asset()"
  - "On-chain and GitHub fetchers wired into ingest_stage for crypto assets"
  - "Pre-computed correlation data for NetworkEngine"
  - "Integration tests verifying 15-engine pipeline coverage"
  - "/scorecard displays all 15 engine categories with accuracy breakdown"
affects: [pipeline-execution, daily-report, scorecard-display]

# Tech tracking
tech-stack:
  added: []
  patterns: [cross-asset-correlation-pre-computation, per-engine-accuracy-display, stub-engine-na-display]

key-files:
  created: []
  modified:
    - src/data/analyze.py
    - src/data/ingest.py
    - tests/test_data/test_analyze.py
    - src/bot/handlers/scorecard.py
    - src/report/formatter.py
    - tests/test_bot/test_handlers.py
    - tests/test_data/test_analyze_extended.py

key-decisions:
  - "Stock gets 13 engines (onchain and alternative are crypto-only), crypto gets 14 (options is stock-only)"
  - "_compute_correlation_data loads all watchlisted assets' 30-day prices for cross-correlation"
  - "Stub engines (options, game_theory) show 'N/A -- data source unavailable' in scorecard per D-24"

patterns-established:
  - "Cross-asset correlation pre-computation: load once per analyze_stage call, pass via constructor injection"
  - "Per-engine accuracy display: query AccuracyStats with engine_name IS NOT NULL for Engine Breakdown section"

requirements-completed: [ENGN-04, ENGN-06, ENGN-07, ENGN-08, ENGN-10, ENGN-11, ENGN-13, ENGN-14]

# Metrics
duration: 11min
completed: 2026-03-26
---

# Phase 10 Plan 05: Pipeline Integration and Scorecard Summary

**All 15 engines wired into analyze_stage with on-chain/GitHub fetchers in ingest, cross-asset correlation pre-computation, and /scorecard Engine Breakdown showing per-engine accuracy**

## Performance

- **Duration:** 11 min
- **Started:** 2026-03-26T02:43:24Z
- **Completed:** 2026-03-26T02:54:39Z
- **Tasks:** 3
- **Files modified:** 7

## Accomplishments
- Wired all 8 new engines (MLAIEngine, OnChainEngine, OptionsEngine, BehavioralEngine, AlternativeDataEngine, NetworkEngine, GameTheoryEngine, EmergingMethodsEngine) into _get_engines_for_asset
- Added _load_onchain_data, _load_github_data, and _compute_correlation_data helper functions to analyze_stage
- Added on-chain and GitHub data fetchers to ingest_stage for crypto assets (lazy imports, graceful failure)
- Integration tests verify: 13 stock engines, 14 crypto engines, valid signal ranges, all 15 categories covered
- /scorecard Engine Breakdown section shows per-engine accuracy with N/A for stub engines per D-24

## Task Commits

Each task was committed atomically:

1. **Task 1: Wire 8 new engines into analyze_stage and add crypto data fetchers** - `9146a8a` (feat)
2. **Task 2: Integration tests for 15-engine pipeline** - `3c968ab` (test)
3. **Task 3: Update /scorecard to display all 15 engine categories** - `a03aee9` (feat)
4. **Task 3 fix: Update existing test mocks for Phase 10 changes** - `62fc2af` (fix)

## Files Created/Modified
- `src/data/analyze.py` - Added 8 engine imports, new data params, helper functions, Phase 10 data loading in analyze_stage
- `src/data/ingest.py` - Added on-chain and GitHub fetcher calls for crypto assets
- `tests/test_data/test_analyze.py` - Added 11 integration tests (stock/crypto engine counts, valid signals, category completeness)
- `src/bot/handlers/scorecard.py` - Added ALL_ENGINE_CATEGORIES (15), STUB_ENGINE_CATEGORIES, AccuracyStats query
- `src/report/formatter.py` - Added per_engine_accuracy param and Engine Breakdown section
- `tests/test_bot/test_handlers.py` - Fixed mock setups for new AccuracyStats query chain
- `tests/test_data/test_analyze_extended.py` - Updated engine count assertion and added Phase 10 mocks

## Decisions Made
- Stock gets 13 engines, crypto gets 14 -- options is stock-only, onchain and alternative are crypto-only
- _compute_correlation_data queries all watchlisted assets to compute cross-asset correlation matrix
- Stub engines (options, game_theory) display "N/A -- data source unavailable" in Engine Breakdown
- Module-level `from sqlalchemy import select` in scorecard.py replaces local imports to avoid shadowing

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed existing test mocks for new scorecard AccuracyStats query**
- **Found during:** Task 3 (scorecard update)
- **Issue:** Existing scorecard handler tests used bare AsyncMock() for session, which failed when new code called session.execute().scalars().all()
- **Fix:** Added proper mock_execute_result with scalars().all() returning [] to all affected tests
- **Files modified:** tests/test_bot/test_handlers.py
- **Verification:** All 769 tests pass
- **Committed in:** 62fc2af

**2. [Rule 1 - Bug] Fixed local select import shadowing module-level import**
- **Found during:** Task 3 (scorecard update)
- **Issue:** Local `from sqlalchemy import select` inside conditional block caused UnboundLocalError when module-level select was used before the conditional
- **Fix:** Removed redundant local imports, changed `sel(DD)` to `select(DD)`
- **Files modified:** src/bot/handlers/scorecard.py
- **Committed in:** a03aee9

**3. [Rule 1 - Bug] Updated engine count assertion in extended analyze test**
- **Found during:** Task 2 (integration tests)
- **Issue:** test_analyze_extended.py asserted 7 engines but stock now has 13
- **Fix:** Updated assertion to 13 and added Phase 10 data loading mocks
- **Files modified:** tests/test_data/test_analyze_extended.py
- **Committed in:** 62fc2af

---

**Total deviations:** 3 auto-fixed (3 bugs in existing tests)
**Impact on plan:** All fixes necessary to maintain passing test suite. No scope creep.

## Issues Encountered
None beyond the test mock fixes documented above.

## User Setup Required
None - no external service configuration required.

## Known Stubs
None - all data paths are wired. Engines that lack real data sources (options, game_theory) return score=0/confidence=0 by design and are marked as stubs in the scorecard.

## Next Phase Readiness
- Full 15-engine pipeline is operational for both stock and crypto assets
- All engines produce valid signals and are tracked in /scorecard
- Phase 10 (remaining-specialized-engines) is complete

## Self-Check: PASSED

All files verified:
- src/data/analyze.py: contains all 8 new engine imports and _compute_correlation_data
- src/data/ingest.py: contains fetch_onchain_data and fetch_github_activity calls
- tests/test_data/test_analyze.py: contains all 4 new test classes
- src/bot/handlers/scorecard.py: contains ALL_ENGINE_CATEGORIES with 15 entries
- src/report/formatter.py: contains per_engine_accuracy parameter and Engine Breakdown

All commits verified in git log:
- 9146a8a (Task 1)
- 3c968ab (Task 2)
- a03aee9 (Task 3)
- 62fc2af (Task 3 fix)

769 tests pass.

---
*Phase: 10-remaining-specialized-engines*
*Completed: 2026-03-26*
