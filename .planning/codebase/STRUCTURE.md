# Codebase Structure

**Analysis Date:** 2026-03-24

## Directory Layout

```
trade-agent/
├── src/                        # All application source code
│   ├── config.py               # Pydantic-settings singleton (Settings + settings)
│   ├── logging.py              # Structlog setup (setup_logging)
│   ├── __init__.py
│   ├── bot/                    # Independent FastAPI bot service
│   │   ├── main.py             # FastAPI app, /health endpoint, uvicorn startup
│   │   └── __init__.py
│   ├── data/                   # Data acquisition, validation, and ingestion
│   │   ├── base.py             # BaseFetcher ABC, OHLCVRow dataclass
│   │   ├── idx_stocks.py       # IDXStockFetcher (yfinance, .JK tickers)
│   │   ├── crypto.py           # CryptoFetcher (ccxt/Binance + CoinGecko fallback)
│   │   ├── validation.py       # validate_rows(), validate_date_coverage()
│   │   ├── staleness.py        # check_staleness() for stock and crypto
│   │   ├── alerts.py           # AlertCollector (batched DATA_STALE / FETCH_FAILURE)
│   │   ├── ingest.py           # ingest_stage() — StageFunc for fetch stage
│   │   ├── backfill.py         # Historical backfill CLI (run_backfill)
│   │   ├── __main__.py         # Enables python -m src.data.backfill
│   │   └── __init__.py
│   ├── db/                     # Database models, engine, repository, migrations
│   │   ├── models.py           # SQLAlchemy ORM models + SEED_ASSETS
│   │   ├── database.py         # Async engine, session factory, get_session, init_db
│   │   ├── price_repo.py       # Raw asyncpg OHLCV repository (upsert_prices, get_latest_date)
│   │   ├── migrations/         # Alembic migration scripts
│   │   │   ├── env.py          # Alembic env config
│   │   │   ├── script.py.mako  # Migration template
│   │   │   └── versions/
│   │   │       ├── 001_initial_schema.py      # Phase 1: assets, pipeline_runs, pipeline_asset_runs, daily_decisions
│   │   │       └── 002_price_history_hypertables.py  # Phase 2: price_history, price_history_hourly, backoff_state (TimescaleDB hypertables)
│   │   └── __init__.py
│   ├── llm/                    # LLM completion wrapper
│   │   ├── client.py           # llm_completion(), LLMResult, LLM_UNAVAILABLE sentinel
│   │   └── __init__.py
│   └── pipeline/               # Pipeline orchestration
│       ├── main.py             # CLI entry point (argparse, asyncio.run)
│       ├── runner.py           # PipelineRunner — checkpointing, timeout, failure routing
│       ├── tiers.py            # DataTier enum, SOURCE_TIERS map, handle_source_failure()
│       └── __init__.py
├── tests/                      # Test suite mirroring src layout
│   ├── conftest.py             # Shared fixtures (test_settings)
│   ├── test_config.py          # Settings tests
│   ├── test_data/              # Tests for src/data/
│   │   ├── conftest.py         # Data test fixtures (mock fetcher, sample rows)
│   │   ├── test_crypto_fetcher.py
│   │   ├── test_idx_fetcher.py
│   │   ├── test_ingest.py
│   │   ├── test_migration.py
│   │   ├── test_price_repo.py
│   │   ├── test_staleness.py
│   │   └── test_validation.py
│   ├── test_db/
│   │   └── test_models.py      # ORM model tests
│   ├── test_llm/
│   │   └── test_client.py      # LLM client tests
│   └── test_pipeline/
│       ├── test_runner.py      # PipelineRunner tests
│       └── test_tiers.py       # Tier classification tests
├── .planning/                  # GSD planning documents (not shipped)
│   ├── codebase/               # Codebase analysis documents
│   └── phases/                 # Phase implementation plans
├── alembic.ini                 # Alembic database migration config
├── pyproject.toml              # Project metadata, deps, tool config (pytest, mypy)
├── Dockerfile                  # Container image definition
├── docker-compose.yml          # Local dev: TimescaleDB only
├── docker-compose.prod.yml     # Production: app + TimescaleDB
├── .env.example                # Required env vars template (safe to commit)
├── .env                        # Local secrets (gitignored)
├── .python-version             # Python 3.13 pinned (used by pyenv/uv)
├── .ruff.toml                  # Ruff linter/formatter config
├── .pre-commit-config.yaml     # Pre-commit hooks
└── uv.lock                     # Dependency lockfile
```

## Directory Purposes

**`src/`:**
- Purpose: All application source code, structured as a Python package
- Contains: Config, logging, and five sub-packages (bot, data, db, llm, pipeline)
- Key files: `src/config.py`, `src/logging.py`

**`src/data/`:**
- Purpose: External data acquisition through to database ingestion
- Contains: Fetcher implementations, validation, staleness detection, alert collection, ingest stage function, backfill utility
- Key files: `src/data/base.py` (contracts), `src/data/ingest.py` (stage function)

**`src/db/`:**
- Purpose: All database concerns — schema, ORM, raw SQL, migrations
- Contains: ORM models with seed data, async engine factory, asyncpg repository, Alembic migrations
- Key files: `src/db/models.py`, `src/db/price_repo.py`, `src/db/database.py`

**`src/pipeline/`:**
- Purpose: Orchestrate multi-stage pipeline execution with durability guarantees
- Contains: CLI entry, `PipelineRunner` with checkpointing, data tier failure classification
- Key files: `src/pipeline/runner.py`, `src/pipeline/tiers.py`

