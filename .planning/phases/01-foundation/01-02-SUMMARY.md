---
phase: 01-foundation
plan: 02
subsystem: pipeline
tags: [asyncio, sqlalchemy, checkpointing, tiers, pipeline-runner, structlog]

# Dependency graph
requires:
  - phase: 01-foundation/01
    provides: "SQLAlchemy models (PipelineRun, PipelineAssetRun, Asset), async session factory, Settings"
provides:
  - "DataTier enum and SOURCE_TIERS mapping for data source classification"
  - "handle_source_failure routing: CRITICAL raises, IMPORTANT degrades, SUPPLEMENTARY skips"
  - "PipelineRunner with per-asset-per-stage checkpointing and idempotent stage execution"
  - "StageResult dataclass for stage outcome reporting"
  - "Pipeline CLI entry point with --stage, --date, --rerun-failed flags"
affects: [phase-02-fetch, phase-03-engines, phase-04-llm, phase-05-report]

# Tech tracking
tech-stack:
  added: [aiosqlite (dev only, for async SQLite test fixtures)]
  patterns: [TDD red-green-refactor, tier-based failure routing, per-asset checkpointing, idempotent stage execution]

key-files:
  created:
    - src/pipeline/tiers.py
    - src/pipeline/runner.py
    - src/pipeline/main.py
    - tests/test_pipeline/__init__.py
    - tests/test_pipeline/test_tiers.py
    - tests/test_pipeline/test_runner.py
  modified: []

key-decisions:
  - "Unknown data sources default to SUPPLEMENTARY tier (safe default -- avoids pipeline crashes on new sources)"
  - "SQLite + aiosqlite for unit tests with JSONB-to-JSON type swap to avoid PostgreSQL dependency in CI"
  - "Per-asset processing uses individual sessions to prevent one asset rollback from affecting others"

patterns-established:
  - "Tier-based failure routing: CRITICAL raises SourceCriticalError, IMPORTANT returns DegradedResult, SUPPLEMENTARY returns SkippedResult"
  - "Idempotent stages: completed stages return cached result without re-executing"
  - "Partial resume: only incomplete/failed assets are reprocessed on subsequent runs"
  - "Test fixtures: _sqlite_friendly_create_all swaps PostgreSQL-specific types for SQLite compatibility"

requirements-completed: [DATA-04, DATA-06]

# Metrics
duration: 5min
completed: 2026-03-23
---

# Phase 01 Plan 02: Pipeline Runner Summary

**Pipeline runner with per-asset-per-stage checkpointing, tier-based failure routing, and idempotent stage execution using asyncio.wait_for timeouts**

## Performance

- **Duration:** 5 min
- **Started:** 2026-03-23T11:38:36Z
- **Completed:** 2026-03-23T11:43:14Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments
- DataTier enum (CRITICAL/IMPORTANT/SUPPLEMENTARY) with SOURCE_TIERS mapping for all 9 data sources
- handle_source_failure routes by tier: raises SourceCriticalError, returns DegradedResult, or returns SkippedResult
- PipelineRunner creates PipelineRun + PipelineAssetRun checkpoint records in database
- Completed stages are skipped on re-run (idempotent); partial stages resume from last incomplete asset
- Per-asset timeouts via asyncio.wait_for prevent hung API calls from stalling the pipeline
- CLI entry point with --stage, --date, --rerun-failed flags
- 30 tests passing (16 tiers + 14 runner)

## Task Commits

Each task was committed atomically:

1. **Task 1: Data tier classification and failure handling**
   - `2546847` (test) - Failing tests for DataTier, SOURCE_TIERS, handle_source_failure
   - `3aad9fa` (feat) - Implementation of tiers.py with DataTier enum, SOURCE_TIERS, failure handlers

2. **Task 2: Pipeline runner with per-asset-per-stage checkpointing**
   - `0f75688` (test) - Failing tests for PipelineRunner (idempotency, resume, isolation, timeout)
   - `f3e293d` (feat) - Implementation of runner.py and main.py

## Files Created/Modified
- `src/pipeline/tiers.py` - DataTier enum, SOURCE_TIERS mapping, handle_source_failure routing
- `src/pipeline/runner.py` - PipelineRunner with run_stage/run_pipeline, StageResult dataclass
- `src/pipeline/main.py` - CLI entry point with argparse (--stage, --date, --rerun-failed)
- `tests/test_pipeline/__init__.py` - Test package init
- `tests/test_pipeline/test_tiers.py` - 16 tests for tier classification and failure handling
- `tests/test_pipeline/test_runner.py` - 14 tests for pipeline runner (idempotency, resume, isolation, timeout, CLI)

## Decisions Made
- Unknown data sources default to SUPPLEMENTARY tier (safe default -- avoids pipeline crashes on new sources)
- Used aiosqlite for in-memory async SQLite test fixtures with a JSONB-to-JSON type swap helper to avoid requiring PostgreSQL for unit tests
- Per-asset processing uses individual DB sessions so one asset's rollback doesn't affect others

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Added aiosqlite dev dependency for async SQLite tests**
- **Found during:** Task 2 (Pipeline runner tests)
- **Issue:** Tests need async SQLite for in-memory database but aiosqlite wasn't in dependencies
- **Fix:** Added aiosqlite as dev dependency via `uv add --dev aiosqlite`
- **Files modified:** pyproject.toml, uv.lock
- **Verification:** All 14 runner tests pass with async SQLite engine
- **Committed in:** `0f75688` (Task 2 test commit)

**2. [Rule 3 - Blocking] Created _sqlite_friendly_create_all helper for JSONB compatibility**
- **Found during:** Task 2 (Pipeline runner tests)
- **Issue:** SQLite cannot handle PostgreSQL JSONB type; Base.metadata.create_all fails
- **Fix:** Created helper that temporarily swaps JSONB columns to JSON for table creation
- **Files modified:** tests/test_pipeline/test_runner.py
- **Verification:** All tables created successfully in SQLite; tests pass
- **Committed in:** `f3e293d` (Task 2 feat commit)

---

**Total deviations:** 2 auto-fixed (2 blocking)
**Impact on plan:** Both fixes necessary for test infrastructure. No scope creep.

## Issues Encountered
- Pre-existing mypy errors in src/db/models.py (generic dict without type params) -- out of scope for this plan, not introduced by our changes

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Pipeline runner ready for Phase 2 (fetch stage implementation)
- Stage functions can be registered via stage_funcs dict passed to run_pipeline
- Tier-based failure handling ready for all data source integrations
- Per-asset timeout values configurable via Settings (timeout_fetch, timeout_analyze, timeout_llm)

---
*Phase: 01-foundation*
*Completed: 2026-03-23*
