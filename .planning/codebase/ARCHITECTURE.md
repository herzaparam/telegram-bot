# Architecture

**Analysis Date:** 2026-03-24

## Pattern Overview

**Overall:** Async pipeline with per-asset checkpointing, layered into data acquisition, persistence, orchestration, and presentation tiers.

**Key Characteristics:**
- Fully async Python (asyncio) — blocking calls (yfinance) wrapped in `run_in_executor`
- Two independent processes: pipeline (`src/pipeline`) and bot (`src/bot`), explicitly prohibited from cross-importing
- Per-asset, per-stage checkpointing stored in PostgreSQL — pipeline is kill/restart safe with zero wasted work
- Data source tier system classifies failures as CRITICAL (skip asset), IMPORTANT (degrade), or SUPPLEMENTARY (ignore)
- Dual database clients: SQLAlchemy async ORM for pipeline orchestration, raw `asyncpg` for hot-path bulk OHLCV upserts

## Layers

**Configuration:**
- Purpose: Centralized environment-driven settings
- Location: `src/config.py`
- Contains: Single `Settings` class (pydantic-settings), singleton `settings` object
- Depends on: `.env` file or environment variables
- Used by: All modules that need runtime configuration

**Logging:**
- Purpose: Structured JSON logging setup
- Location: `src/logging.py`
- Contains: `setup_logging()` function configuring structlog with JSON or console renderer
- Depends on: `structlog`
- Used by: Pipeline and bot entry points at startup

**Data Fetcher Layer:**
- Purpose: Abstract external market data acquisition
- Location: `src/data/`
- Contains: `BaseFetcher` ABC, `IDXStockFetcher` (yfinance), `CryptoFetcher` (ccxt/Binance + CoinGecko fallback)
- Depends on: yfinance, ccxt, httpx, tenacity (retry), `src/data/base.py`
- Used by: `src/data/ingest.py`, `src/data/backfill.py`

**Data Processing Layer:**
- Purpose: Validate, check staleness, and collect alerts after fetching
- Location: `src/data/`
- Contains: `validate_rows()` in `validation.py`, `check_staleness()` in `staleness.py`, `AlertCollector` in `alerts.py`
- Depends on: `src/data/base.py` (OHLCVRow)
- Used by: `src/data/ingest.py`, fetchers themselves pre-return

**Database Layer:**
- Purpose: ORM models, async engine, raw SQL repository for OHLCV
- Location: `src/db/`
- Contains: `models.py` (SQLAlchemy ORM), `database.py` (engine/session factory), `price_repo.py` (raw asyncpg repository), `migrations/` (Alembic)
- Depends on: SQLAlchemy, asyncpg, TimescaleDB
- Used by: Pipeline runner, ingest stage, backfill

**Ingest Stage:**
- Purpose: Orchestrate fetch → validate → upsert → staleness-check for one asset
- Location: `src/data/ingest.py`
- Contains: `ingest_stage(session, asset)` — implements `StageFunc` signature
- Depends on: fetchers, validation, staleness, price_repo, tiers
- Used by: `PipelineRunner` via `stage_funcs` mapping

**Pipeline Orchestration Layer:**
- Purpose: Run stages with per-asset checkpointing, timeout enforcement, and failure triage
- Location: `src/pipeline/`
- Contains: `PipelineRunner` class (`runner.py`), `tiers.py` (source tier classification), `main.py` (CLI entry point)
- Depends on: `src/db/models.py`, `src/config.py`, `src/data/ingest.py`
- Used by: CLI (`python -m src.pipeline.main`)

**LLM Layer:**
- Purpose: Provide a single async LLM completion function with retry, fallback, and never-raise guarantee
- Location: `src/llm/client.py`
- Contains: `llm_completion()`, `LLMResult` dataclass, `LLM_UNAVAILABLE` sentinel
- Depends on: litellm, `src/config.py`
- Used by: Future analyze/decide pipeline stages

**Bot Layer:**
- Purpose: Independent FastAPI service for health checks and future Telegram integration
- Location: `src/bot/main.py`
- Contains: FastAPI `app`, `/health` endpoint, `main()` startup function
- Depends on: FastAPI, uvicorn, `src/config.py`, `src/logging.py`
- Explicitly MUST NOT import from: `src/pipeline` or `src/llm`

**Backfill Utility:**
- Purpose: Standalone CLI for historical data ingestion
- Location: `src/data/backfill.py`
- Contains: `run_backfill()`, `parse_args()`, semaphore-limited concurrent fetch
- Depends on: fetchers, validation, price_repo, asyncpg
- Used by: `python -m src.data.backfill`

## Data Flow

**Normal Pipeline Run:**

