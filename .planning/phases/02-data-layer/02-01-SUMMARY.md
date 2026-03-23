---
phase: 02-data-layer
plan: 01
subsystem: database
tags: [timescaledb, hypertable, asyncpg, ohlcv, validation, alembic, dataclass]

requires:
  - phase: 01-foundation
    provides: Base ORM, Asset model, Alembic migration 001, async engine

provides:
  - PriceHistory and PriceHistoryHourly ORM models
  - Alembic migration 002 with hypertable creation, compression, retention
  - asyncpg price_repo (upsert_prices, get_latest_date)
  - OHLCVRow dataclass and BaseFetcher ABC
  - OHLCV validation module (validate_rows, validate_date_coverage)
  - BackoffState model for adaptive retry persistence

affects: [02-data-layer-plan-02, 03-engines, 04-llm-verdict, 06-evaluation]

tech-stack:
  added: []
  patterns:
    - "asyncpg raw SQL for OHLCV hot-path (bypass ORM)"
    - "source-inspection smoke tests for Alembic migrations"
    - "structlog capture_logs() for log assertion in tests"
    - "Composite PK on (time, asset_id) for TimescaleDB hypertables"

key-files:
  created:
    - src/data/__init__.py
    - src/data/base.py
    - src/data/validation.py
    - src/db/price_repo.py
    - src/db/migrations/versions/002_price_history_hypertables.py
    - tests/test_data/__init__.py
    - tests/test_data/conftest.py
    - tests/test_data/test_migration.py
    - tests/test_data/test_price_repo.py
    - tests/test_data/test_validation.py
  modified:
    - src/db/models.py

key-decisions:
  - "asyncpg conn typed as Any to avoid missing py.typed stubs from asyncpg"
  - "Migration smoke tests use inspect.getsource() to verify DDL patterns without real TimescaleDB"
  - "structlog.testing.capture_logs() for log assertions instead of manual CapturingLogger"

patterns-established:
  - "TDD with source-inspection for Alembic migrations"
  - "Mock asyncpg connection for price_repo unit tests"
  - "OHLCVRow as the universal exchange format between fetchers and price_repo"

requirements-completed: [DATA-01]

duration: 6min
completed: 2026-03-23
---

# Phase 02 Plan 01: Data Layer Foundation Summary

**TimescaleDB hypertable models with compression/retention policies, asyncpg upsert repo, OHLCVRow/BaseFetcher contracts, and OHLCV validation with structlog rejection logging**

## Performance

- **Duration:** 6 min
- **Started:** 2026-03-23T12:49:22Z
- **Completed:** 2026-03-23T12:55:36Z
- **Tasks:** 2
- **Files modified:** 11

## Accomplishments

- PriceHistory and PriceHistoryHourly ORM models with composite PK on (time, asset_id)
- Alembic migration 002 creates hypertables with 30-day compression and 7-day hourly retention
- asyncpg price_repo with idempotent ON CONFLICT upsert and get_latest_date
- BaseFetcher ABC and OHLCVRow dataclass establishing the data contract
- Validation module rejecting None, NaN, high<low, negative volume with structlog warnings
- BackoffState model for adaptive retry state persistence
- 24 tests passing across migration smoke, price repo mocks, and validation

## Task Commits

Each task was committed atomically (TDD: test then feat):

1. **Task 1: Schema models, migration, price repo** - `5b6cb69` (test: RED), `527ff3b` (feat: GREEN)
2. **Task 2: OHLCV validation module** - `522bb2a` (test: RED), `4b16429` (feat: GREEN)

_TDD tasks each have RED + GREEN commits._

## Files Created/Modified

- `src/data/__init__.py` - Package init
- `src/data/base.py` - OHLCVRow dataclass and BaseFetcher ABC
- `src/data/validation.py` - validate_rows and validate_date_coverage with structlog
- `src/db/models.py` - Added PriceHistory, PriceHistoryHourly, BackoffState models
- `src/db/price_repo.py` - asyncpg upsert_prices and get_latest_date
- `src/db/migrations/versions/002_price_history_hypertables.py` - Hypertable DDL migration
- `tests/test_data/conftest.py` - Shared OHLCV row fixtures
- `tests/test_data/test_migration.py` - Migration DDL smoke tests (7 tests)
- `tests/test_data/test_price_repo.py` - Price repo mock tests (8 tests)
- `tests/test_data/test_validation.py` - Validation tests (10 tests)

## Decisions Made

- Used `Any` type for asyncpg connection parameters since asyncpg lacks py.typed marker
- Migration smoke tests use `inspect.getsource()` for DDL pattern verification without requiring TimescaleDB
- Used `structlog.testing.capture_logs()` context manager for reliable log assertions
- Used `importlib.import_module()` for migration import since module name starts with digit

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed mypy errors in price_repo**
- **Found during:** Overall verification
- **Issue:** asyncpg has no py.typed marker; fetchval return type was Any
- **Fix:** Typed conn as Any, added explicit type annotation for fetchval result
- **Files modified:** src/db/price_repo.py
- **Verification:** `uv run mypy src/data/ src/db/price_repo.py` passes
- **Committed in:** `5810ffb`

**2. [Rule 3 - Blocking] Fixed migration import SyntaxError in test**
- **Found during:** Task 1 GREEN phase
- **Issue:** Python cannot import module names starting with digits (`002_...`)
- **Fix:** Used `importlib.import_module()` instead of direct `from` import
- **Files modified:** tests/test_data/test_migration.py
- **Verification:** All migration smoke tests pass
- **Committed in:** `527ff3b` (part of GREEN commit)

---

**Total deviations:** 2 auto-fixed (1 bug, 1 blocking)
**Impact on plan:** Both fixes were necessary for correctness. No scope creep.

## Issues Encountered

- Pre-existing test failure in `tests/test_config.py::TestSettings::test_default_telegram_settings` due to `.env` file override. Not caused by this plan, not fixed. Logged to deferred items.

## Known Stubs

None - all code is fully wired with no placeholder data.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- OHLCVRow and BaseFetcher contracts ready for Plan 02 fetcher implementations
- price_repo upsert ready for ingest stage integration
- Validation module ready to filter fetcher output before database insertion
- BackoffState model ready for adaptive retry logic

## Self-Check: PASSED

- All 11 created files verified present
- All 5 commit hashes verified in git log
- 24/24 tests passing
- ruff check: all passed
- mypy: no issues found

---
*Phase: 02-data-layer*
*Completed: 2026-03-23*