**`src/llm/`:**
- Purpose: Isolated LLM abstraction to protect pipeline from LLM failures
- Contains: Single `llm_completion()` function with retry + model fallback
- Key files: `src/llm/client.py`

**`src/bot/`:**
- Purpose: Independent FastAPI process for monitoring and future Telegram integration
- Contains: FastAPI app with health check
- Key files: `src/bot/main.py`

**`tests/`:**
- Purpose: Test suite mirroring `src/` directory structure
- Contains: pytest tests, conftest fixtures — no integration tests against live DB
- Key files: `tests/conftest.py`, `tests/test_data/conftest.py`

**`src/db/migrations/versions/`:**
- Purpose: Alembic migration history
- Contains: Numbered migration files `NNN_slug.py`
- Key files: `001_initial_schema.py`, `002_price_history_hypertables.py`

## Key File Locations

**Entry Points:**
- `src/pipeline/main.py`: Pipeline CLI — `python -m src.pipeline.main`
- `src/data/__main__.py`: Backfill CLI — `python -m src.data.backfill`
- `src/bot/main.py`: Bot FastAPI service — `python -m src.bot.main`

**Configuration:**
- `src/config.py`: All runtime settings (DB URL, LLM keys, timeouts, log level)
- `alembic.ini`: Alembic migration settings
- `pyproject.toml`: Project deps, pytest config, mypy config
- `.ruff.toml`: Linting/formatting rules

**Core Logic:**
- `src/pipeline/runner.py`: `PipelineRunner` — the central orchestrator
- `src/data/ingest.py`: `ingest_stage()` — the fetch stage handler
- `src/data/base.py`: `BaseFetcher` ABC + `OHLCVRow` — the data contract
- `src/pipeline/tiers.py`: `DataTier` + `handle_source_failure()` — failure routing
- `src/db/price_repo.py`: `upsert_prices()` + `get_latest_date()` — hot-path DB operations

**Schema:**
- `src/db/models.py`: All ORM models (`Asset`, `PipelineRun`, `PipelineAssetRun`, `DailyDecision`, `PriceHistory`, `PriceHistoryHourly`, `BackoffState`) and `SEED_ASSETS`

**Testing:**
- `tests/conftest.py`: Root test fixtures
- `tests/test_data/conftest.py`: Data module fixtures

## Naming Conventions

**Files:**
- Snake_case for all Python source files (e.g., `idx_stocks.py`, `price_repo.py`)
- Test files prefixed with `test_` and matching module name (e.g., `test_ingest.py` tests `ingest.py`)
- Migration files: `NNN_slug.py` where NNN is zero-padded revision number

**Directories:**
- All lowercase, underscore-separated for multi-word (e.g., `test_data/`, `test_pipeline/`)
- Test directories mirror source directories: `tests/test_data/` mirrors `src/data/`

**Classes:**
- PascalCase (e.g., `PipelineRunner`, `CryptoFetcher`, `OHLCVRow`, `AlertCollector`)

**Functions:**
- Snake_case (e.g., `run_pipeline`, `ingest_stage`, `validate_rows`, `check_staleness`)
- Private helpers prefixed with `_` (e.g., `_fetch_ccxt`, `_read_backoff_state`)

**Constants/Sentinels:**
- UPPER_SNAKE_CASE (e.g., `LLM_UNAVAILABLE`, `SOURCE_TIERS`, `SEED_ASSETS`, `COINGECKO_ID_MAP`)

## Where to Add New Code

**New Pipeline Stage (e.g., `analyze`):**
- Stage function: `src/data/<stage_name>.py` implementing `StageFunc` signature `async def analyze_stage(session: AsyncSession, asset: Asset) -> None`
- Wire up in: `src/pipeline/main.py` `stage_funcs` dict passed to `PipelineRunner.run_pipeline()`
- Tests: `tests/test_data/test_<stage_name>.py`

**New Data Fetcher:**
- Implementation: `src/data/<source>.py`, subclass `BaseFetcher` from `src/data/base.py`
- Add `source_name` to `SOURCE_TIERS` dict in `src/pipeline/tiers.py` with appropriate `DataTier`
- Tests: `tests/test_data/test_<source>_fetcher.py`

**New ORM Model:**
- Add to `src/db/models.py`, subclass `Base`
- Create migration: `alembic revision --autogenerate -m "description"`
- Add migration file to `src/db/migrations/versions/`

**New Configuration Value:**
- Add field to `Settings` class in `src/config.py` with type annotation and default

**New Bot Endpoint:**
- Add route to `src/bot/main.py` on the existing `app` FastAPI instance

**Utilities/Shared Helpers:**
- Pure functions with no external dependencies: add to relevant module or create new module in `src/data/` or `src/db/`
- Never import `src/pipeline` or `src/llm` from `src/bot/`

## Special Directories

**`.planning/`:**
- Purpose: GSD workflow planning documents and phase plans
- Generated: No (human/AI authored)
- Committed: Yes

**`.venv/`:**
- Purpose: uv-managed virtual environment
- Generated: Yes (by `uv sync`)
- Committed: No

**`src/db/migrations/versions/`:**
- Purpose: Alembic auto-generated migration history
- Generated: Partially (auto-generate with manual review)
- Committed: Yes

**`plan/`:**
- Purpose: Early-phase planning notes (pre-GSD)
- Generated: No
- Committed: Yes

---

*Structure analysis: 2026-03-24*
