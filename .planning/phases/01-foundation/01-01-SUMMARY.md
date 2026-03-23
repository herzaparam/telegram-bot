---
phase: 01-foundation
plan: 01
subsystem: infra
tags: [pydantic-settings, sqlalchemy, asyncpg, alembic, timescaledb, structlog, docker, ruff]

# Dependency graph
requires: []
provides:
  - "Pydantic Settings configuration (src/config.py)"
  - "SQLAlchemy ORM models: Asset, PipelineRun, PipelineAssetRun, DailyDecision"
  - "Async database engine and session factory (src/db/database.py)"
  - "Alembic migration framework with async support"
  - "TimescaleDB via Docker Compose with health check"
  - "Seed data: 6 assets (3 IDX stocks, 3 crypto)"
  - "Structured logging via structlog (JSON/console)"
  - "Dev tooling: ruff, mypy, pre-commit, pytest"
affects: [01-02, 01-03, 02-data-fetching, 03-analysis-engines]

# Tech tracking
tech-stack:
  added: [pydantic-settings, sqlalchemy, asyncpg, alembic, litellm, structlog, tenacity, httpx, pytest, pytest-asyncio, ruff, mypy, pre-commit]
  patterns: [pydantic-settings-config, sqlalchemy-naming-convention, async-alembic-migrations, structlog-json-logging]

key-files:
  created:
    - src/config.py
    - src/logging.py
    - src/db/models.py
    - src/db/database.py
    - docker-compose.yml
    - alembic.ini
    - src/db/migrations/env.py
    - src/db/migrations/versions/001_initial_schema.py
    - .ruff.toml
    - .pre-commit-config.yaml
    - .env.example
    - .gitignore
    - tests/conftest.py
    - tests/test_config.py
    - tests/test_db/test_models.py
  modified:
    - pyproject.toml

key-decisions:
  - "Used trade_dev as default DB password matching Docker Compose config"
  - "Separate pipeline_asset_runs table for per-asset-per-stage checkpointing (not JSONB in pipeline_runs)"
  - "SQLAlchemy naming conventions for all constraints enabling reversible Alembic migrations"
  - "Async Alembic env.py with sys.path insert for project root imports"

patterns-established:
  - "Config pattern: from src.config import settings -- singleton loaded from .env"
  - "Model pattern: DeclarativeBase with naming_convention MetaData"
  - "Migration pattern: async Alembic with manual revision files"
  - "Test pattern: patch.dict os.environ for isolated Settings tests"

requirements-completed: [DATA-05]

# Metrics
duration: 8min
completed: 2026-03-23
---

# Phase 1 Plan 1: Project Setup and Database Foundation Summary

**Pydantic-settings config, 4 SQLAlchemy models with look-ahead bias prevention, async Alembic migrations, TimescaleDB Docker, and 26 passing tests**

## Performance

- **Duration:** 8 min
- **Started:** 2026-03-23T11:28:17Z
- **Completed:** 2026-03-23T11:36:23Z
- **Tasks:** 2
- **Files modified:** 19

## Accomplishments
- Settings class validates all config from env with sensible defaults (database, LLM, Telegram, logging, timeouts)
- All 4 Phase 1 ORM models defined with correct columns, types, constraints, and foreign keys
- DailyDecision has look-ahead bias prevention columns: decision_price_at, evaluation_price, evaluation_price_at
- Initial Alembic migration creates all tables with TimescaleDB extension enabled and 6 seed assets
- Docker Compose starts TimescaleDB 2.18.0-pg16 with health check passing
- Dev tooling configured: ruff linting, mypy type checking, pre-commit hooks, pytest with asyncio

## Task Commits

Each task was committed atomically:

1. **Task 1: Project setup, config, Docker, and database models** - `16a8bed` (feat)
2. **Task 2: Alembic migrations with seed data** - `1fdd708` (feat)

## Files Created/Modified
- `pyproject.toml` - Dependencies and tool config (pytest, mypy)
- `src/config.py` - Pydantic Settings with all config fields
- `src/logging.py` - Structlog setup for JSON/console output
- `src/db/models.py` - Asset, PipelineRun, PipelineAssetRun, DailyDecision ORM models + SEED_ASSETS
- `src/db/database.py` - Async engine, session factory, init_db
- `docker-compose.yml` - Dev TimescaleDB container
- `alembic.ini` - Alembic configuration
- `src/db/migrations/env.py` - Async Alembic migration runner
- `src/db/migrations/versions/001_initial_schema.py` - Initial schema with all Phase 1 tables and seed data
- `.ruff.toml` - Ruff linter config (py313, line-length 120)
- `.pre-commit-config.yaml` - Ruff lint + format hooks
- `.env.example` - All settings keys with example values
- `.gitignore` - Python cache, env, build artifacts
- `tests/conftest.py` - Shared test fixtures
- `tests/test_config.py` - 10 tests for Settings validation
- `tests/test_db/test_models.py` - 16 tests for ORM models, constraints, and seed data

## Decisions Made
- Used `trade_dev` as default database password to match Docker Compose POSTGRES_PASSWORD
- Chose separate `pipeline_asset_runs` table (Option A from research) over JSONB metadata for per-asset tracking
- Applied SQLAlchemy naming conventions on Base metadata for deterministic constraint names
- Added sys.path insert in Alembic env.py for reliable `from src.` imports
- Overrode alembic.ini URL with async URL from settings in env.py for online mode

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Fixed database password mismatch between config defaults and Docker Compose**
- **Found during:** Task 2 (Alembic migration)
- **Issue:** Config defaults used password `trade` but Docker Compose uses `trade_dev`, causing auth failure
- **Fix:** Updated config.py, alembic.ini, .env.example, and tests to use `trade_dev` consistently
- **Files modified:** src/config.py, alembic.ini, .env.example, tests/test_config.py
- **Verification:** `uv run alembic upgrade head` succeeds, all 26 tests pass
- **Committed in:** 1fdd708 (Task 2 commit)

**2. [Rule 2 - Missing Critical] Added .gitignore for Python cache and sensitive files**
- **Found during:** Task 2 (post-migration)
- **Issue:** __pycache__ directories and .env would be committed without .gitignore
- **Fix:** Created .gitignore with standard Python exclusions
- **Files modified:** .gitignore
- **Verification:** `git status` no longer shows __pycache__ directories
- **Committed in:** 1fdd708 (Task 2 commit)

---

**Total deviations:** 2 auto-fixed (1 blocking, 1 missing critical)
**Impact on plan:** Both fixes necessary for correct operation. No scope creep.

## Issues Encountered
- Docker daemon was not running; started Docker Desktop and waited for readiness before proceeding
- Alembic env.py could not import `src.db.models` because project root was not on sys.path; fixed with sys.path.insert

## User Setup Required
None - no external service configuration required.

## Known Stubs
None - all code is functional, no placeholders.

## Next Phase Readiness
- Database foundation complete: all Phase 1 tables migrated with seed data
- Config, models, and database modules ready for import by subsequent plans
- Plan 01-02 (LLM wrapper) and 01-03 (pipeline runner) can build on this foundation
- TimescaleDB extension enabled, ready for hypertable creation in Phase 2

---
*Phase: 01-foundation*
*Completed: 2026-03-23*
