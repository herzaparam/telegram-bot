# Phase 1: Foundation - Research

**Researched:** 2026-03-23
**Domain:** Python project infrastructure -- Docker Compose, config management, database schema, LLM wrapper, pipeline checkpointing, structured logging
**Confidence:** HIGH

## Summary

Phase 1 is a greenfield infrastructure phase: no existing code beyond a stub `pyproject.toml` and empty `main.py`. The work involves standing up a Python project with Docker Compose (TimescaleDB, bot, pipeline), config management via pydantic-settings, an LLM wrapper with retry/fallback via LiteLLM, per-asset-per-stage pipeline checkpointing, a data source tier classification system, and a decision schema that prevents look-ahead bias.

All chosen technologies are mature and well-documented. The primary risk is the gap between the ARCHITECTURE.md `pipeline_runs` schema (which tracks per-stage only) and the CONTEXT.md requirement for per-asset-per-stage checkpointing. The schema needs to be extended to track individual asset progress within each stage. The LLM wrapper must return a deterministic fallback (not crash) when OpenAI is unreachable.

**Primary recommendation:** Follow ARCHITECTURE.md as the blueprint but extend `pipeline_runs` to support per-asset-per-stage granularity. Use uv for dependency management (not pip/requirements.txt). Development uses local Python with Docker only for TimescaleDB.

<user_constraints>

## User Constraints (from CONTEXT.md)

### Locked Decisions
- Local Python (uv) + Docker only for TimescaleDB during development
- uv as package manager (pyproject.toml + uv.lock already initialized)
- Python 3.13+ target (already set in pyproject.toml)
- src/ layout matching ARCHITECTURE.md (e.g., `src/config.py`, `src/bot/main.py`)
- pytest for testing (with pytest-asyncio for async code)
- ruff + mypy for code quality (linting, formatting, and type checking)
- Pre-commit hooks with ruff enabled
- Phase 1 tables only: assets, pipeline_runs, daily_decisions (plus config/data-tier tables)
- Other tables added in their respective phases via Alembic migrations
- Alembic for all database migrations, auto-generated from SQLAlchemy models
- daily_decisions includes decision_price and evaluation_price with explicit timestamps from day one
- Default seed data for assets table (BBCA.JK, BTC/USDT, ETH/USDT and others)
- Per-asset-per-stage checkpointing (zero wasted work on restart)
- When an asset fails mid-stage, continue processing remaining assets and mark failed one for retry
- Per-asset timeouts to prevent hung API calls
- structlog for structured JSON logging
- Critical failures alert via Telegram AND log to stdout
- Default log level INFO in production, DEBUG via environment variable

### Claude's Discretion
- Exact Docker Compose configuration details (resource limits, health check intervals)
- LLM wrapper retry strategy (backoff timing, max retries)
- Deterministic fallback implementation when LLM is unavailable
- Per-asset timeout values (specific seconds per stage)
- structlog configuration and context binding patterns
- Pre-commit hook configuration details
- Seed data: which specific assets to include beyond BBCA.JK, BTC/USDT, ETH/USDT

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope

</user_constraints>

<phase_requirements>

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| DATA-04 | Pipeline stages are idempotent and restartable from point of failure | Per-asset-per-stage checkpointing in `pipeline_runs` table; stage runner checks last successful checkpoint before starting |
| DATA-05 | Pipeline tracks execution state in pipeline_runs table | Extended `pipeline_runs` schema with asset-level tracking via `pipeline_asset_runs` table or JSONB metadata column |
| DATA-06 | System classifies data sources by tier (critical/important/supplementary) and degrades gracefully on failure | `DataTier` enum + `SOURCE_TIERS` mapping from ARCHITECTURE.md; tier-based exception handling in pipeline runner |

</phase_requirements>

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pydantic-settings | 2.13.1 | Type-safe config from .env + env vars | Standard for Python config; validates at startup, SecretStr for sensitive values |
| sqlalchemy | 2.0.48 | ORM models + async sessions for relational data | Industry standard; Alembic autogenerate requires it; async mode via asyncpg |
| asyncpg | 0.31.0 | Fast async PostgreSQL driver | ~0.1ms/query; required for SQLAlchemy async dialect |
| alembic | 1.18.4 | Database migrations | Only serious migration tool for SQLAlchemy; autogenerate from models |
| litellm | 1.82.6 | LLM abstraction with retry + fallback | Swap between GPT-4o-mini / Gemini Flash / DeepSeek without code changes |
| structlog | 25.5.0 | Structured JSON logging | Context-binding, processors, stdlib integration; standard for production Python |
| tenacity | 9.1.4 | Retry with exponential backoff | Used by LiteLLM internally; also needed for data fetcher retries |
| httpx | 0.28.1 | Async HTTP client | Async, connection pooling, HTTP/2; replaces requests for async code |

