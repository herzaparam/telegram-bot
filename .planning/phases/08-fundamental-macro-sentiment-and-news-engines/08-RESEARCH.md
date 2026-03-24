# Phase 8: Fundamental, Macro, Sentiment, and News Engines - Research

**Researched:** 2026-03-24
**Domain:** Financial data engines, external API integration, RSS/news ingestion, LLM-based scoring
**Confidence:** HIGH

## Summary

Phase 8 adds four new engines (Fundamental, Macro, Sentiment, Event) plus three new data fetchers (macro from FRED, news from RSS+Finnhub, sentiment from Fear&Greed+Reddit) and an LLM-based news impact scorer. The existing codebase provides a clean, well-established engine pattern (BaseEngine -> Signal dataclass, zone-mapping + weighted average scoring) and a fetch-then-cache data architecture. All four engines follow the same `BaseEngine.analyze()` contract and plug into `_get_engines_for_asset()` in `analyze.py`.

Key technical findings: (1) yfinance `.info` dict reliably provides P/E, P/B, ROE, revenue growth, dividend yield for IDX .JK tickers -- verified live against BBCA.JK; (2) FRED provides all needed macro series via `fredapi` with well-known series IDs; (3) alternative.me Fear & Greed API is free, no-auth, returns JSON with value 0-100; (4) RSS feeds from Kontan use `https://www.kontan.co.id/feed` (not rss.kontan.co.id which is down); (5) the four new engines are data-store-backed (they read from DB, not from the price DataFrame), which is a new pattern requiring careful integration.

**Primary recommendation:** Implement in waves: (1) DB migrations + config for all new tables/keys, (2) fetchers (fundamental, macro, news, sentiment), (3) engines (fundamental, macro, sentiment, event), (4) LLM news scorer + report news section. Each wave builds on the prior and can be tested independently.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Use yfinance `.info` dict as the sole data source for IDX stock fundamentals (P/E, P/B, revenue growth, ROE, dividend yield, debt/equity)
- **D-02:** Cache fundamentals in a new `stock_fundamentals` table. Weekly refresh -- skip fetch if data is <7 days old
- **D-03:** For crypto assets, return score=0/confidence=0 with reasoning "Fundamentals not applicable for crypto" (not supports_crypto=False -- keep engine visible to LLM)
- **D-04:** Six ratios: P/E, P/B, revenue growth, ROE, dividend yield, and debt/equity. Zone-map each ratio to a sub-score (-1 to +1), combine via weighted average (same pattern as TechnicalEngine)
- **D-05:** Fetch-then-cache pattern: new macro fetcher runs during fetch stage, stores macro indicators in a new `macro_data` table. MacroEngine.analyze() reads cached macro data from DB (not the price DataFrame). Same BaseEngine contract preserved
- **D-06:** FRED as the sole macro data source -- covers Fed funds rate, US CPI, DXY index, and USD/IDR exchange rate. Single API, free, well-documented `fredapi` library. No Bank Indonesia or World Bank APIs needed
- **D-07:** One global macro score per pipeline run. Reasoning highlights IDX-relevant factors (BI rate proxy, rupiah via USD/IDR) for stocks and global factors (Fed rate, DXY, risk appetite) for crypto. LLM interprets the contextual difference
- **D-08:** FRED API key required -- add `FRED_API_KEY` to Settings and .env
- **D-09:** Two sentiment sources: Crypto Fear & Greed Index (alternative.me, free, no auth) + Reddit via PRAW (r/cryptocurrency for crypto, r/finansial for IDX stocks). Skip Stockbit scraping -- too fragile
- **D-10:** Reddit sentiment analyzed via LLM batch call: fetch top ~20 posts per subreddit daily, one LLM call per subreddit, returns sentiment score per mentioned asset. Uses existing `llm_completion()` with JSON mode. ~$0.02/day
- **D-11:** Reddit API keys needed -- add `REDDIT_CLIENT_ID` and `REDDIT_CLIENT_SECRET` to Settings and .env
- **D-12:** Graceful degradation: if Reddit API unavailable, engine still produces a score from Fear & Greed alone with lowered confidence
- **D-13:** News fetchers (RSS for Indonesian + Finnhub for global) run as part of the existing fetch stage, alongside price and macro fetchers. News is global data, cached in `news_events` table
- **D-14:** Batch LLM scoring: collect all today's headlines (RSS + Finnhub), send in one LLM call with the watchlist. LLM returns impact_score + affected_assets + category per headline. ~$0.03/day
- **D-15:** Indonesian news from three RSS feeds: Kontan (rss.kontan.co.id), CNBC Indonesia (cnbcindonesia.com/news/rss), Bisnis (bisnis.com/rss) via `feedparser` library
- **D-16:** Global crypto/financial news from Finnhub REST API. Free tier (60 calls/min, plenty for daily batch). User will register for API key -- add `FINNHUB_API_KEY` to Settings and .env
- **D-17:** EventEngine reads from `news_events` table (populated by news fetchers + LLM scoring). Signals upcoming earnings, BI rate meetings, and crypto halvings based on news category tags
- **D-18:** Event engine is news-derived, not calendar-based -- events surface through LLM classification of news headlines
- **D-19:** Separate "News & Events" section at the bottom of the daily report. Top 5-10 high-impact headlines grouped by category
- **D-20:** News digest satisfies NEWS-04 requirement

