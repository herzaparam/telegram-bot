---
phase: 03-technical-engine-pipeline-shell
plan: 01
subsystem: engines
tags: [baseengine, signal, sqlalchemy, alembic, pandas-ta-classic, pmdarima, timescaledb]

# Dependency graph
requires:
  - phase: 01-foundation
    provides: "SQLAlchemy Base, models.py, Settings, Alembic migration pattern"
  - phase: 02-data-ingestion
    provides: "price_history tables, asyncpg price_repo pattern, migration 002"
provides:
  - "BaseEngine ABC with analyze()/category contract"
  - "Signal frozen dataclass for engine output"
  - "SignalRecord ORM model for signal persistence"
  - "Alembic migration 003 for signals table"
  - "SignalRepository with UPSERT and query methods"
  - "Indicator weight configuration (technical + quantitative)"
  - "Test fixtures with synthetic OHLCV DataFrames (200/50/10/empty)"
affects: [03-02-technical-engine, 03-03-quantitative-engine, 03-04-pipeline-shell]

# Tech tracking
tech-stack:
  added: [pandas-ta-classic, pmdarima]
  patterns: [BaseEngine ABC, Signal dataclass, SignalRepository UPSERT]

key-files:
  created:
    - src/engines/__init__.py
    - src/engines/base.py
    - src/db/signal_repo.py
    - src/db/migrations/versions/003_signals_table.py
    - tests/test_engines/__init__.py
    - tests/test_engines/conftest.py
    - tests/test_engines/test_base_engine.py
    - tests/test_db/test_signal_repo.py
  modified:
    - pyproject.toml
    - src/db/models.py
    - src/config.py

key-decisions:
  - "SignalRepository uses SQLAlchemy ORM with pg_insert for UPSERT (not raw asyncpg) matching plan specification"
  - "Signal dataclass is frozen for immutability after engine computation"
  - "signals table is regular PostgreSQL (not hypertable) since signals are not time-series hot-path data"

patterns-established:
  - "BaseEngine ABC: subclasses implement analyze() and category property"
  - "Signal dataclass: frozen, carries score/confidence/reasoning/indicators/data_quality"
  - "SignalRepository: session-based async methods with pg_insert UPSERT on conflict"
  - "Engine test fixtures: sample_price_df_200/50/10/empty for various data sufficiency scenarios"

requirements-completed: [ENGN-01, ENGN-03]

# Metrics
duration: 4min
completed: 2026-03-24
---

# Phase 03 Plan 01: Engine Foundation Summary

**BaseEngine ABC, Signal dataclass, SignalRecord ORM model, 003 migration, SignalRepository with UPSERT, and indicator weight config for technical/quantitative engines**

## Performance

- **Duration:** 4 min
- **Started:** 2026-03-24T07:51:58Z
- **Completed:** 2026-03-24T07:55:28Z
- **Tasks:** 2
- **Files modified:** 11

## Accomplishments
- BaseEngine ABC defines analyze()/category contract that all 15 engine types will implement
- Signal frozen dataclass carries score/confidence/reasoning/indicators/data_quality from engines to repository
- SignalRecord ORM model and 003 migration create signals table with UPSERT-friendly unique constraint
- SignalRepository provides async upsert_signals, get_signals_for_asset, get_latest_signals
- pandas-ta-classic and pmdarima installed as project dependencies
- Indicator weight configuration for RSI/MACD/Bollinger/EMA/volume/trend and momentum/mean-reversion/ARIMA
- 22 tests covering Signal, BaseEngine, SignalRecord, and SignalRepository

## Task Commits

Each task was committed atomically:

1. **Task 1: Install dependencies, create BaseEngine ABC, Signal, SignalRecord, migration, SignalRepository, config** - `c2ca51f` (feat)
2. **Task 2: Test scaffolding for engines and signal repo** - `158b264` (test)

## Files Created/Modified
- `src/engines/__init__.py` - Empty package init for engines module
- `src/engines/base.py` - BaseEngine ABC and Signal frozen dataclass
- `src/db/models.py` - Added SignalRecord ORM model
- `src/db/signal_repo.py` - SignalRepository with UPSERT and query methods
- `src/db/migrations/versions/003_signals_table.py` - Alembic migration for signals table
- `src/config.py` - Added technical and quantitative indicator weight fields
- `pyproject.toml` - Added pandas-ta-classic and pmdarima dependencies
- `tests/test_engines/__init__.py` - Test package init
- `tests/test_engines/conftest.py` - Synthetic OHLCV DataFrame fixtures (200/50/10/empty)
- `tests/test_engines/test_base_engine.py` - Tests for Signal, BaseEngine, SignalRecord
- `tests/test_db/test_signal_repo.py` - Tests for SignalRepository with mocked sessions

## Decisions Made
- SignalRepository uses SQLAlchemy ORM with pg_insert for UPSERT (not raw asyncpg) -- plan specified ORM approach for type safety
- Signal dataclass is frozen for immutability after engine computation
- signals table is regular PostgreSQL (not hypertable) since signals are low-volume relational data
- Tests use mocked AsyncSession for SignalRepository since pg_insert is PostgreSQL-specific

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- BaseEngine ABC ready for TechnicalEngine (03-02) and QuantitativeEngine (03-03) implementation
- SignalRepository ready for pipeline integration in 03-04
- Test fixtures (sample_price_df_200/50/10) ready for engine-specific tests
- pandas-ta-classic and pmdarima installed and available

---
*Phase: 03-technical-engine-pipeline-shell*
*Completed: 2026-03-24*
