# Technology Stack

**Analysis Date:** 2026-03-24

## Languages

**Primary:**
- Python 3.13 - All application code in `src/`

## Runtime

**Environment:**
- CPython 3.13 (pinned via `.python-version`)

**Package Manager:**
- uv (latest, installed in Docker via `ghcr.io/astral-sh/uv`)
- Lockfile: `uv.lock` — present and committed

## Frameworks

**Web / Bot API:**
- FastAPI 0.135.1+ — Bot service HTTP API (`src/bot/main.py`), serves on port 8000
- uvicorn[standard] 0.42.0+ — ASGI server for FastAPI

**Database ORM:**
- SQLAlchemy[asyncio] 2.0.48+ — Async ORM and query layer (`src/db/`)
- Alembic 1.18.4+ — Database migrations (`src/db/migrations/`)

**Data / ML:**
- pandas 3.0.1+ — DataFrame processing for OHLCV data in `src/data/idx_stocks.py`

**Configuration:**
- pydantic-settings 2.13.1+ — Env-var config via `src/config.py`

**Testing:**
- pytest 9.0.2+ — Test runner, config in `pyproject.toml`
- pytest-asyncio 1.3.0+ — Async test support (`asyncio_mode = "auto"`)
- aiosqlite 0.22.1+ — In-memory SQLite for tests (dev only)

**Build/Dev:**
- ruff 0.15.7+ — Linting and formatting (`/.ruff.toml`)
- mypy 1.19.1+ — Static type checking, strict mode (`pyproject.toml`)
- pre-commit 4.5.1+ — Git hooks (`/.pre-commit-config.yaml`)

## Key Dependencies

**Critical:**
- litellm 1.82.6+ — Unified LLM gateway (`src/llm/client.py`); routes to OpenAI and Google Gemini
- ccxt 4.5.44+ — Crypto exchange data via Binance (`src/data/crypto.py`)
- yfinance 1.2.0+ — IDX stock OHLCV data via Yahoo Finance (`src/data/idx_stocks.py`)
- asyncpg 0.31.0+ — Async PostgreSQL driver (used by SQLAlchemy async engine)
- httpx 0.28.1+ — Async HTTP client for CoinGecko fallback (`src/data/crypto.py`)
- tenacity 9.1.4+ — Retry logic with exponential backoff (`src/data/idx_stocks.py`, `src/data/crypto.py`)
- structlog 25.5.0+ — Structured JSON logging (`src/logging.py`)

**Infrastructure:**
- TimescaleDB 2.18.0-pg16 — Time-series extension on PostgreSQL 16 (Docker)

## Configuration

**Environment:**
- Loaded from `.env` file via pydantic-settings (`src/config.py`)
- Settings class: `src/config.py` → `Settings(BaseSettings)`
- Key configs: `DATABASE_URL`, `OPENAI_API_KEY`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, `LLM_PRIMARY_MODEL`, `LLM_FALLBACK_MODEL`
- Secrets use `pydantic.SecretStr` type: `openai_api_key`, `telegram_bot_token`

**Build:**
- `pyproject.toml` — Project metadata, dependencies, pytest config, mypy config
- `.ruff.toml` — Linting rules (line length 120, py313 target, rulesets E/F/I/W/UP/B/SIM)
- `alembic.ini` — Migration config, migrations in `src/db/migrations/`
- `Dockerfile` — python:3.13-slim base, uv for deps
- `docker-compose.yml` — Dev: TimescaleDB only
- `docker-compose.prod.yml` — Prod: TimescaleDB + bot service + pipeline service (profiles)

## Platform Requirements

**Development:**
- Python 3.13
- uv package manager
- Docker + Docker Compose (for TimescaleDB)
- `.env` file with database and API credentials

**Production:**
- Docker Compose with three services: `db`, `bot`, `pipeline`
- Bot service: FastAPI on port 8000, memory limit 192M
- Pipeline service: run via `profiles: ["pipeline"]`, memory limit 1280M, CPU limit 1.5

---

*Stack analysis: 2026-03-24*