### Claude's Discretion
- Exact zone thresholds for fundamental ratio scoring (e.g., P/E <15 = bullish)
- Fundamental ratio weights
- FRED series IDs for each macro indicator
- Macro score computation method (how to combine multiple macro indicators)
- Macro data refresh frequency (daily or weekly)
- Reddit post selection criteria (top/hot, time window)
- LLM prompt design for Reddit sentiment analysis and news impact scoring
- news_events table migration details
- macro_data and stock_fundamentals table schemas
- RSS parsing and deduplication logic
- Finnhub endpoint selection (general news vs company news)
- Event engine scoring logic (how news categories map to event signals)
- Error handling for each new data source
- How to wire new engines into `_get_engines_for_asset()` in analyze.py

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| ENGN-02 | Fundamental analysis engine (P/E, P/B, revenue growth, ROE) for IDX stocks | yfinance `.info` dict verified to contain trailingPE, priceToBook, returnOnEquity, revenueGrowth, dividendYield for BBCA.JK. Zone-mapping pattern from TechnicalEngine applies directly. D-01 through D-04 define approach. |
| ENGN-05 | Sentiment engine (Reddit, Stockbit, Fear & Greed) | alternative.me API verified (free, no auth, 60 req/min). asyncpraw for Reddit async access. D-09/D-10/D-12 define sources and degradation. Stockbit scraping deferred per D-09. |
| ENGN-09 | Event-driven engine (earnings calendar, BI meetings, halving) | News-derived approach per D-17/D-18. EventEngine reads `news_events` table, filters by LLM-assigned category tags. No static calendar needed. |
| ENGN-12 | Macro/economic engine (BI rate, Fed rate, CPI, DXY, rupiah) | FRED API covers all needed series. fredapi library verified. Series IDs identified: DFF, CPIAUCSL, DTWEXBGS, CCUSMA02IDM618N. D-05 through D-08 define approach. |
| NEWS-01 | Ingest Indonesian financial news (Kontan, CNBC Indonesia, Bisnis) via RSS | feedparser library (latest PyPI). Kontan RSS at `https://www.kontan.co.id/feed`. CNBC Indonesia and Bisnis RSS feeds to be verified at integration time. D-15 defines sources. |
| NEWS-02 | Ingest global crypto/financial news (Finnhub) | finnhub-python library, free tier 60 calls/min. General news endpoint for market-wide headlines. D-16 defines approach. |
| NEWS-03 | LLM scores news impact per asset | Batch LLM call via existing `llm_completion()` with JSON mode. D-14 defines approach. One call with all headlines + watchlist, returns structured per-headline scoring. |
| NEWS-04 | Daily digest of relevant news in report | News section in Telegram report via `format_news_digest()` in formatter.py. D-19/D-20 define format and placement. |
</phase_requirements>

## Project Constraints (from CLAUDE.md)

- Python 3.13, uv package manager
- pydantic-settings for configuration, `.env` for secrets
- SQLAlchemy async ORM + Alembic migrations
- structlog JSON logging with component binding
- Two-process boundary: bot MUST NOT import pipeline/llm modules
- Per-asset error isolation via try/except in analyze_stage
- `_failed_signal()` fallback on any engine exception
- HTML parse_mode for Telegram messages
- mypy strict mode with type annotations
- ruff for linting/formatting
- pre-commit hooks enforced
- Report formatter in `src/report/` shared by both processes

## Standard Stack