### Dev / Testing

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pytest | 9.0.2 | Test framework | All tests |
| pytest-asyncio | 1.3.0 | Async test support | Testing async database, HTTP, pipeline code |
| ruff | 0.15.7 | Linter + formatter | Pre-commit + CI; replaces flake8, isort, black |
| mypy | 1.19.1 | Type checking | Static analysis on src/ |

### Infrastructure

| Component | Version/Tag | Purpose |
|-----------|-------------|---------|
| TimescaleDB | `timescale/timescaledb:2.18.0-pg16` | Time-series DB (pinned, not :latest) |
| Docker Compose | v2.40.3 (installed) | Service orchestration |
| uv | 0.7.0 (installed) | Package management + venv |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| pydantic-settings | python-dotenv + dataclass | Loses validation, type coercion, SecretStr |
| structlog | stdlib logging | Loses structured context, JSON output, processor pipeline |
| litellm | openai SDK directly | Loses model portability, built-in fallback/retry |
| tenacity | manual retry loop | Tenacity handles jitter, backoff, retry conditions correctly |
| asyncpg | psycopg3 async | asyncpg is faster for bulk reads; psycopg3 is catching up but asyncpg is more battle-tested |

**Installation (via uv):**
```bash
uv add pydantic-settings sqlalchemy[asyncio] asyncpg alembic litellm structlog tenacity httpx
uv add --dev pytest pytest-asyncio ruff mypy
```

## Architecture Patterns

### Recommended Project Structure

Following ARCHITECTURE.md, adapted for Phase 1 scope:

```
trade-agent/
  src/
    __init__.py
    config.py                   # pydantic-settings BaseSettings
    db/
      __init__.py
      models.py                 # SQLAlchemy ORM: assets, pipeline_runs, pipeline_asset_runs, daily_decisions
      database.py               # async engine + session factory
      migrations/               # Alembic directory
        env.py                  # async migration runner
        versions/
    llm/
      __init__.py
      client.py                 # LiteLLM wrapper with retry, fallback, LLM_UNAVAILABLE sentinel
    pipeline/
      __init__.py
      main.py                   # Pipeline entry point
      runner.py                 # Stage orchestration + checkpoint logic
      tiers.py                  # DataTier enum + SOURCE_TIERS mapping
    bot/
      __init__.py
      main.py                   # Bot entry point (stub for Phase 1, just health check)
  tests/
    __init__.py
    conftest.py                 # shared fixtures (db session, test config)
    test_config.py
    test_db/
      test_models.py
      test_migrations.py
    test_llm/
      test_client.py
    test_pipeline/
      test_runner.py
      test_tiers.py
  docker-compose.yml            # TimescaleDB only (dev mode)
  docker-compose.prod.yml       # Full stack (bot + pipeline + db) for production
  Dockerfile
  .env.example
  alembic.ini
  pyproject.toml
  .pre-commit-config.yaml
```

### Pattern 1: Pydantic Settings Configuration

**What:** Centralized, validated configuration with environment variable overrides.
**When to use:** Every module imports `from src.config import settings`.

```python
# src/config.py
from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Database
    database_url: str = "postgresql+asyncpg://trade:trade@localhost:5432/trade_agent"

    # LLM
    openai_api_key: SecretStr = SecretStr("")
    llm_primary_model: str = "gpt-4o-mini"
    llm_fallback_model: str = "gemini/gemini-2.0-flash"
    llm_max_retries: int = 3
    llm_timeout: int = 30

    # Telegram
    telegram_bot_token: SecretStr = SecretStr("")
    telegram_chat_id: str = ""

    # Logging
    log_level: str = "INFO"
    log_format: str = "json"  # "json" for production, "console" for dev

    # Pipeline timeouts (seconds)
    timeout_fetch: int = 60
    timeout_analyze: int = 120
    timeout_llm: int = 30

settings = Settings()
```