1. `python -m src.pipeline.main` → `PipelineRunner.run_pipeline(run_date, stages)`
2. For each stage, `run_stage()` creates or resumes a `PipelineRun` record
3. For each active `Asset`, a `PipelineAssetRun` record is created with status `pending`
4. `stage_func(session, asset)` is called with a per-call `asyncio.wait_for` timeout
5. For the `fetch` stage: `ingest_stage()` selects a fetcher based on `asset.asset_type`
6. Fetcher applies adaptive backoff delay from `BackoffState` DB record, then calls external API
7. Returned `OHLCVRow` list is validated via `validate_rows()`
8. Valid rows are bulk-upserted via raw asyncpg `ON CONFLICT DO UPDATE`
9. Staleness check runs against latest stored timestamp; alerts are batched into `AlertCollector`
10. `PipelineAssetRun.status` is set to `completed`, `failed`, or `skipped`
11. After all assets, `PipelineRun.status` is set to `completed`, `partial`, or `failed`

**Crypto Fetch Flow (two-tier fallback):**

1. `CryptoFetcher.fetch()` attempts ccxt/Binance with pagination + tenacity retry
2. On any ccxt exception, falls back to CoinGecko free API via httpx
3. Both paths return validated `list[OHLCVRow]`
4. Hourly candles (last 7 days) fetched separately via `fetch_hourly()` — ccxt only, no fallback

**State Management:**
- Pipeline state: `PipelineRun` and `PipelineAssetRun` rows in PostgreSQL
- Adaptive backoff state: `BackoffState` rows in PostgreSQL (persist across runs)
- Alert state: `AlertCollector` module-level singleton, reset at pipeline run start

## Key Abstractions

**BaseFetcher:**
- Purpose: Contract for all market data sources
- Examples: `src/data/idx_stocks.py` (IDXStockFetcher), `src/data/crypto.py` (CryptoFetcher)
- Pattern: Abstract base class with `source_name` property and async `fetch()` method

**OHLCVRow:**
- Purpose: Canonical candle data transfer object between fetcher and database
- Examples: `src/data/base.py`
- Pattern: Plain `@dataclass` with typed fields: `time`, `asset_id`, `open/high/low/close/volume`, `source`

**StageFunc:**
- Purpose: Type alias defining the per-asset stage handler contract
- Examples: `ingest_stage` in `src/data/ingest.py` implements this signature
- Pattern: `Callable[[AsyncSession, Asset], Awaitable[None]]` — raises on unrecoverable failure, raises `SourceCriticalError` to skip

**DataTier / SourceCriticalError:**
- Purpose: Classify data source failures and route them to the correct pipeline behavior
- Examples: `src/pipeline/tiers.py`
- Pattern: `CRITICAL` raises `SourceCriticalError` (asset skipped), `IMPORTANT` returns `DegradedResult`, `SUPPLEMENTARY` returns `SkippedResult`

**Settings:**
- Purpose: Single source of truth for all configuration
- Examples: `src/config.py`
- Pattern: pydantic-settings `BaseSettings` singleton loaded from `.env`

## Entry Points

**Pipeline CLI:**
- Location: `src/pipeline/main.py`
- Invocation: `python -m src.pipeline.main [--stage] [--date] [--rerun-failed]`
- Responsibilities: Parse CLI args, initialize logging, create `PipelineRunner`, run pipeline, log stage results

**Backfill CLI:**
- Location: `src/data/backfill.py`, `src/data/__main__.py`
- Invocation: `python -m src.data.backfill [--from] [--to] [--assets] [--type]`
- Responsibilities: Parse args, connect raw asyncpg, fan out fetch tasks with `asyncio.Semaphore(5)`, upsert results

**Bot Service:**
- Location: `src/bot/main.py`
- Invocation: `python -m src.bot.main`
- Responsibilities: Start FastAPI/uvicorn on port 8000, expose `/health` endpoint

**Root main.py:**
- Location: `main.py` (project root)
- Note: Stub file, only prints hello — not used by any real flow

## Error Handling

**Strategy:** Explicit error routing via tier classification; LLM calls never raise; pipeline runner catches all exceptions per-asset to prevent one failure from blocking others.

**Patterns:**
- `SourceCriticalError` raised by `handle_source_failure()` when a CRITICAL source fails — caught by `PipelineRunner.run_stage()`, sets asset status to `skipped`
- `TimeoutError` caught separately by `PipelineRunner` (from `asyncio.wait_for`) — sets status to `failed`, increments `retry_count`
- All other exceptions caught by `PipelineRunner` generic handler — sets status to `failed`, stores `error_message`
- `llm_completion()` catches all exceptions internally, returns `LLM_UNAVAILABLE` sentinel — callers check `result.model_used == "none"`
- Fetcher-level retries via tenacity: 3 attempts, exponential backoff (2–30s) on network/timeout errors

## Cross-Cutting Concerns

**Logging:** structlog with bound context (`component`, `asset`, `stage`). JSON format in production, console in dev. Configured once at startup via `src/logging.py`. All modules use `structlog.get_logger(__name__)`.

**Validation:** Applied at fetcher boundary before any DB write. `validate_rows()` in `src/data/validation.py` rejects null/NaN fields, invalid high/low, negative volume. Returns both valid and rejected rows; rejections are logged but do not halt processing.

**Authentication:** No application-layer auth. Bot service has no auth on `/health`. LLM auth via `OPENAI_API_KEY` env var passed through litellm.

---

*Architecture analysis: 2026-03-24*