### Core (New Dependencies)
| Library | Purpose | Why Standard |
|---------|---------|--------------|
| feedparser | Parse RSS feeds from Indonesian news sites | De facto Python RSS parser, lightweight, no auth needed |
| fredapi | Fetch FRED macro data (Fed rate, CPI, DXY, USD/IDR) | Official FRED Python client by mortada/fredapi, returns pandas Series |
| asyncpraw | Async Reddit API access for sentiment data | Official async fork of PRAW, handles rate limiting/auth automatically |
| finnhub-python | Fetch global financial/crypto news | Official Finnhub Python client, clean REST wrapper |

### Existing (Already Installed)
| Library | Purpose in This Phase |
|---------|----------------------|
| yfinance | Fetch `.info` dict for IDX stock fundamentals (P/E, P/B, ROE, etc.) |
| litellm | LLM calls for Reddit sentiment analysis and news impact scoring |
| httpx | HTTP client for Fear & Greed API (alternative.me) |
| sqlalchemy[asyncio] | ORM models for new tables, async DB access |
| alembic | Database migrations for 3 new tables |
| structlog | Logging in all new modules |
| pydantic-settings | New API key configuration fields |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| fredapi | Direct FRED REST API via httpx | fredapi handles pagination, rate limiting, returns pandas; direct HTTP adds boilerplate |
| asyncpraw | praw (sync) + run_in_executor | asyncpraw is native async, cleaner in async pipeline; sync praw would work but adds executor overhead |
| feedparser | httpx + manual XML parsing | feedparser handles encoding, date parsing, malformed feeds; manual parsing is fragile |
| finnhub-python | Direct Finnhub REST via httpx | Official client adds type hints and handles auth header; httpx works but more boilerplate |

**Installation:**
```bash
uv add feedparser fredapi asyncpraw finnhub-python
```

## Architecture Patterns

### New Files Structure
```
src/
  config.py                    # Add FRED_API_KEY, FINNHUB_API_KEY, REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET + engine weights
  data/
    macro_fetcher.py           # FRED macro data fetcher (fetch stage)
    news_fetcher.py            # RSS + Finnhub news fetcher (fetch stage)
    sentiment_fetcher.py       # Fear & Greed + Reddit sentiment fetcher (fetch stage)
    fundamental_fetcher.py     # yfinance .info fundamental data fetcher (fetch stage, per-asset)
  engines/
    fundamental.py             # FundamentalEngine (reads stock_fundamentals table)
    macro.py                   # MacroEngine (reads macro_data table)
    sentiment.py               # SentimentEngine (reads sentiment cache)
    event.py                   # EventEngine (reads news_events table)
  llm/
    news_analyzer.py           # LLM-based news impact scoring
  db/
    models.py                  # Add NewsEvent, MacroData, StockFundamental models
    migrations/versions/
      007_news_macro_fundamentals.py  # New tables migration
  report/
    formatter.py               # Add format_news_digest() function
```

### Pattern 1: Store-Backed Engine (New Pattern for Phase 8)
**What:** Engines that read pre-fetched data from DB tables rather than from the price DataFrame
**When to use:** When engine data comes from external APIs (FRED, RSS, Reddit) fetched during the fetch stage
**Example:**
```python
# src/engines/macro.py
class MacroEngine(BaseEngine):
    @property
    def category(self) -> str:
        return "macro"

    def __init__(self, macro_data: dict[str, float] | None = None) -> None:
        self._macro_data = macro_data

    def analyze(self, asset_id: int, asset_symbol: str, df: pd.DataFrame) -> Signal:
        if self._macro_data is None:
            return Signal(category="macro", score=0.0, confidence=0.0,
                          reasoning="No macro data available", indicators={}, data_quality={})
        # Zone-map each macro indicator, combine via weighted average
        ...
```

**Key insight:** The `analyze()` signature accepts `df: pd.DataFrame` but store-backed engines may ignore it. Data is injected via constructor or loaded from DB within `analyze_stage()` before calling `engine.analyze()`. The `analyze_stage()` function in `analyze.py` must be extended to load macro/sentiment/news data from DB and pass it to the new engines.

### Pattern 2: Global Fetcher (Not Per-Asset)
**What:** Fetchers that run once per pipeline run for global data (macro, news) rather than per-asset
**When to use:** When data is shared across all assets (FRED rates, news headlines, Fear & Greed)
**Example:**
```python
# In pipeline/main.py or called before per-asset fetch stage
async def fetch_global_data(session: AsyncSession) -> None:
    """Fetch macro, news, and sentiment data once per pipeline run."""
    await fetch_macro_data(session)      # FRED -> macro_data table
    await fetch_news(session)            # RSS + Finnhub -> news_events table
    await fetch_sentiment_data(session)  # Fear & Greed + Reddit -> sentiment cache
    await score_news_impact(session)     # LLM batch scoring of today's headlines
```

