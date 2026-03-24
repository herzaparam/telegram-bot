# External Integrations

**Analysis Date:** 2026-03-24

## APIs & External Services

**Market Data — Stocks:**
- Yahoo Finance (via yfinance) — IDX stock OHLCV data (`.JK` tickers: BBCA, BBRI, TLKM)
  - SDK/Client: `yfinance` (synchronous, wrapped in `asyncio.run_in_executor`)
  - Auth: None (public API)
  - Implementation: `src/data/idx_stocks.py` → `IDXStockFetcher`
  - Retry: tenacity, 3 attempts, exponential backoff

**Market Data — Crypto (Primary):**
- Binance via ccxt — Crypto OHLCV data (BTC/USDT, ETH/USDT, SOL/USDT), daily and hourly
  - SDK/Client: `ccxt` async (`ccxt.binance`)
  - Auth: None required for public market data (rate limiting enabled)
  - Implementation: `src/data/crypto.py` → `CryptoFetcher._fetch_ccxt()`
  - Retry: tenacity, 3 attempts, on `ccxt.NetworkError`, `ccxt.ExchangeNotAvailable`, `TimeoutError`

**Market Data — Crypto (Fallback):**
- CoinGecko Free API — OHLC fallback when ccxt/Binance fails
  - SDK/Client: `httpx.AsyncClient` (direct HTTP)
  - Auth: None (public free tier)
  - Endpoint: `https://api.coingecko.com/api/v3/coins/{id}/ohlc`
  - Supported symbols: BTC/USDT → `bitcoin`, ETH/USDT → `ethereum`, SOL/USDT → `solana`
  - Note: Volume is always 0 — CoinGecko OHLC endpoint does not provide it
  - Implementation: `src/data/crypto.py` → `CryptoFetcher._fetch_coingecko()`

**LLM — Primary:**
- OpenAI GPT-4o-mini — Trading analysis and decisions
  - SDK/Client: `litellm` (`litellm.acompletion`)
  - Auth: `OPENAI_API_KEY` env var (stored as `SecretStr`)
  - Model config: `LLM_PRIMARY_MODEL` (default: `gpt-4o-mini`)
  - Implementation: `src/llm/client.py` → `llm_completion()`

**LLM — Fallback:**
- Google Gemini 2.0 Flash — Fallback when OpenAI fails
  - SDK/Client: `litellm` (unified gateway, `gemini/gemini-2.0-flash`)
  - Auth: Google API key via litellm env convention
  - Model config: `LLM_FALLBACK_MODEL` (default: `gemini/gemini-2.0-flash`)
  - Behavior: litellm handles fallback automatically; `llm_completion()` never raises

**Notifications (Planned):**
- Telegram Bot API — Alert delivery (referenced in `src/data/alerts.py` as "Phase 5")
  - Auth: `TELEGRAM_BOT_TOKEN` env var (stored as `SecretStr`), `TELEGRAM_CHAT_ID`
  - Current state: Config present in `src/config.py`, `AlertCollector` in `src/data/alerts.py` collects alerts but does not yet send them to Telegram

## Data Storage

**Databases:**
- TimescaleDB 2.18.0 on PostgreSQL 16
  - Connection (async): `DATABASE_URL` env var (default: `postgresql+asyncpg://trade:trade_dev@localhost:5432/trade_agent`)
  - Connection (sync/Alembic): `DATABASE_URL_SYNC` env var (default: `postgresql://trade:trade_dev@localhost:5432/trade_agent`)
  - Client: SQLAlchemy async (`src/db/database.py`), asyncpg driver
  - Session factory: `async_session_factory` in `src/db/database.py`
  - Pool: `pool_size=5`, `max_overflow=10`
  - Tables: `assets`, `pipeline_runs`, `pipeline_asset_runs`, `daily_decisions`, `price_history` (hypertable), `price_history_hourly` (hypertable, 7-day retention), `backoff_state`
  - Hypertable compression: daily price data compressed after 30 days (segment by `asset_id`)
  - Dev testing: `aiosqlite` in-memory SQLite (dev dependency)

**File Storage:**
- Local filesystem only — no object storage integration

**Caching:**
- None — no Redis or in-memory cache layer

## Authentication & Identity

**Auth Provider:**
- None — no user authentication or identity provider
- The bot service (`src/bot/main.py`) exposes only an unauthenticated `/health` endpoint

## Monitoring & Observability

**Error Tracking:**
- None — no Sentry or equivalent

**Logs:**
- structlog with JSON renderer in production, console renderer in dev
- Configuration: `src/logging.py` → `setup_logging()`
- Format controlled by `LOG_FORMAT` env var (`json` or `console`)
- Level controlled by `LOG_LEVEL` env var

## CI/CD & Deployment

**Hosting:**
- Docker Compose (production via `docker-compose.prod.yml`)
- Three services: `db` (TimescaleDB), `bot` (FastAPI on :8000), `pipeline` (batch job, profile-gated)

**CI Pipeline:**
- pre-commit hooks only (ruff lint + ruff format)
- No GitHub Actions or other CI service detected

## Environment Configuration

**Required env vars:**
- `DATABASE_URL` — async PostgreSQL connection string
- `DATABASE_URL_SYNC` — sync PostgreSQL connection string (Alembic)
- `DB_PASSWORD` — database password (production docker-compose)
- `OPENAI_API_KEY` — OpenAI API key for LLM
- `TELEGRAM_BOT_TOKEN` — Telegram bot token (future use)
- `TELEGRAM_CHAT_ID` — Telegram chat ID (future use)

**Optional env vars (with defaults):**
- `LLM_PRIMARY_MODEL` — default `gpt-4o-mini`
- `LLM_FALLBACK_MODEL` — default `gemini/gemini-2.0-flash`
- `LLM_MAX_RETRIES` — default `3`
- `LLM_TIMEOUT` — default `30` seconds
- `LOG_LEVEL` — default `INFO`
- `LOG_FORMAT` — default `json`
- `TIMEOUT_FETCH`, `TIMEOUT_ANALYZE`, `TIMEOUT_LLM` — stage timeouts in seconds

**Secrets location:**
- `.env` file at project root (gitignored), loaded by pydantic-settings
- Secrets typed as `pydantic.SecretStr` in `src/config.py`

## Webhooks & Callbacks

**Incoming:**
- None — no webhook endpoints implemented

**Outgoing:**
- Telegram Bot API (planned, Phase 5) — alert push notifications

---

*Integration audit: 2026-03-24*
