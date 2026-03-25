---
phase: 10-remaining-specialized-engines
plan: 01
subsystem: database
tags: [xgboost, onnxmltools, pywavelets, alembic, sqlalchemy, on-chain, github, ml-predictions]

# Dependency graph
requires:
  - phase: 09-idx-documents-valuation
    provides: "Existing ORM model patterns and migration chain (up to 008)"
provides:
  - "OnChainData, GitHubActivity, MLPrediction ORM models"
  - "Three Alembic migrations (009-011) with proper revision chain"
  - "xgboost, onnxmltools, PyWavelets production dependencies"
  - "github_token Settings field for GitHub API access"
affects: [10-02, 10-03, 10-04, 10-05]

# Tech tracking
tech-stack:
  added: [xgboost, onnxmltools, PyWavelets]
  patterns: [on-chain data storage, github activity tracking, ML prediction caching]

key-files:
  created:
    - src/db/migrations/versions/009_on_chain_data.py
    - src/db/migrations/versions/010_github_activity.py
    - src/db/migrations/versions/011_ml_predictions.py
  modified:
    - pyproject.toml
    - uv.lock
    - src/db/models.py
    - src/config.py

key-decisions:
  - "libomp required as system dependency for xgboost on macOS (brew install libomp)"
  - "mypy overrides added for xgboost, onnxmltools, pywt (no py.typed stubs)"

patterns-established:
  - "On-chain data keyed by (asset_id, date, metric) for multi-metric storage per asset per day"
  - "ML predictions keyed by (asset_id, date) with nullable columns for each model type"

requirements-completed: [ENGN-04, ENGN-06, ENGN-10]

# Metrics
duration: 4min
completed: 2026-03-25
---

# Phase 10 Plan 01: Foundation Dependencies and DB Models Summary

**xgboost/onnxmltools/PyWavelets installed, 3 new ORM models (OnChainData, GitHubActivity, MLPrediction) with Alembic migrations 009-011**

## Performance

- **Duration:** 4 min
- **Started:** 2026-03-25T17:20:47Z
- **Completed:** 2026-03-25T17:25:06Z
- **Tasks:** 2
- **Files modified:** 7

## Accomplishments
- Installed xgboost, onnxmltools, and PyWavelets as production dependencies
- Added OnChainData, GitHubActivity, MLPrediction ORM models to src/db/models.py
- Created three Alembic migrations (009, 010, 011) with proper revision chain from 008
- Extended Settings with github_token for GitHub API rate limit upgrade
- All 638 existing tests continue to pass

## Task Commits

Each task was committed atomically:

1. **Task 1: Install dependencies and add DB models** - `40bb5c6` (feat)
2. **Task 2: Create Alembic migrations for three new tables** - `9229910` (feat)

## Files Created/Modified
- `pyproject.toml` - Added xgboost, onnxmltools, pywavelets dependencies + mypy overrides
- `uv.lock` - Updated lockfile with new dependency tree
- `src/db/models.py` - Added OnChainData, GitHubActivity, MLPrediction ORM model classes
- `src/config.py` - Added github_token field to Settings class
- `src/db/migrations/versions/009_on_chain_data.py` - Migration for on_chain_data table
- `src/db/migrations/versions/010_github_activity.py` - Migration for github_activity table
- `src/db/migrations/versions/011_ml_predictions.py` - Migration for ml_predictions table

## Decisions Made
- Added mypy ignore_missing_imports overrides for xgboost, onnxmltools, pywt (no py.typed stubs available)
- libomp system dependency required for xgboost on macOS (brew install libomp)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Added mypy overrides for new packages**
- **Found during:** Task 1 (Install dependencies)
- **Issue:** xgboost, onnxmltools, pywt lack py.typed stubs, would cause mypy strict failures
- **Fix:** Added all three to the mypy ignore_missing_imports override list in pyproject.toml
- **Files modified:** pyproject.toml
- **Verification:** Imports succeed without mypy errors
- **Committed in:** 40bb5c6 (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Auto-fix necessary for mypy strict mode compatibility. No scope creep.

## Issues Encountered
- xgboost requires libomp (OpenMP runtime) on macOS -- resolved with `brew install libomp`

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- All three DB tables and ORM models ready for engine implementations in plans 02-05
- xgboost available for ML prediction engine
- PyWavelets available for wavelet-based signal processing
- onnxmltools available for ONNX model export/inference
- github_token config ready for GitHub Activity fetcher

## Self-Check: PASSED

All 7 files verified on disk. Both task commits (40bb5c6, 9229910) confirmed in git log.

---
*Phase: 10-remaining-specialized-engines*
*Completed: 2026-03-25*