**Integration point:** Global fetchers should run once before the per-asset fetch loop. They can be called in `async_main()` in `pipeline/main.py` before `runner.run_pipeline()`, or as a separate pre-fetch stage.

### Pattern 3: Per-Asset Fetcher (Fundamental Data)
**What:** Fundamental data fetch runs per-asset during the existing fetch stage, similar to price fetching
**When to use:** When data is asset-specific (yfinance .info per stock ticker)
**Example:**
```python
# In data/fundamental_fetcher.py
async def fetch_fundamentals(session: AsyncSession, asset: Asset) -> None:
    """Fetch and cache fundamental data for a stock asset."""
    if asset.asset_type != "stock":
        return  # Crypto has no fundamentals to fetch

    # Check cache freshness (weekly refresh per D-02)
    existing = await _get_cached_fundamentals(session, asset.id)
    if existing and (date.today() - existing.fetched_at.date()).days < 7:
        return

    # Fetch via yfinance (blocking, needs run_in_executor)
    info = await asyncio.get_event_loop().run_in_executor(
        None, _fetch_yfinance_info, asset.yfinance_symbol or asset.symbol
    )
    await _upsert_fundamentals(session, asset.id, info)
```

### Pattern 4: Zone-Mapping Scoring (Replicated from TechnicalEngine)
**What:** Map each input metric to a sub-score in [-1, +1], then weighted-average combine
**When to use:** All four new engines
**Example for fundamental ratios:**
```python
def _pe_to_score(pe: float | None) -> float:
    """Map P/E ratio to sub-score. Lower P/E = more attractive = higher score."""
    if pe is None:
        return 0.0
    if pe < 0:
        return -0.8  # Negative earnings
    if pe < 8:
        return 0.8   # Deeply undervalued
    if pe < 12:
        return 0.5   # Undervalued
    if pe < 18:
        return 0.2   # Fair value
    if pe < 25:
        return -0.2  # Slightly overvalued
    if pe < 40:
        return -0.5  # Overvalued
    return -0.8       # Extremely overvalued
```

### Anti-Patterns to Avoid
- **Calling external APIs inside engine.analyze():** Engines must be CPU-bound and read from DB only. All I/O happens during the fetch stage.
- **Making engines async:** `BaseEngine.analyze()` is synchronous. Store-backed engines load data before calling analyze, or accept data via constructor.
- **Blocking the event loop with yfinance:** Always wrap yfinance calls in `run_in_executor()` as IDXStockFetcher already does.
- **Fetching global data per-asset:** Macro, news, and Fear & Greed data should be fetched once per pipeline run, not once per asset.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| RSS parsing | Custom XML parser | feedparser | Handles encoding, malformed feeds, date normalization |
| FRED data access | Direct HTTP to FRED API | fredapi | Pagination, rate limiting, pandas return type |
| Reddit API auth + rate limiting | Custom OAuth2 flow | asyncpraw | Handles token refresh, rate limit headers, pagination |
| News deduplication | Custom string matching | URL-based dedup with DB unique constraint | Headlines may differ across sources for same story; URL is canonical |
| LLM JSON parsing | Manual string manipulation | `response_format={"type": "json_object"}` via litellm | Guarantees valid JSON from LLM |

## Common Pitfalls

### Pitfall 1: yfinance .info Returns None for Some Fields
**What goes wrong:** Not all IDX stocks have all fundamental metrics. `debtToEquity` returned `None` for BBCA.JK in live testing.
**Why it happens:** yfinance scrapes Yahoo Finance which has incomplete data for some IDX stocks.
**How to avoid:** Every zone-mapping function must handle `None` input gracefully (return 0.0 score). Confidence should decrease proportionally to missing fields.
**Warning signs:** Engine returning 0/0 for all stocks.

### Pitfall 2: FRED Series Update Lag
**What goes wrong:** FRED data updates on different schedules -- DFF (daily), CPIAUCSL (monthly, ~2 week lag), DTWEXBGS (daily on business days).
**Why it happens:** Different economic indicators have different release schedules.
**How to avoid:** Always fetch the latest available observation, not today's date specifically. Use `fredapi.get_series()` with no end date and take the last value. Store the observation date alongside the value.
**Warning signs:** Macro score stuck at the same value for weeks.