### Pattern 2: Per-Asset-Per-Stage Checkpointing

**What:** Track each asset's progress within each pipeline stage so restarts skip completed work.
**When to use:** Pipeline runner checks checkpoints before processing each asset.

The ARCHITECTURE.md schema has `pipeline_runs` with `UNIQUE(run_date, stage)` -- this only tracks stage-level completion. The CONTEXT.md requires per-asset granularity. Two approaches:

**Option A (Recommended): Separate `pipeline_asset_runs` table**
```python
# pipeline_runs: one row per (run_date, stage) -- tracks stage status
# pipeline_asset_runs: one row per (run_id, asset_id) -- tracks asset within stage

class PipelineRun(Base):
    __tablename__ = "pipeline_runs"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    run_date: Mapped[date]
    stage: Mapped[str]          # "fetch", "analyze", "decide", "report"
    status: Mapped[str]         # "running", "completed", "failed", "partial"
    started_at: Mapped[datetime | None]
    completed_at: Mapped[datetime | None]
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSONB)
    __table_args__ = (UniqueConstraint("run_date", "stage"),)

class PipelineAssetRun(Base):
    __tablename__ = "pipeline_asset_runs"
    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("pipeline_runs.id"))
    asset_id: Mapped[int] = mapped_column(ForeignKey("assets.id"))
    status: Mapped[str]         # "pending", "running", "completed", "failed", "skipped"
    started_at: Mapped[datetime | None]
    completed_at: Mapped[datetime | None]
    error_message: Mapped[str | None]
    retry_count: Mapped[int] = mapped_column(default=0)
    __table_args__ = (UniqueConstraint("run_id", "asset_id"),)
```

**Option B: JSONB metadata column** -- store asset progress as JSON in `pipeline_runs.metadata`. Simpler but harder to query and lacks FK constraints.

**Recommendation:** Option A. The per-asset table makes checkpoint queries trivial (`SELECT asset_id FROM pipeline_asset_runs WHERE run_id = ? AND status != 'completed'`) and supports the retry-failed-assets requirement directly.

### Pattern 3: LLM Wrapper with Deterministic Fallback

**What:** Wrap LiteLLM to handle retries, model fallback, and return a sentinel result when all LLMs fail.
**When to use:** All LLM calls go through this wrapper.

```python
# src/llm/client.py
import litellm
from dataclasses import dataclass

@dataclass
class LLMResult:
    content: str
    model_used: str
    is_fallback: bool = False  # True when LLM_UNAVAILABLE

LLM_UNAVAILABLE = LLMResult(
    content="",
    model_used="none",
    is_fallback=True,
)

async def llm_completion(
    messages: list[dict],
    model: str | None = None,
    fallback_models: list[str] | None = None,
    num_retries: int = 3,
    timeout: int = 30,
) -> LLMResult:
    """Call LLM with retry + fallback. Returns LLM_UNAVAILABLE on total failure."""
    model = model or settings.llm_primary_model
    fallbacks = fallback_models or [settings.llm_fallback_model]

    try:
        response = await litellm.acompletion(
            model=model,
            messages=messages,
            num_retries=num_retries,
            timeout=timeout,
            fallbacks=fallbacks,
        )
        return LLMResult(
            content=response.choices[0].message.content,
            model_used=response.model,
        )
    except Exception:
        # All retries + fallbacks exhausted
        log.error("llm_all_models_failed", model=model, fallbacks=fallbacks)
        return LLM_UNAVAILABLE
```

### Pattern 4: Data Tier Classification

**What:** Classify data sources by criticality; pipeline degrades gracefully instead of crashing.
**When to use:** Every data fetch operation checks the tier before deciding how to handle failures.

```python
# src/pipeline/tiers.py
from enum import StrEnum

class DataTier(StrEnum):
    CRITICAL = "critical"           # Pipeline cannot produce useful output
    IMPORTANT = "important"         # Degrades quality significantly
    SUPPLEMENTARY = "supplementary" # Nice to have

SOURCE_TIERS: dict[str, DataTier] = {
    "price_ohlcv":     DataTier.CRITICAL,
    "orderbook":       DataTier.IMPORTANT,
    "news_sentiment":  DataTier.SUPPLEMENTARY,
    "social_metrics":  DataTier.SUPPLEMENTARY,
    "onchain_data":    DataTier.SUPPLEMENTARY,
    "macro_data":      DataTier.IMPORTANT,
    "alt_data":        DataTier.SUPPLEMENTARY,
}
```

