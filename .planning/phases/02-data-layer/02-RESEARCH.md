# Phase 2: Data Layer - Research

**Researched:** 2026-03-23
**Domain:** TimescaleDB hypertables, market data fetching (yfinance, ccxt, CoinGecko), async Python data pipelines
**Confidence:** HIGH

## Summary

Phase 2 builds the data foundation: two TimescaleDB hypertables (`price_history` for daily OHLCV, `price_history_hourly` for crypto hourly), fetchers for IDX stocks (yfinance) and crypto (ccxt/Binance with CoinGecko fallback), validation, staleness detection, compression policies, and idempotent upserts. The existing Phase 1 infrastructure (PipelineRunner, Asset model with `yfinance_symbol`/`ccxt_symbol`, Alembic migrations, structlog) provides solid integration points.

The main technical risks are: (1) yfinance is an unofficial Yahoo Finance scraper that can break without notice -- IDX `.JK` tickers need early validation, (2) TimescaleDB hypertable creation requires raw SQL in Alembic migrations since SQLAlchemy has no native hypertable support, and (3) asyncpg raw SQL is recommended for bulk OHLCV upserts (hot path) while SQLAlchemy handles relational queries.

**Primary recommendation:** Use asyncpg raw `INSERT ... ON CONFLICT` for OHLCV upserts (hot path performance), yfinance `download()` with date-range parameters for IDX delta-fetch, ccxt async `fetch_ohlcv` for crypto, and Alembic `op.execute()` for hypertable/compression DDL.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- 2-year backfill on first run (~500 trading days IDX, ~730 crypto); auto-backfill on empty + CLI `python -m src.data.backfill` with `--from`/`--to` flags
- Daily runs fetch only missing days (delta); weekly re-fetch of full recent month for corrections via silent UPSERT
- Daily (1d) candles in `price_history` hypertable; separate `price_history_hourly` for crypto hourly (7-day rolling)
- Strict validation: reject rows where any OHLCV field is null/NaN; skip bad rows, keep good ones; validate date coverage
- IDX staleness = no data for last trading day; crypto staleness = no data in 24h; checked after ingest
- IDX fetcher: yfinance, retry 3x adaptive backoff, no fallback source
- Crypto fetcher: ccxt/Binance, retry 3x, CoinGecko daily OHLCV fallback
- Adaptive backoff state persisted in DB; `source` column on price rows
- All assets fetched concurrently via asyncio.gather with Semaphore(5)
- Alerting: structlog only in Phase 2 (Telegram deferred to Phase 5); build alert structure for later plug-in; batched summary after ingest
- UPSERT on (asset_id, time) for idempotency
- Rejected rows logged via structlog with asset, date, reason

### Claude's Discretion
- Exact adaptive backoff algorithm (exponential, jitter, decay rate)
- Semaphore size tuning (5 is starting point)
- Compression policy timing details (30-day threshold per ARCHITECTURE.md)
- Hourly candle cleanup strategy (rolling 7-day window maintenance)
- Backoff state DB schema (key-value or dedicated table)
- Exact validation error messages and log format

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| DATA-01 | System stores daily OHLCV price history in TimescaleDB hypertables with auto-compression after 30 days | Hypertable creation via Alembic `op.execute()`, compression policy SQL, asyncpg upsert pattern |
| DATA-02 | System fetches IDX stock prices via yfinance (.JK suffix) with aggressive caching | yfinance `download()` with start/end date range, delta-fetch pattern, `.JK` suffix confirmed working |
| DATA-03 | System fetches crypto OHLCV via ccxt (Binance) with CoinGecko metadata backup | ccxt async `fetch_ohlcv` with pagination, CoinGecko `/coins/{id}/ohlc` fallback, source tagging |
</phase_requirements>

## Project Constraints (from CLAUDE.md)