### Pitfall 3: RSS Feed Format Changes
**What goes wrong:** Indonesian news sites may change their RSS feed structure or URL without notice.
**Why it happens:** RSS is not a primary product for these news sites.
**How to avoid:** Wrap each RSS source in try/except, log failures, continue with other sources. Use SUPPLEMENTARY tier so failures don't block the pipeline. Kontan's RSS is at `https://www.kontan.co.id/feed` (NOT `rss.kontan.co.id` which is down).
**Warning signs:** Zero news items fetched for multiple days.

### Pitfall 4: Reddit Rate Limiting with asyncpraw
**What goes wrong:** Reddit API returns 429 errors or asyncpraw raises RedditAPIException.
**Why it happens:** Reddit's rate limits are 100 req/min for OAuth clients but there are undocumented limits.
**How to avoid:** asyncpraw handles rate limiting automatically (waits up to `ratelimit_seconds=5`). Fetch only ~20 posts per subreddit, which requires very few API calls. D-12 mandates graceful degradation -- if Reddit fails, use Fear & Greed alone with lowered confidence.
**Warning signs:** Consistent RedditAPIException in logs.

### Pitfall 5: Store-Backed Engines Getting Stale Data
**What goes wrong:** Engine reads data from a prior pipeline run because the current run's fetcher failed silently.
**Why it happens:** Macro/news fetchers run before engines. If a fetcher fails, the engine reads old data.
**How to avoid:** Each DB record should have a `fetched_at` timestamp. Engines should check data freshness and lower confidence for stale data. Log warnings for data older than expected refresh interval.
**Warning signs:** Macro score showing no change despite market shifts.

### Pitfall 6: LLM News Scoring Cost Overruns
**What goes wrong:** Too many headlines sent to LLM, or headlines are too long, causing high token usage.
**Why it happens:** RSS feeds can return dozens of items; Finnhub returns many headlines.
**How to avoid:** Cap at 50 headlines per LLM call. Send only headline + source (not full article). Limit headline text to 200 chars. Per D-14, expected cost is ~$0.03/day -- monitor actual usage.
**Warning signs:** LLM call timing out or daily costs exceeding $0.10.

### Pitfall 7: FRED API Key Missing Blocks Entire Pipeline
**What goes wrong:** Pipeline crashes because FRED_API_KEY is empty/missing.
**Why it happens:** New API key not added to .env on deployment.
**How to avoid:** Make all new API keys optional in Settings (default to empty string). Macro fetcher checks for key before calling FRED -- if missing, logs warning and returns empty data. MacroEngine handles missing data gracefully (score=0, confidence=0). Same pattern for FINNHUB_API_KEY and Reddit keys.
**Warning signs:** "FRED_API_KEY not configured" warning in logs.

## Code Examples

### FRED Series IDs for Macro Indicators
```python
# Verified FRED series IDs
FRED_SERIES = {
    "fed_funds_rate": "DFF",           # Federal Funds Effective Rate (daily)
    "cpi": "CPIAUCSL",                 # CPI All Urban Consumers (monthly, ~2wk lag)
    "dxy": "DTWEXBGS",                 # Nominal Broad US Dollar Index (daily, business days)
    "usd_idr": "CCUSMA02IDM618N",      # USD/IDR Average of Daily Rates (monthly)
}
# Note: BI rate is not directly in FRED. Use fed_funds_rate as proxy per D-07.
```

### Fear & Greed API Call
```python
# Source: https://api.alternative.me/fng/
async def fetch_fear_greed(client: httpx.AsyncClient) -> dict[str, object]:
    """Fetch current Crypto Fear & Greed Index."""
    resp = await client.get("https://api.alternative.me/fng/?limit=1")
    resp.raise_for_status()
    data = resp.json()
    entry = data["data"][0]
    return {
        "value": int(entry["value"]),             # 0-100
        "classification": entry["value_classification"],  # "Extreme Fear", "Fear", etc.
        "timestamp": int(entry["timestamp"]),
    }
```