### Pattern 5: Structlog Configuration

**What:** Structured JSON logging with context binding per pipeline run and asset.

```python
# src/logging.py
import structlog
import logging

def setup_logging(log_level: str = "INFO", log_format: str = "json") -> None:
    shared_processors = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
    ]

    if log_format == "json":
        renderer = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer()

    structlog.configure(
        processors=[
            *shared_processors,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    formatter = structlog.stdlib.ProcessorFormatter(
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            renderer,
        ],
    )

    handler = logging.StreamHandler()
    handler.setFormatter(formatter)

    root = logging.getLogger()
    root.addHandler(handler)
    root.setLevel(getattr(logging, log_level.upper()))
```

### Anti-Patterns to Avoid

- **Importing pipeline modules from bot process:** The two-process model is a hard constraint. Bot and pipeline share ONLY the database. No cross-imports.
- **Using `asyncio.gather()` for CPU-bound engine work:** This starves the event loop. Engines run synchronously per the architecture.
- **Tracking pipeline progress only at stage level:** Must track per-asset within each stage for zero-wasted-work restarts.
- **Using `:latest` Docker image tags:** Pin TimescaleDB to `2.18.0-pg16` to avoid surprise major version upgrades that require `pg_upgrade`.
- **Calling `structlog.get_logger().bind()` at module scope:** The logger is a lazy proxy at import time; bind in function/method scope only.
- **Storing `requirements.txt` alongside `pyproject.toml`:** uv manages dependencies via `pyproject.toml` + `uv.lock`. No `requirements.txt`.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| LLM retry + fallback | Custom retry loop with requests | LiteLLM `num_retries` + `fallbacks` | Handles rate limits, backoff, jitter, model-specific errors |
| Config validation | Manual os.environ parsing | pydantic-settings `BaseSettings` | Type coercion, SecretStr, .env loading, validation errors at startup |
| Database migrations | Raw SQL files | Alembic autogenerate from SQLAlchemy models | Tracks migration history, handles up/down, schema diffing |
| Structured logging | stdlib `logging.basicConfig` | structlog with processor pipeline | Context binding, JSON output, request correlation |
| Exponential backoff | `time.sleep(2 ** attempt)` | tenacity `@retry` decorator | Handles jitter, max attempts, specific exception filtering |
| Async DB sessions | Manual connection pool | SQLAlchemy 2.0 async_session + asyncpg | Connection pooling, transaction management, type safety |

**Key insight:** Every "simple" retry/config/logging system eventually grows to need the features these libraries already provide. Starting with them avoids a rewrite.

## Common Pitfalls

### Pitfall 1: ARCHITECTURE.md Schema vs CONTEXT.md Requirements Mismatch

**What goes wrong:** The ARCHITECTURE.md `pipeline_runs` table has `UNIQUE(run_date, stage)` with no per-asset tracking. Building this as-is means you can only restart at stage boundaries, not per-asset.
**Why it happens:** ARCHITECTURE.md was written before the per-asset-per-stage checkpoint requirement was articulated.
**How to avoid:** Add a `pipeline_asset_runs` table (see Pattern 2 above). Keep `pipeline_runs` for stage-level status, add child table for asset-level tracking.
**Warning signs:** If the plan has no asset-level checkpoint table, the success criteria #2 (restart from last checkpoint) will not be achievable at per-asset granularity.

### Pitfall 2: daily_decisions Schema Missing Look-Ahead Bias Prevention Columns

**What goes wrong:** The ARCHITECTURE.md `daily_decisions` table has `price_at_decision` but no separate `evaluation_price` or explicit timestamps for when each price was captured. This enables accidental look-ahead bias in accuracy calculations.
**Why it happens:** The ARCHITECTURE.md schema stores decision price but evaluation happens in a separate `evaluations` table. However, CONTEXT.md success criteria #5 requires explicit timestamps in the decisions table itself.
**How to avoid:** Add `decision_price`, `decision_price_at` (timestamptz), `evaluation_price`, `evaluation_price_at` (timestamptz) columns to `daily_decisions`. The evaluation columns are NULL until the next day's evaluation runs.
**Warning signs:** If accuracy is ever computed using a price without a recorded capture timestamp, look-ahead bias is possible.