No CLAUDE.md file exists in the project root. Phase follows conventions established in Phase 1:
- Python 3.13+, uv package manager
- pytest with pytest-asyncio (asyncio_mode="auto")
- ruff + mypy (strict mode) for code quality
- structlog for JSON logging
- SQLAlchemy async ORM with asyncpg driver
- pydantic-settings for configuration
- Alembic for all database migrations

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| yfinance | >=1.2.0 | IDX stock OHLCV via Yahoo Finance | Only free source for IDX `.JK` stocks; widely used despite unofficial status |
| ccxt | >=4.4 | Crypto OHLCV from Binance | Unified async API for 100+ exchanges; exchange-portable |
| asyncpg | >=0.31.0 | Raw SQL upserts for OHLCV hot path | Already in project; bulk INSERT ON CONFLICT is 10-50x faster than ORM |
| SQLAlchemy | >=2.0.48 | ORM for relational queries (assets, backoff state) | Already in project; type-safe relational operations |
| pandas | >=2.2 | DataFrame for yfinance data processing and validation | yfinance returns pandas DataFrames natively |
| httpx | >=0.28.1 | CoinGecko API fallback HTTP client | Already in project; async with connection pooling |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| structlog | >=25.5.0 | Already in project | All logging: validation failures, staleness alerts, fetch summaries |
| tenacity | >=9.1.4 | Already in project | Retry logic for fetchers (3x with backoff) |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| yfinance | yahooquery | Similar unofficial approach; yfinance has larger community |
| Raw asyncpg upserts | SQLAlchemy bulk insert | 10-50x slower for OHLCV writes; acceptable only for small datasets |
| CoinGecko REST | ccxt with secondary exchange | CoinGecko provides broader metadata; 10k calls/mo free tier is sufficient for daily fallback |

**New dependencies to add:**
```bash
uv add yfinance ccxt pandas
```

**Note:** httpx, asyncpg, tenacity, structlog, SQLAlchemy already in pyproject.toml.

## Architecture Patterns

### Recommended Project Structure
```
src/
├── data/
│   ├── __init__.py
│   ├── base.py              # BaseFetcher ABC + common retry/validation
│   ├── idx_stocks.py        # IDXStockFetcher (yfinance)
│   ├── crypto.py            # CryptoFetcher (ccxt + CoinGecko fallback)
│   ├── validation.py        # OHLCV validation rules, row rejection logic
│   ├── staleness.py         # Staleness detection per asset type
│   ├── alerts.py            # Alert structure (structlog now, Telegram later)
│   ├── backfill.py          # CLI entry point: python -m src.data.backfill
│   └── ingest.py            # Ingest stage function (plugs into PipelineRunner)
├── db/
│   ├── models.py            # Add PriceHistory, PriceHistoryHourly, BackoffState models
│   ├── price_repo.py        # asyncpg raw SQL: upsert_prices, get_latest_date, etc.
│   └── migrations/versions/
│       └── 002_price_history_hypertables.py
```

### Pattern 1: BaseFetcher with Retry
**What:** Abstract base class with tenacity retry, validation, and source tagging
**When to use:** Every data fetcher inherits this
**Example:**
```python
# Source: ARCHITECTURE.md BaseFetcher + tenacity (already in deps)
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date, datetime

import structlog
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

logger = structlog.get_logger(__name__)

@dataclass
class OHLCVRow:
    time: datetime
    asset_id: int
    open: float
    high: float
    low: float
    close: float
    volume: float
    source: str  # 'yfinance', 'ccxt', 'coingecko'

class BaseFetcher(ABC):
    @abstractmethod
    async def fetch(
        self, asset_id: int, symbol: str, start: date, end: date
    ) -> list[OHLCVRow]:
        """Fetch OHLCV data for date range. Returns validated rows."""
        ...

    def validate_row(self, row: OHLCVRow) -> bool:
        """Strict validation: all OHLCV fields must be non-null, non-NaN."""
        import math
        for field in (row.open, row.high, row.low, row.close, row.volume):
            if field is None or math.isnan(field):
                return False
        return True
```