### News Events Table Schema
```python
# src/db/models.py addition
class NewsEvent(Base):
    """News headline with LLM-scored impact."""
    __tablename__ = "news_events"
    __table_args__ = (UniqueConstraint("url", name="uq_news_events_url"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    headline: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str] = mapped_column(String(50), nullable=False)  # "kontan", "cnbc_id", "bisnis", "finnhub"
    url: Mapped[str] = mapped_column(Text, nullable=False)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    impact_score: Mapped[float | None] = mapped_column(Float, nullable=True)  # -1.0 to +1.0
    affected_assets: Mapped[dict[str, object] | None] = mapped_column(JSONB, nullable=True)  # {"BBCA": 0.7, "BTC": -0.3}
    category: Mapped[str | None] = mapped_column(String(30), nullable=True)  # "central_bank", "earnings", "regulation", "halving"
    raw_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
```

### Macro Data Table Schema
```python
class MacroData(Base):
    """Cached macro economic indicator values from FRED."""
    __tablename__ = "macro_data"
    __table_args__ = (UniqueConstraint("series_id", "observation_date", name="uq_macro_data_series_date"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    series_id: Mapped[str] = mapped_column(String(30), nullable=False)  # "DFF", "CPIAUCSL", etc.
    observation_date: Mapped[date] = mapped_column(Date, nullable=False)
    value: Mapped[float] = mapped_column(Float, nullable=False)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
```

### Stock Fundamentals Table Schema
```python
class StockFundamental(Base):
    """Cached fundamental data from yfinance .info dict."""
    __tablename__ = "stock_fundamentals"
    __table_args__ = (UniqueConstraint("asset_id", name="uq_stock_fundamentals_asset"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    asset_id: Mapped[int] = mapped_column(Integer, ForeignKey("assets.id"), nullable=False)
    trailing_pe: Mapped[float | None] = mapped_column(Float, nullable=True)
    forward_pe: Mapped[float | None] = mapped_column(Float, nullable=True)
    price_to_book: Mapped[float | None] = mapped_column(Float, nullable=True)
    return_on_equity: Mapped[float | None] = mapped_column(Float, nullable=True)
    revenue_growth: Mapped[float | None] = mapped_column(Float, nullable=True)
    dividend_yield: Mapped[float | None] = mapped_column(Float, nullable=True)
    debt_to_equity: Mapped[float | None] = mapped_column(Float, nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
```

### Wiring New Engines into analyze_stage
```python
# In src/data/analyze.py -- modified _get_engines_for_asset
from src.engines.fundamental import FundamentalEngine
from src.engines.macro import MacroEngine
from src.engines.sentiment import SentimentEngine
from src.engines.event import EventEngine

async def _load_engine_context(session: AsyncSession, asset: Asset) -> dict[str, object]:
    """Load store-backed data for engines that need DB data."""
    context: dict[str, object] = {}
    # Load fundamentals for this asset
    context["fundamentals"] = await _load_fundamentals(session, asset.id)
    # Load global macro data (same for all assets)
    context["macro_data"] = await _load_latest_macro(session)
    # Load sentiment data
    context["sentiment"] = await _load_sentiment(session, asset)
    # Load news events for event engine
    context["news_events"] = await _load_recent_news(session)
    return context

def _get_engines_for_asset(asset: Asset, context: dict[str, object]) -> list[BaseEngine]:
    """Return engines applicable to this asset type."""
    all_engines: list[BaseEngine] = [
        TechnicalEngine(),
        QuantitativeEngine(),
        FundamentalEngine(fundamentals=context.get("fundamentals")),
        MacroEngine(macro_data=context.get("macro_data")),
        SentimentEngine(sentiment_data=context.get("sentiment")),
        EventEngine(news_events=context.get("news_events")),
    ]
    return [
        e for e in all_engines
        if (asset.asset_type == "stock" and e.supports_stocks)
        or (asset.asset_type == "crypto" and e.supports_crypto)
    ]
```

### LLM News Impact Scoring Prompt
```python
NEWS_SCORING_SYSTEM_PROMPT = """\
You are a financial news analyst. Score each headline's impact on the listed assets.

Output valid JSON array where each element has:
- headline_index: int (0-based index matching input)
- impact_score: float from -1.0 (very bearish) to +1.0 (very bullish), 0.0 if irrelevant
- affected_assets: dict of asset_symbol -> relevance_score (0.0 to 1.0)
- category: one of "central_bank", "earnings", "regulation", "halving", "macro", "sector", "company", "market", "other"

Only include assets from the watchlist that are meaningfully affected."""
```