### Pitfall 3: Alembic + TimescaleDB Hypertable Interaction

**What goes wrong:** Alembic autogenerate does not understand `create_hypertable()` or TimescaleDB-specific DDL. Running `alembic downgrade` on a hypertable can fail.
**Why it happens:** Alembic only knows standard SQLAlchemy DDL operations.
**How to avoid:** Phase 1 does not create hypertables (price_history is Phase 2). But set up Alembic with `run_migrations_online()` configured for async, and add a convention for putting `op.execute("SELECT create_hypertable(...)")` in migration files manually when needed.
**Warning signs:** Autogenerated migration for a hypertable table will not include the `create_hypertable` call.

### Pitfall 4: Docker Compose dev vs prod Configuration

**What goes wrong:** Developers build a full 3-service docker-compose.yml but then run Python locally, causing port conflicts or confusion about which DB to connect to.
**Why it happens:** CONTEXT.md says "Local Python + Docker only for TimescaleDB during development."
**How to avoid:** Use `docker-compose.yml` with ONLY the `db` service for development. Create a separate `docker-compose.prod.yml` (or use profiles) for the full 3-service production stack.
**Warning signs:** Developer running `docker compose up` expecting to edit code and see changes -- containers don't have hot reload.

### Pitfall 5: LiteLLM Fallback Retry Loop

**What goes wrong:** LiteLLM retries each fallback model `num_retries` times, potentially causing long delays (3 retries x 3 fallbacks x 30s timeout = 4.5 minutes).
**Why it happens:** LiteLLM applies retry logic to each fallback model independently.
**How to avoid:** Keep fallback list short (1-2 models). Set a reasonable `timeout` (30s). Wrap the entire call in an outer timeout. When total time exceeds budget, return `LLM_UNAVAILABLE` immediately.
**Warning signs:** Pipeline stalling for minutes when OpenAI is down.

### Pitfall 6: SQLAlchemy Naming Convention for Constraints

**What goes wrong:** Alembic cannot autogenerate `DROP CONSTRAINT` statements without knowing constraint names.
**Why it happens:** PostgreSQL auto-generates constraint names, but Alembic needs deterministic names to produce reversible migrations.
**How to avoid:** Set naming conventions on the SQLAlchemy `MetaData` object:
```python
convention = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}
metadata = MetaData(naming_convention=convention)
Base = DeclarativeBase(metadata=metadata)
```
**Warning signs:** Alembic downgrade fails with "constraint name not found."

## Code Examples

### Docker Compose (Development -- TimescaleDB only)

```yaml
# docker-compose.yml (dev)
services:
  db:
    image: timescale/timescaledb:2.18.0-pg16
    ports:
      - "5432:5432"
    environment:
      POSTGRES_DB: trade_agent
      POSTGRES_USER: trade
      POSTGRES_PASSWORD: trade_dev
    volumes:
      - pgdata:/var/lib/postgresql/data
    shm_size: "64mb"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U trade -d trade_agent"]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 10s

volumes:
  pgdata:
```

### Docker Compose (Production -- full stack)

```yaml
# docker-compose.prod.yml
services:
  db:
    image: timescale/timescaledb:2.18.0-pg16
    deploy:
      resources:
        limits:
          memory: 256M
          cpus: "0.5"
        reservations:
          memory: 128M
    volumes:
      - pgdata:/var/lib/postgresql/data
    environment:
      POSTGRES_DB: trade_agent
      POSTGRES_USER: trade
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    shm_size: "64mb"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U trade -d trade_agent"]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 10s

  bot:
    build: .
    command: python -m src.bot.main
    deploy:
      resources:
        limits:
          memory: 192M
          cpus: "0.25"
    depends_on:
      db:
        condition: service_healthy
    env_file: .env
    restart: unless-stopped
    healthcheck:
      test: ["CMD-SHELL", "python -c 'import httpx; httpx.get(\"http://localhost:8000/health\")'"]
      interval: 30s
      timeout: 10s
      retries: 3

  pipeline:
    build: .
    command: python -m src.pipeline.main
    deploy:
      resources:
        limits:
          memory: 1280M
          cpus: "1.5"
    depends_on:
      db:
        condition: service_healthy
    env_file: .env
    profiles: ["pipeline"]

volumes:
  pgdata:
```

### Alembic Async env.py