### Pattern 2: asyncpg Raw Upsert for Hot Path
**What:** Direct asyncpg for bulk OHLCV inserts, bypassing SQLAlchemy ORM overhead
**When to use:** All price_history writes (the "hot path" per ARCHITECTURE.md)
**Example:**
```python
# Source: asyncpg docs + TimescaleDB upsert docs
async def upsert_prices(conn, rows: list[OHLCVRow]) -> int:
    """Bulk upsert OHLCV rows. Returns count of affected rows."""
    if not rows:
        return 0
    result = await conn.executemany(
        """
        INSERT INTO price_history (time, asset_id, open, high, low, close, volume, source)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
        ON CONFLICT (asset_id, time)
        DO UPDATE SET open = EXCLUDED.open, high = EXCLUDED.high,
                      low = EXCLUDED.low, close = EXCLUDED.close,
                      volume = EXCLUDED.volume, source = EXCLUDED.source
        WHERE price_history.open != EXCLUDED.open
           OR price_history.high != EXCLUDED.high
           OR price_history.low != EXCLUDED.low
           OR price_history.close != EXCLUDED.close
           OR price_history.volume != EXCLUDED.volume
        """,
        [(r.time, r.asset_id, r.open, r.high, r.low, r.close, r.volume, r.source)
         for r in rows]
    )
    return len(rows)
```

### Pattern 3: Ingest Stage Integration with PipelineRunner
**What:** The ingest stage function that plugs into PipelineRunner's StageFunc signature
**When to use:** Pipeline daily run and backfill
**Example:**
```python
# Signature must match StageFunc = Callable[[AsyncSession, Asset], Awaitable[None]]
async def ingest_stage(session: AsyncSession, asset: Asset) -> None:
    """Fetch and store OHLCV data for a single asset."""
    # 1. Determine date range (delta fetch: last stored date to today)
    # 2. Select fetcher based on asset.asset_type
    # 3. Fetch, validate, upsert
    # 4. Check staleness
    # 5. Log results
    ...
```

### Pattern 4: Hypertable Migration via Alembic op.execute()
**What:** TimescaleDB DDL requires raw SQL since SQLAlchemy has no hypertable support
**When to use:** Creating price_history and price_history_hourly tables
**Example:**
```python
# In Alembic migration 002_price_history_hypertables.py
def upgrade() -> None:
    # Create table with standard SQLAlchemy, then convert to hypertable
    op.create_table("price_history", ...)
    op.execute("SELECT create_hypertable('price_history', 'time')")
    op.execute("""
        ALTER TABLE price_history SET (
            timescaledb.compress,
            timescaledb.compress_segmentby = 'asset_id',
            timescaledb.compress_orderby = 'time DESC'
        )
    """)
    op.execute("SELECT add_compression_policy('price_history', INTERVAL '30 days')")
```

### Anti-Patterns to Avoid
- **Using SQLAlchemy ORM for bulk OHLCV writes:** ORM overhead (object creation, identity map, flush) adds 10-50x latency for bulk inserts. Use asyncpg raw SQL.
- **Fetching all history on every run:** Only fetch missing days (delta). Use `SELECT MAX(time) FROM price_history WHERE asset_id = $1` to determine start date.
- **Ignoring yfinance's end-date exclusion:** yfinance `download(end=...)` is exclusive -- the end date is NOT included. Always add 1 day to get today's data.
- **Storing NaN values:** yfinance can return NaN for volume or adjusted close. Validate EVERY field before insert.
- **Not closing ccxt exchange objects:** Async ccxt exchange connections MUST be closed with `await exchange.close()` to prevent resource leaks.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Retry with backoff | Custom retry loop | tenacity (already in deps) | Handles jitter, exponential backoff, exception filtering, retry logging |
| OHLCV data fetching | Raw HTTP to Yahoo Finance | yfinance library | Handles cookies, session management, Yahoo API changes |
| Crypto exchange API | Direct Binance REST calls | ccxt | Unified API, handles auth, rate limiting, pagination |
| Hypertable compression | Manual CRON to compress chunks | TimescaleDB compression policy | `add_compression_policy` automates chunk compression transparently |
| DataFrame validation | Manual row-by-row loops | pandas `.isna()`, `.dropna()` with logging | Vectorized operations are faster; log rejected rows individually |

**Key insight:** yfinance and ccxt abstract away fragile external API interactions. The real custom work is in: (1) delta-fetch logic, (2) validation/rejection, (3) staleness detection, and (4) the ingest stage orchestration.