### Fundamental Zone Thresholds (Recommended)
```python
# IDX stock P/E thresholds (IDX market averages ~12-18x)
PE_ZONES = [
    (0, -0.8),     # Negative earnings
    (8, 0.8),      # Deeply undervalued
    (12, 0.5),     # Undervalued
    (18, 0.2),     # Fair value
    (25, -0.2),    # Slightly overvalued
    (40, -0.5),    # Overvalued
    (999, -0.8),   # Extremely overvalued
]

# P/B thresholds
PB_ZONES = [
    (0.5, 0.8),    # Deeply undervalued
    (1.0, 0.5),    # Undervalued
    (2.0, 0.2),    # Fair value
    (3.5, -0.2),   # Slightly overvalued
    (6.0, -0.5),   # Overvalued
    (999, -0.8),   # Extremely overvalued
]

# ROE thresholds (higher is better)
ROE_ZONES = [
    (0.0, -0.7),   # Negative ROE
    (0.05, -0.3),  # Poor
    (0.10, 0.0),   # Below average
    (0.15, 0.3),   # Average
    (0.20, 0.6),   # Good
    (1.0, 0.8),    # Excellent
]

# Recommended weights for fundamental ratios
FUNDAMENTAL_WEIGHTS = {
    "pe": 0.25,
    "pb": 0.15,
    "roe": 0.25,
    "revenue_growth": 0.15,
    "dividend_yield": 0.10,
    "debt_to_equity": 0.10,
}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| praw (sync) | asyncpraw | 2021+ | Native async Reddit API wrapper, no need for run_in_executor |
| Manual FRED HTTP | fredapi library | Stable since 2019 | Clean pandas-based interface, handles pagination |
| feedparser 5.x | feedparser 6.x | 2020 | Python 3 native, better encoding handling |
| Finnhub websocket | Finnhub REST for batch | Current | REST is simpler for daily batch; websocket for real-time only |

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2+ with pytest-asyncio |
| Config file | `pyproject.toml` [tool.pytest.ini_options] |
| Quick run command | `uv run pytest tests/test_engines/ -x -q` |
| Full suite command | `uv run pytest tests/ -x -q` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| ENGN-02 | Fundamental engine scores IDX stocks, returns 0/0 for crypto | unit | `uv run pytest tests/test_engines/test_fundamental.py -x` | Wave 0 |
| ENGN-05 | Sentiment engine combines Fear&Greed + Reddit, degrades gracefully | unit | `uv run pytest tests/test_engines/test_sentiment.py -x` | Wave 0 |
| ENGN-09 | Event engine surfaces upcoming events from news_events | unit | `uv run pytest tests/test_engines/test_event.py -x` | Wave 0 |
| ENGN-12 | Macro engine produces context score from FRED data | unit | `uv run pytest tests/test_engines/test_macro.py -x` | Wave 0 |
| NEWS-01 | RSS fetcher ingests Indonesian news | unit | `uv run pytest tests/test_data/test_news_fetcher.py -x` | Wave 0 |
| NEWS-02 | Finnhub fetcher ingests global news | unit | `uv run pytest tests/test_data/test_news_fetcher.py -x` | Wave 0 |
| NEWS-03 | LLM scores news impact per asset | unit | `uv run pytest tests/test_llm/test_news_analyzer.py -x` | Wave 0 |
| NEWS-04 | News digest appears in daily report | unit | `uv run pytest tests/test_report/test_formatter_news.py -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/test_engines/ tests/test_data/ -x -q`
- **Per wave merge:** `uv run pytest tests/ -x -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_engines/test_fundamental.py` -- covers ENGN-02
- [ ] `tests/test_engines/test_macro.py` -- covers ENGN-12
- [ ] `tests/test_engines/test_sentiment.py` -- covers ENGN-05
- [ ] `tests/test_engines/test_event.py` -- covers ENGN-09
- [ ] `tests/test_data/test_news_fetcher.py` -- covers NEWS-01, NEWS-02
- [ ] `tests/test_data/test_macro_fetcher.py` -- covers macro data fetch
- [ ] `tests/test_data/test_sentiment_fetcher.py` -- covers sentiment data fetch
- [ ] `tests/test_data/test_fundamental_fetcher.py` -- covers fundamental data fetch
- [ ] `tests/test_llm/test_news_analyzer.py` -- covers NEWS-03
- [ ] `tests/test_report/test_formatter_news.py` -- covers NEWS-04
- [ ] `tests/test_data/test_migration.py` -- extend for 007 migration DDL check

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.13 | All code | Yes | 3.13 | -- |
| uv | Package management | Yes | 0.7.0 | -- |
| Docker/TimescaleDB | Database | Yes | Via docker-compose | -- |
| feedparser | NEWS-01 | Not installed | Latest on PyPI | -- |
| fredapi | ENGN-12 | Not installed | Latest on PyPI | -- |
| asyncpraw | ENGN-05 | Not installed | Latest on PyPI | -- |
| finnhub-python | NEWS-02 | Not installed | Latest on PyPI | -- |
| FRED API key | ENGN-12 | User must register | -- | Engine returns 0/0 |
| Finnhub API key | NEWS-02 | User must register | -- | Skip global news, use RSS only |
| Reddit API credentials | ENGN-05 | User must register | -- | Use Fear & Greed only (D-12) |

**Missing dependencies with no fallback:**
- feedparser, fredapi, asyncpraw, finnhub-python (must be installed via `uv add`)

**Missing dependencies with fallback:**
- FRED API key: macro engine degrades to score=0/confidence=0
- Finnhub API key: news fetcher skips global news, uses Indonesian RSS only
- Reddit credentials: sentiment engine uses Fear & Greed alone with lowered confidence (D-12)

## Open Questions

1. **Kontan RSS URL verification**
   - What we know: `rss.kontan.co.id` appears to be down (shows Apache default page). `https://www.kontan.co.id/feed` exists.
   - What's unclear: Whether `/feed` provides financial news or all categories; sub-feeds may exist.
   - Recommendation: Use `https://www.kontan.co.id/feed` as primary. Verify at implementation time and add category-specific feeds if available.