```python
# src/db/migrations/env.py
import asyncio
from logging.config import fileConfig
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config
from alembic import context

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

from src.db.models import Base
target_metadata = Base.metadata

def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()

def do_run_migrations(connection):
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()

async def run_async_migrations():
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()

def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

### Seed Data for Assets Table

```python
# Recommended seed assets (BBCA.JK + BTC/USDT + ETH/USDT from CONTEXT.md, plus a few more)
SEED_ASSETS = [
    # IDX stocks
    {"symbol": "BBCA", "name": "Bank Central Asia", "asset_type": "stock", "exchange": "IDX", "yfinance_symbol": "BBCA.JK"},
    {"symbol": "BBRI", "name": "Bank Rakyat Indonesia", "asset_type": "stock", "exchange": "IDX", "yfinance_symbol": "BBRI.JK"},
    {"symbol": "TLKM", "name": "Telkom Indonesia", "asset_type": "stock", "exchange": "IDX", "yfinance_symbol": "TLKM.JK"},
    # Crypto
    {"symbol": "BTC", "name": "Bitcoin", "asset_type": "crypto", "exchange": "binance", "ccxt_symbol": "BTC/USDT"},
    {"symbol": "ETH", "name": "Ethereum", "asset_type": "crypto", "exchange": "binance", "ccxt_symbol": "ETH/USDT"},
    {"symbol": "SOL", "name": "Solana", "asset_type": "crypto", "exchange": "binance", "ccxt_symbol": "SOL/USDT"},
]
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| APScheduler 4.x for cron | System cron (pre-Phase 1 decision) | Project planning | APScheduler 4 still alpha; system cron more reliable |
| pandas-ta (original) | pandas-ta-classic v0.4.47 | Project planning | Original maintainer warned of archival; fork is drop-in compatible |
| requirements.txt | uv + pyproject.toml + uv.lock | uv 0.7.0 | Faster, deterministic, replaces pip + pip-tools |
| Pydantic v1 settings | pydantic-settings 2.x (separate package) | 2023 | Settings split into own package in Pydantic v2 |
| SQLAlchemy 1.x async | SQLAlchemy 2.0 native async | 2023 | Mapped annotations, async session, better typing |

**Deprecated/outdated:**
- `requirements.txt` -- project uses uv, do NOT create this file
- APScheduler -- replaced by system cron per project decision
- `python-dotenv` alone -- pydantic-settings includes .env loading

## Open Questions

1. **TimescaleDB extension in Alembic**
   - What we know: Phase 1 does not create hypertables (that is Phase 2 with price_history)
   - What's unclear: Should the initial migration include `CREATE EXTENSION IF NOT EXISTS timescaledb`?
   - Recommendation: Yes, include it in the first migration so the extension is ready when Phase 2 needs it

2. **Bot health check endpoint in Phase 1**
   - What we know: Success criteria #1 requires bot to pass health check
   - What's unclear: How minimal can the bot be? Just a FastAPI `/health` endpoint?
   - Recommendation: Stub bot with FastAPI + a single `/health` route returning `{"status": "ok"}`. No Telegram commands yet.

3. **Pipeline entry point behavior**
   - What we know: Pipeline is triggered by cron, runs stages sequentially, exits when done
   - What's unclear: Should it accept CLI arguments for running a single stage? For re-running failed assets?
   - Recommendation: Accept optional `--stage` and `--rerun-failed` flags from the start for debugging

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.13 | Runtime | Yes | 3.13.2 | -- |
| uv | Package management | Yes | 0.7.0 | -- |
| Docker | TimescaleDB container | Yes | 28.5.1 | -- |
| Docker Compose | Service orchestration | Yes | v2.40.3 | -- |
| ruff | Linting (via uv tool) | No (not global) | -- | `uv tool install ruff` or `uv run ruff` |
| mypy | Type checking (via uv tool) | No (not global) | -- | `uv tool install mypy` or `uv run mypy` |
| pytest | Testing (via uv) | No (not global) | -- | `uv run pytest` (installed as dev dep) |
| PostgreSQL client | psql for debugging | Not checked | -- | Docker exec into db container |

**Missing dependencies with no fallback:** None -- all tools can be installed via uv.