## Common Pitfalls

### Pitfall 1: yfinance IDX Data Gaps
**What goes wrong:** yfinance returns empty DataFrames or stale data for `.JK` tickers, especially for small-cap or recently listed stocks
**Why it happens:** Yahoo Finance's IDX coverage is incomplete; data updates can lag 1-2 days; the library scrapes unofficial endpoints that change
**How to avoid:** Always check `df.empty` after download; validate that returned dates cover the requested range; log gaps as warnings; mark asset as stale if no data for last trading day
**Warning signs:** Empty DataFrame, dates not matching request range, all-zero volume

### Pitfall 2: yfinance End Date is Exclusive
**What goes wrong:** Requesting `end="2026-03-23"` does NOT include March 23 data
**Why it happens:** yfinance follows Python convention where end is exclusive
**How to avoid:** Always add `timedelta(days=1)` to the end date when you want to include today
**Warning signs:** Consistently missing the most recent day's data

### Pitfall 3: TimescaleDB Hypertable + Alembic Auto-generate Conflicts
**What goes wrong:** Alembic auto-generate tries to drop TimescaleDB-created indexes on hypertables
**Why it happens:** TimescaleDB creates internal indexes that Alembic doesn't know about; reflection picks them up as "extra"
**How to avoid:** Use `include_object` filter in Alembic env.py to exclude TimescaleDB internal objects; write hypertable migrations manually with `op.execute()`, not auto-generate
**Warning signs:** Alembic migration includes unexpected `DROP INDEX` statements

### Pitfall 4: Upserts on Compressed Chunks are Slow
**What goes wrong:** INSERT ON CONFLICT targeting data in compressed chunks causes decompression, which is very slow
**Why it happens:** TimescaleDB must decompress chunks to resolve conflicts on compressed data
**How to avoid:** Only upsert recent data (within 30-day uncompressed window); for historical backfill, load data BEFORE enabling compression policy; weekly correction refresh targets last 30 days only
**Warning signs:** Upserts taking seconds per row instead of milliseconds

### Pitfall 5: ccxt Rate Limiting
**What goes wrong:** Binance returns 429 errors or temporarily bans IP
**Why it happens:** Too many concurrent requests; Binance allows 1200 req/min but ccxt may batch
**How to avoid:** Use Semaphore(5) as decided; ccxt has built-in rate limiting (`enableRateLimit: True`); add explicit sleep between pagination calls for historical backfill
**Warning signs:** HTTP 429 responses, increasing error counts

### Pitfall 6: CoinGecko Free Tier Exhaustion
**What goes wrong:** CoinGecko returns 429 after ~10k calls/month (Demo tier) or 5-15 calls/min (public)
**Why it happens:** Free tier has strict limits; each asset OHLCV fetch counts as a call
**How to avoid:** Only use CoinGecko as fallback when ccxt fails; cache responses; register for Demo API key (30 calls/min, 10k/mo)
**Warning signs:** 429 responses from CoinGecko

### Pitfall 7: Timezone Confusion in OHLCV Data
**What goes wrong:** Daily candle timestamps from yfinance vs ccxt use different timezone conventions; duplicates or gaps appear
**Why it happens:** yfinance returns IDX data in exchange timezone (WIB/UTC+7); ccxt returns UTC timestamps; TimescaleDB stores TIMESTAMPTZ
**How to avoid:** Normalize ALL timestamps to UTC before storing; daily candles use midnight UTC as canonical timestamp; document timezone convention
**Warning signs:** Duplicate rows for same logical day, gaps where data exists

## Code Examples