2. **CNBC Indonesia and Bisnis RSS exact URLs**
   - What we know: Decision D-15 references `cnbcindonesia.com/news/rss` and `bisnis.com/rss`.
   - What's unclear: Exact working URLs need runtime verification.
   - Recommendation: Verify at implementation time. feedparser will gracefully fail if URL is wrong; news source is SUPPLEMENTARY tier.

3. **Macro data refresh frequency**
   - What we know: FRED series update at different intervals (DFF daily, CPI monthly).
   - What's unclear: Whether to refresh all series daily or on their natural schedule.
   - Recommendation: Fetch all series daily. FRED API is free with generous limits. fredapi will return the latest observation even if it hasn't changed. Store observation_date to detect staleness.

4. **asyncpraw vs praw for this use case**
   - What we know: asyncpraw is the official async wrapper. We only fetch ~20 posts per subreddit once daily.
   - What's unclear: Whether asyncpraw adds unnecessary complexity for such light usage.
   - Recommendation: Use asyncpraw since the pipeline is fully async. Avoids run_in_executor overhead. If issues arise, fall back to sync praw + executor.

## Sources

### Primary (HIGH confidence)
- yfinance `.info` dict -- verified live against BBCA.JK: trailingPE=14.51, priceToBook=2.96, returnOnEquity=0.211, revenueGrowth=-0.027, dividendYield=4.96, debtToEquity=None
- FRED series IDs: DFF, CPIAUCSL, DTWEXBGS, CCUSMA02IDM618N -- verified via fred.stlouisfed.org
- alternative.me Fear & Greed API -- verified live: returns JSON with value (0-100), classification, timestamp
- Existing codebase patterns: BaseEngine, TechnicalEngine zone-mapping, analyze_stage, ingest_stage, pipeline/tiers.py

### Secondary (MEDIUM confidence)
- [fredapi PyPI](https://pypi.org/project/fredapi/) -- official FRED Python client
- [asyncpraw GitHub](https://github.com/praw-dev/asyncpraw) -- async Reddit API wrapper
- [Finnhub API docs](https://finnhub.io/docs/api/rate-limit) -- 60 calls/min free tier
- [alternative.me API docs](https://alternative.me/crypto/api/) -- Fear & Greed endpoint

### Tertiary (LOW confidence)
- Kontan RSS URL `https://www.kontan.co.id/feed` -- found via web search, not verified via feedparser parse
- CNBC Indonesia and Bisnis RSS URLs -- from D-15, not independently verified

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - all libraries well-established, yfinance data verified live
- Architecture: HIGH - follows existing codebase patterns exactly (BaseEngine, zone-mapping, fetch-then-cache)
- Pitfalls: HIGH - based on live testing of yfinance and understanding of FRED/RSS patterns
- New pattern (store-backed engines): MEDIUM - first time this pattern is used in this codebase, needs careful integration

**Research date:** 2026-03-24
**Valid until:** 2026-04-24 (stable libraries, well-known APIs)
