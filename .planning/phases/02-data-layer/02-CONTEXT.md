# Phase 2: Data Layer - Context

**Gathered:** 2026-03-23
**Status:** Ready for planning

<domain>
## Phase Boundary

IDX stock and crypto prices fetched, validated, and stored in TimescaleDB hypertables with compression — the data foundation every engine depends on. Covers: price_history hypertable creation, IDX fetcher (yfinance), crypto fetcher (ccxt + CoinGecko fallback), data validation, staleness detection, compression policy, idempotent upserts, and backfill CLI. Does NOT include: engine analysis, signal generation, or Telegram delivery.

</domain>

<decisions>
## Implementation Decisions

### Historical backfill
- 2-year backfill on first run (~500 trading days for IDX, ~730 for crypto)
- Auto-backfill when pipeline detects empty price_history, PLUS a separate CLI command (`python -m src.data.backfill`)
- CLI supports `--from` and `--to` date range flags; defaults to 2 years if omitted
- Daily runs fetch only missing days (delta); once per week re-fetch the full recent month to catch corrections (split adjustments, volume revisions)
- Weekly refresh uses silent UPSERT — overwrite corrected values, no audit trail

### Candle timeframes
- Daily (1d) candles for all assets in `price_history` hypertable (primary storage)
- Separate `price_history_hourly` hypertable for crypto hourly candles, last 7 days rolling
- Hourly candles are crypto-only; IDX stores daily only

### Validation rules
- Reject any row where open, high, low, close, OR volume is null/NaN — strict, no partial OHLCV
- Skip bad rows but keep good ones from the same fetch — one bad day doesn't block the rest
- Validate that returned dates cover the requested range; log warnings for gaps
- Rejected rows logged via structlog with asset, date, and reason

### Staleness detection
- IDX stocks: stale if no data for the last trading day (accounts for weekends/holidays)
- Crypto: stale if no data in last 24 hours (24/7 market)
- Staleness checked after ingest stage completes

### Fetcher resilience
- IDX (yfinance): retry 3x with adaptive backoff, then alert. No fallback source
- Crypto (ccxt/Binance): retry 3x, then fall back to CoinGecko for daily OHLCV prices
- Adaptive backoff state persisted in DB across pipeline runs (if yfinance was flaky yesterday, start slower today)
- Price rows tagged with `source` column ('yfinance', 'ccxt', 'coingecko') so engines know data provenance

### Concurrency
- All assets (IDX + crypto) fetched concurrently via asyncio.gather with shared Semaphore(5)
- Adaptive backoff for yfinance rate limiting (start fast, slow down on errors)
- IDX symbol resolution uses `yfinance_symbol` from assets table (already has .JK suffix)

### Alerting
- Target: Telegram + structlog for DATA_STALE and fetch failures
- Phase 2 implementation: structlog only (defer Telegram sending to Phase 5)
- Build alert structure so Telegram delivery can be plugged in later
- Batched summary after ingest stage completes (e.g., "3 assets stale: BBCA.JK, TLKM.JK, SOL")
- Only failures/staleness reported; successful fetches logged at INFO level only

### Idempotency
- UPSERT on (asset_id, time) — re-running ingest for same date produces no duplicates
- Same mechanism handles weekly correction refresh

### Claude's Discretion
- Exact adaptive backoff algorithm (exponential, jitter, decay rate)
- Semaphore size tuning (5 is the starting point)
- Compression policy timing details (30-day threshold per ARCHITECTURE.md)
- Hourly candle cleanup strategy (rolling 7-day window maintenance)
- Backoff state DB schema (could be a simple key-value or dedicated table)
- Exact validation error messages and log format

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Architecture & Schema
- `plan/ARCHITECTURE.md` — Full system architecture, price_history hypertable schema, compression policy, BaseFetcher pattern, data source table, concurrency strategy (Semaphore(5))
- `plan/ARCHITECTURE.md` §Database Schema — price_history table definition with OHLCV columns, create_hypertable call, compression settings
- `plan/ARCHITECTURE.md` §Data Sources — yfinance for IDX (.JK), ccxt for crypto, CoinGecko strategy (metadata + fallback)

### Data Sources
- `plan/FREE_TRADING_APIS_2025_2026.md` — Available free trading APIs, rate limits, and access methods

### Project Decisions
- `.planning/PROJECT.md` §Key Decisions — asyncpg for hot paths, SQLAlchemy for relational, TimescaleDB hypertables
- `.planning/STATE.md` §Accumulated Context — yfinance IDX delta-fetch reliability concern flagged as research blocker

### Phase 1 Foundation
- `.planning/phases/01-foundation/01-CONTEXT.md` — Dev workflow, schema scope, checkpoint granularity, logging decisions that Phase 2 must follow

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/db/models.py` — Asset model with `yfinance_symbol` and `ccxt_symbol` fields ready for fetchers; Base with naming conventions for Alembic
- `src/db/database.py` — async engine and session factory; `init_db()` for connectivity check
- `src/pipeline/runner.py` — PipelineRunner with per-asset checkpointing; `StageFunc` type alias for stage handlers
- `src/pipeline/tiers.py` — Data source tier classification (critical/important/supplementary) and SourceCriticalError
- `src/config.py` — Settings with database URLs, timeouts (fetch: 60s, analyze: 120s), log level
- `src/logging.py` — structlog setup

### Established Patterns
- SQLAlchemy async ORM with asyncpg driver for all DB operations currently
- Per-asset-per-stage checkpointing via PipelineAssetRun records
- pydantic-settings for configuration; .env file support
- structlog for JSON logging with component binding

### Integration Points
- Ingest stage plugs into PipelineRunner as a StageFunc
- price_history and price_history_hourly tables need Alembic migration (extending 001_initial_schema)
- Asset seed data in models.py provides test assets (BBCA.JK, BBRI.JK, TLKM.JK, BTC, ETH, SOL)
- `src/data/` directory specified in ARCHITECTURE.md for fetcher modules (base.py, idx_stocks.py, crypto.py)

</code_context>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches. Follow ARCHITECTURE.md patterns (BaseFetcher, asyncpg for hot paths).

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 02-data-layer*
*Context gathered: 2026-03-23*