### yfinance IDX Stock Fetch
```python
# Source: yfinance docs + IDX .JK convention
import yfinance as yf
from datetime import date, timedelta

async def fetch_idx_ohlcv(symbol: str, start: date, end: date) -> list[dict]:
    """Fetch IDX stock daily OHLCV via yfinance.

    Args:
        symbol: yfinance symbol with .JK suffix (e.g., "BBCA.JK")
        start: Start date (inclusive)
        end: End date (inclusive -- we add 1 day for yfinance exclusion)
    """
    # yfinance is synchronous -- run in executor
    df = yf.download(
        tickers=symbol,
        start=start.isoformat(),
        end=(end + timedelta(days=1)).isoformat(),
        interval="1d",
        progress=False,
        auto_adjust=True,  # Use adjusted prices
    )
    if df.empty:
        return []
    # df columns: Open, High, Low, Close, Volume
    # Index: DatetimeIndex (timezone-naive, exchange local time)
    rows = []
    for dt, row in df.iterrows():
        rows.append({
            "time": dt.to_pydatetime().replace(tzinfo=None),  # Normalize later
            "open": float(row["Open"]) if not pd.isna(row["Open"]) else None,
            "high": float(row["High"]) if not pd.isna(row["High"]) else None,
            "low": float(row["Low"]) if not pd.isna(row["Low"]) else None,
            "close": float(row["Close"]) if not pd.isna(row["Close"]) else None,
            "volume": float(row["Volume"]) if not pd.isna(row["Volume"]) else None,
        })
    return rows
```

### ccxt Async Crypto Fetch
```python
# Source: ccxt docs + Binance OHLCV example
import ccxt.async_support as ccxt

async def fetch_crypto_ohlcv(
    symbol: str, start_ms: int, timeframe: str = "1d", limit: int = 1000
) -> list[list]:
    """Fetch crypto OHLCV from Binance via ccxt.

    Args:
        symbol: ccxt symbol (e.g., "BTC/USDT")
        start_ms: Start timestamp in milliseconds
        timeframe: Candle interval ("1d" or "1h")
        limit: Max candles per request (Binance max: 1000)
    """
    exchange = ccxt.binance({"enableRateLimit": True})
    try:
        ohlcv = await exchange.fetch_ohlcv(
            symbol, timeframe, since=start_ms, limit=limit
        )
        # Returns: [[timestamp_ms, open, high, low, close, volume], ...]
        return ohlcv
    finally:
        await exchange.close()
```

### Alembic Migration for Hypertables
```python
# Source: TimescaleDB docs + Alembic op.execute pattern
def upgrade() -> None:
    # price_history (daily candles)
    op.create_table(
        "price_history",
        sa.Column("time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("asset_id", sa.Integer, sa.ForeignKey("assets.id"), nullable=False),
        sa.Column("open", sa.Float, nullable=False),
        sa.Column("high", sa.Float, nullable=False),
        sa.Column("low", sa.Float, nullable=False),
        sa.Column("close", sa.Float, nullable=False),
        sa.Column("volume", sa.Float, nullable=False),
        sa.Column("source", sa.String(20), nullable=False, server_default="unknown"),
        sa.UniqueConstraint("asset_id", "time", name="uq_price_history_asset_time"),
    )
    op.execute("SELECT create_hypertable('price_history', 'time')")
    op.execute("""
        ALTER TABLE price_history SET (
            timescaledb.compress,
            timescaledb.compress_segmentby = 'asset_id',
            timescaledb.compress_orderby = 'time DESC'
        )
    """)
    op.execute("SELECT add_compression_policy('price_history', INTERVAL '30 days')")

    # price_history_hourly (crypto hourly, 7-day rolling)
    op.create_table(
        "price_history_hourly",
        sa.Column("time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("asset_id", sa.Integer, sa.ForeignKey("assets.id"), nullable=False),
        sa.Column("open", sa.Float, nullable=False),
        sa.Column("high", sa.Float, nullable=False),
        sa.Column("low", sa.Float, nullable=False),
        sa.Column("close", sa.Float, nullable=False),
        sa.Column("volume", sa.Float, nullable=False),
        sa.Column("source", sa.String(20), nullable=False, server_default="ccxt"),
        sa.UniqueConstraint("asset_id", "time", name="uq_price_history_hourly_asset_time"),
    )
    op.execute("SELECT create_hypertable('price_history_hourly', 'time')")
    # Retention policy: auto-delete hourly data older than 7 days
    op.execute("SELECT add_retention_policy('price_history_hourly', INTERVAL '7 days')")
```