**Missing dependencies with fallback:**
- ruff, mypy, pytest: Not globally installed, but will be project dev dependencies accessed via `uv run`.

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2 + pytest-asyncio 1.3.0 |
| Config file | None -- Wave 0 must create `pyproject.toml [tool.pytest.ini_options]` |
| Quick run command | `uv run pytest tests/ -x -q` |
| Full suite command | `uv run pytest tests/ -v --tb=short` |

### Phase Requirements to Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| DATA-04 | Pipeline stages are idempotent and restartable | integration | `uv run pytest tests/test_pipeline/test_runner.py::test_restart_from_checkpoint -x` | Wave 0 |
| DATA-04 | Killed pipeline resumes from last successful stage checkpoint | integration | `uv run pytest tests/test_pipeline/test_runner.py::test_resume_after_kill -x` | Wave 0 |
| DATA-05 | pipeline_runs table tracks execution state correctly | unit | `uv run pytest tests/test_db/test_models.py::test_pipeline_runs_state_tracking -x` | Wave 0 |
| DATA-05 | pipeline_asset_runs tracks per-asset progress | unit | `uv run pytest tests/test_db/test_models.py::test_pipeline_asset_runs -x` | Wave 0 |
| DATA-06 | Critical source failure skips asset, important degrades, supplementary continues | unit | `uv run pytest tests/test_pipeline/test_tiers.py::test_tier_failure_handling -x` | Wave 0 |
| SC-1 | docker compose up starts 3 services with health checks | smoke | `docker compose -f docker-compose.prod.yml up -d && docker compose -f docker-compose.prod.yml ps` | Manual |
| SC-3 | LLM wrapper returns LLM_UNAVAILABLE when API unreachable | unit | `uv run pytest tests/test_llm/test_client.py::test_fallback_returns_unavailable -x` | Wave 0 |
| SC-5 | daily_decisions has decision_price + evaluation_price with timestamps | unit | `uv run pytest tests/test_db/test_models.py::test_decision_no_lookahead_bias -x` | Wave 0 |

### Sampling Rate

- **Per task commit:** `uv run pytest tests/ -x -q`
- **Per wave merge:** `uv run pytest tests/ -v --tb=short`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `pyproject.toml` `[tool.pytest.ini_options]` -- configure asyncio_mode = "auto"
- [ ] `tests/conftest.py` -- shared fixtures (async db session, test settings, mock LLM)
- [ ] `tests/test_pipeline/test_runner.py` -- covers DATA-04
- [ ] `tests/test_pipeline/test_tiers.py` -- covers DATA-06
- [ ] `tests/test_db/test_models.py` -- covers DATA-05, SC-5
- [ ] `tests/test_llm/test_client.py` -- covers SC-3
- [ ] `tests/test_config.py` -- covers settings loading
- [ ] Dev dependencies: `uv add --dev pytest pytest-asyncio`

## Sources

### Primary (HIGH confidence)
- ARCHITECTURE.md (local) -- full system architecture, database schema, project structure, Docker Compose config, error handling strategy, LLM integration design
- CONTEXT.md (local) -- locked decisions from user discussion session
- PROJECT.md (local) -- key decisions, constraints, core value
- STATE.md (local) -- accumulated pre-Phase 1 decisions

### Secondary (MEDIUM confidence)
- [LiteLLM Reliability Docs](https://docs.litellm.ai/docs/completion/reliable_completions) -- retry + fallback configuration
- [Pydantic Settings Docs](https://docs.pydantic.dev/latest/concepts/pydantic_settings/) -- BaseSettings configuration
- [structlog 25.5.0 Docs](https://www.structlog.org/en/stable/configuration.html) -- configuration and bound loggers
- [TimescaleDB Docker](https://hub.docker.com/r/timescale/timescaledb) -- image tags, version 2.18.0-pg16
- [Alembic Cookbook](https://alembic.sqlalchemy.org/en/latest/cookbook.html) -- async migration setup
- PyPI verified versions for all packages (2026-03-23)

### Tertiary (LOW confidence)
- None

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- all packages verified on PyPI with current versions; mature, well-documented libraries
- Architecture: HIGH -- follows ARCHITECTURE.md closely with documented extensions for per-asset checkpointing
- Pitfalls: HIGH -- identified from schema analysis (ARCHITECTURE.md vs CONTEXT.md gap) and known library behaviors

**Research date:** 2026-03-23
**Valid until:** 2026-04-23 (30 days -- stable domain, no fast-moving dependencies)