### Adaptive Backoff State
```python
# Recommended: simple table for backoff state
# Persists across pipeline runs so flaky sources start slower
class BackoffState(Base):
    __tablename__ = "backoff_state"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source: Mapped[str] = mapped_column(String(30), unique=True, nullable=False)
    consecutive_failures: Mapped[int] = mapped_column(Integer, default=0)
    last_failure_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_success_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    current_delay_seconds: Mapped[float] = mapped_column(Float, default=1.0)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| yfinance `.download()` with period | yfinance `.download()` with start/end dates | v0.2+ | Date-range queries enable delta-fetch |
| ccxt sync API | ccxt async_support module | ccxt 2.0+ | Native async/await, no executor needed |
| Manual TimescaleDB chunk compression | `add_compression_policy()` | TimescaleDB 2.0+ | Automatic background compression |
| Manual data retention | `add_retention_policy()` | TimescaleDB 2.0+ | Auto-drop old hourly chunks |
| CoinGecko free API (no key) | CoinGecko Demo API key (free, 30 calls/min) | 2024 | Must register for stable rate limits |

**Deprecated/outdated:**
- `yfinance.Ticker.history()` for bulk fetches: Use `yfinance.download()` for multi-ticker support and better caching
- ccxt sync mode for Python: Use `ccxt.async_support` for proper async integration

## Open Questions

1. **yfinance IDX `.JK` delta-fetch reliability**
   - What we know: yfinance works for `.JK` tickers in general; date-range queries are supported
   - What's unclear: How reliable is delta-fetch (specific date ranges) for IDX tickers? Flagged as research blocker in STATE.md
   - Recommendation: Early prototyping task in Wave 1 -- fetch BBCA.JK for a specific 5-day range and verify. If unreliable, fall back to period-based fetch with local dedup

2. **IDX Trading Calendar**
   - What we know: IDX has unique holidays (Idul Fitri, Nyepi, etc.) not in standard calendars
   - What's unclear: No free API for IDX trading calendar identified
   - Recommendation: Build a static calendar table or use "last N business days minus weekends" heuristic for staleness; improve in Phase 6

3. **CoinGecko OHLCV endpoint for fallback**
   - What we know: CoinGecko has `/coins/{id}/ohlc` endpoint returning [timestamp, open, high, low, close]
   - What's unclear: Volume is NOT included in CoinGecko OHLC endpoint -- only in `/coins/{id}/market_chart`
   - Recommendation: Use `/coins/{id}/market_chart` for fallback (includes volume via `total_volumes`) or accept null volume from CoinGecko with source tag

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Docker | TimescaleDB | Yes | 28.5.1 | -- |
| Docker Compose | Service orchestration | Yes | v2.40.3 | -- |
| TimescaleDB (Docker) | Hypertables | Yes | 2.18.0-pg16 | -- |
| Python 3.13+ | Runtime | Yes | >=3.13 (pyproject.toml) | -- |
| yfinance | IDX stocks | No (not installed) | Install >=1.2.0 | -- |
| ccxt | Crypto OHLCV | No (not installed) | Install >=4.4 | -- |
| pandas | DataFrame processing | No (not installed) | Install >=2.2 | -- |

**Missing dependencies with no fallback:**
- yfinance, ccxt, pandas must be added via `uv add yfinance ccxt pandas`

**Missing dependencies with fallback:**
- None

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest >=9.0.2 + pytest-asyncio >=1.3.0 |
| Config file | pyproject.toml `[tool.pytest.ini_options]` (asyncio_mode="auto") |
| Quick run command | `uv run pytest tests/test_data/ -x -q` |
| Full suite command | `uv run pytest tests/ -x -q` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| DATA-01 | OHLCV stored in hypertable with compression | integration | `uv run pytest tests/test_data/test_price_repo.py -x` | No -- Wave 0 |
| DATA-01 | Compression policy applied | integration (requires TimescaleDB) | `uv run pytest tests/test_data/test_migration.py -x` | No -- Wave 0 |
| DATA-02 | IDX stock fetch via yfinance .JK | unit (mocked) | `uv run pytest tests/test_data/test_idx_fetcher.py -x` | No -- Wave 0 |
| DATA-02 | Validation rejects null OHLCV | unit | `uv run pytest tests/test_data/test_validation.py -x` | No -- Wave 0 |
| DATA-02 | Staleness detected for stale IDX data | unit | `uv run pytest tests/test_data/test_staleness.py -x` | No -- Wave 0 |
| DATA-03 | Crypto fetch via ccxt | unit (mocked) | `uv run pytest tests/test_data/test_crypto_fetcher.py -x` | No -- Wave 0 |
| DATA-03 | CoinGecko fallback on ccxt failure | unit (mocked) | `uv run pytest tests/test_data/test_crypto_fetcher.py::test_coingecko_fallback -x` | No -- Wave 0 |
| ALL | Idempotent upsert (no duplicates) | unit | `uv run pytest tests/test_data/test_price_repo.py::test_upsert_idempotent -x` | No -- Wave 0 |
| ALL | Ingest stage integrates with PipelineRunner | integration | `uv run pytest tests/test_data/test_ingest.py -x` | No -- Wave 0 |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/test_data/ -x -q`
- **Per wave merge:** `uv run pytest tests/ -x -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_data/__init__.py` -- package init
- [ ] `tests/test_data/test_validation.py` -- OHLCV validation rules (DATA-01, DATA-02)
- [ ] `tests/test_data/test_idx_fetcher.py` -- yfinance fetch with mocked responses (DATA-02)
- [ ] `tests/test_data/test_crypto_fetcher.py` -- ccxt + CoinGecko fallback (DATA-03)
- [ ] `tests/test_data/test_staleness.py` -- staleness detection logic
- [ ] `tests/test_data/test_price_repo.py` -- upsert idempotency, asyncpg raw SQL
- [ ] `tests/test_data/test_ingest.py` -- ingest stage integration
- [ ] `tests/test_data/conftest.py` -- shared fixtures (mock yfinance data, mock ccxt responses)

## Sources

### Primary (HIGH confidence)
- [yfinance PyPI](https://pypi.org/project/yfinance/) - Latest version 1.2.0 confirmed
- [yfinance download() API reference](https://ranaroussi.github.io/yfinance/reference/api/yfinance.download.html) - Parameters, date handling
- [ccxt GitHub examples](https://github.com/ccxt/ccxt/blob/master/examples/py/binance-fetch-ohlcv.py) - Async OHLCV fetch pattern
- [ccxt documentation](https://docs.ccxt.com/) - Unified API, rate limiting, pagination
- [TimescaleDB compression docs](https://github.com/timescale/docs.timescale.com-content/blob/master/using-timescaledb/compression.md) - Compression policy, segmentby/orderby
- [TimescaleDB upsert docs](https://docs.timescale.com/use-timescale/latest/write-data/upsert/) - INSERT ON CONFLICT on hypertables
- [asyncpg bulk upsert discussion](https://github.com/MagicStack/asyncpg/issues/755) - executemany pattern for upserts
- [Alembic + TimescaleDB discussion](https://github.com/sqlalchemy/alembic/discussions/1465) - Index conflict workaround

### Secondary (MEDIUM confidence)
- [CoinGecko rate limits](https://docs.coingecko.com/docs/common-errors-rate-limit) - 5-15 calls/min free, 30 calls/min Demo
- [CoinGecko pricing](https://www.coingecko.com/en/api/pricing) - 10k calls/mo Demo tier
- [TimescaleDB upsert performance blog](https://www.tigerdata.com/blog/how-we-made-postgresql-upserts-300x-faster-on-compressed-data) - Compressed chunk upsert pitfalls

### Tertiary (LOW confidence)
- yfinance IDX `.JK` delta-fetch reliability -- no authoritative source; needs prototyping

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - Libraries are well-documented, versions verified via PyPI
- Architecture: HIGH - Patterns follow ARCHITECTURE.md exactly; asyncpg hot path is documented best practice
- Pitfalls: HIGH - Known issues well-documented in GitHub issues and community posts
- yfinance IDX reliability: LOW - Unofficial API, IDX-specific behavior needs prototyping

**Research date:** 2026-03-23
**Valid until:** 2026-04-07 (yfinance can break at any time; ccxt and TimescaleDB are stable)
