# Phase 11: Asset Discovery + Due Diligence - Research

**Researched:** 2026-03-26
**Domain:** Market scanning, ownership data scraping, due diligence analysis, Telegram command handlers
**Confidence:** MEDIUM-HIGH

## Summary

Phase 11 adds two major capabilities: (1) an asset discovery scanner that screens the full IHSG universe (~900 stocks) and top 100 crypto by market cap daily for unusual volume, breakouts, momentum surges, and statistical anomalies; and (2) a due diligence module for IDX stocks providing sector benchmarking, ownership analysis, management quality scoring, and competitive positioning. Three new Telegram commands (`/discover`, `/duediligence`, `/compare`) are added, the daily report gets a "New Opportunities" section, and the LLM decision prompt is enhanced with DD flags.

The discovery scanner is a new pipeline stage that runs on the full market universe (not per-watchlist-asset), which is architecturally different from existing per-asset StageFunc stages. It should run as a post-pipeline function similar to `run_batch_cross_cutting` and `send_daily_report`. For IDX scanning, yfinance bulk download with batches of ~80 tickers and inter-batch delays handles rate limiting. For crypto scanning, CoinGecko's free `/coins/markets` endpoint returns top 100 by market cap with price change and volume data in a single call.

Due diligence data sources include IDX disclosure filings (shareholder composition above 1% now publicly available since March 2026), existing parsed FinancialData for management quality scoring, and StockFundamental data for sector benchmarking. The architecture reuses the httpx scraping pattern from `idx_doc_fetcher.py` with weekly refresh cycles.

**Primary recommendation:** Implement discovery scanner as a post-pipeline function (not StageFunc), use yfinance batch download for IDX screening, CoinGecko `/coins/markets` for crypto screening, and build DD on top of existing FinancialData + StockFundamental models with a new `ownership_snapshots` table for IDX filings.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Scan all ~900 IHSG stocks daily for unusual activity -- full IDX universe, no filtering to LQ45/IDX80 subset. yfinance bulk fetch for screening data
- **D-02:** Scan top 100 crypto by market cap via CoinGecko for top movers and anomalies
- **D-03:** Four trigger types for flagging discoveries: volume spike (>2x 20-day avg), price breakout (52-week high, resistance break, Bollinger), momentum surge (RSI/MACD crossover), and statistical anomaly detection
- **D-04:** Screening criteria only -- scanner uses lightweight checks (volume, price patterns) to flag candidates. Full 15-engine analysis only runs when user adds asset to watchlist. Keeps scan fast
- **D-05:** Top 5 opportunities presented as compact cards in daily report "New Opportunities" section, matching existing report card style from Phase 5
- **D-06:** Multi-trigger composite score for ranking -- weight each trigger type and combine into single score. Assets with multiple triggers rank higher
- **D-07:** Insider/ownership data from IDX disclosure filings on idx.co.id -- reuse httpx scraping patterns from Phase 9 PDF fetcher
- **D-08:** Extract shareholder composition with percentages, plus quarter-over-quarter changes. Flag when major holders increase/decrease positions significantly. No individual insider transaction log
- **D-09:** Management quality scored on financial track record only -- revenue CAGR, ROE trend, capital allocation efficiency over 3-5 years. All data already available from Phase 9 parsed financials
- **D-10:** Sector benchmarking uses IDX sector classification (Banking, Telco, Consumer, etc.) -- compare company P/E, P/B, ROE, margins against sector median. Highlights above/below sector
- **D-11:** Due diligence is IDX stocks only. Crypto assets get "not applicable" response (consistent with /valuation in Phase 9)
- **D-12:** Weekly refresh cycle for ownership/DD data -- matches Phase 9's weekly PDF check pattern. Insider transactions are disclosed periodically, not daily
- **D-13:** DD flags appear in daily report and /duediligence command only. No push alerts -- consistent with daily-cadence design
- **D-14:** `/discover` shows today's top 5 opportunities as compact cards (ticker, trigger type icon, signal strength, current price + change%). No filtering arguments -- simple, show top 5 overall
- **D-15:** `/duediligence BBCA` returns single comprehensive message with all DD info: sector rank, ownership changes, management score, competitive position. Compact formatting like /valuation
- **D-16:** `/compare BBCA BBRI BMRI` displays side-by-side metrics table with tickers as columns, metrics as rows (P/E, P/B, ROE, margins, debt/equity). Best/worst highlighted
- **D-17:** `/compare` is IDX stocks only -- comparison uses fundamental metrics (P/E, ROE, etc.) which are equity-specific
- **D-18:** DD flags (insider selling, management changes, earnings quality warnings) added to existing LLM decision prompt as additional context section. LLM weighs them naturally alongside engine scores (LLM-06)

### Claude's Discretion
- Discovery scanner implementation details (batch size, rate limiting for yfinance/CoinGecko)
- Composite score weights for trigger types
- Volume spike threshold tuning (2x as starting point)
- Breakout detection algorithm specifics
- Anomaly detection statistical method
- IDX disclosure filing URL structure and scraping implementation
- Sector classification mapping maintenance
- Management quality score formula and thresholds
- DD flag severity levels and how they appear in LLM prompt
- New DB tables schema (discovery_candidates, due_diligence_data, ownership_snapshots, etc.)
- Alembic migration details
- Error handling and graceful degradation per data source
- Telegram message formatting and emoji/icon choices

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| DISC-01 | Scan all IHSG stocks for unusual volume, breakouts | yfinance batch download in groups of 80, volume spike + breakout detection algorithms |
| DISC-02 | Scan crypto market for top movers, anomalies | CoinGecko `/coins/markets` endpoint, free tier, single API call for top 100 |
| DISC-03 | Recommend new assets based on signal strength | Multi-trigger composite scoring with weighted combination |
| DISC-04 | "New Opportunities" section in daily report | Append discovery section to `send_daily_report` after news digest |
| DUED-01 | Sector benchmarking -- compare company metrics against sector median | Expand `IDX_SECTOR_MAP`, compute sector medians from `StockFundamental` table |
| DUED-02 | Ownership & insider analysis from IDX disclosure filings | httpx scraping of idx.co.id disclosure API, new `ownership_snapshots` table |
| DUED-03 | Management quality scoring (tenure, CAGR, capital allocation) | Computed from existing `FinancialData` table (revenue, ROE, net profit across periods) |
| DUED-04 | Competitive positioning (market share, moat indicators) | Sector-relative metrics from `StockFundamental` + `FinancialData` |
| LLM-06 | LLM considers due diligence flags | Add DD flags section to `_format_engine_data` in `src/llm/prompts.py` |
| TBOT-06 | `/discover` shows today's opportunities | New handler following `valuation_handler` pattern, reads from `discovery_candidates` table |
| TBOT-10 | `/compare BBCA BBRI BMRI` side-by-side sector comparison | New handler reading from `StockFundamental` + computing sector medians |
| TBOT-11 | `/duediligence BBCA` full DD report | New handler reading from DD tables, format like `/valuation` |
| REPT-07 | New opportunities discovered | Discovery section appended to daily report cards list |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| yfinance | >=1.2.0 | Bulk OHLCV download for ~900 IHSG stocks | Already in project deps, `yf.download()` supports multi-ticker batch |
| httpx | >=0.28.1 | IDX disclosure filing scraping, CoinGecko API | Already in project deps, async-capable, reuses Phase 9 patterns |
| numpy | (via pandas) | Statistical anomaly detection, Z-scores | Already available, used by BehavioralEngine |
| pandas | >=3.0.1 | DataFrame operations for screening calculations | Already in project deps |
| pandas-ta-classic | >=0.4.47 | RSI, MACD, Bollinger Bands for breakout detection | Already in project deps, used by TechnicalEngine |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| sqlalchemy | >=2.0.48 | ORM models for new tables, query building | All DB operations |
| structlog | >=25.5.0 | Logging throughout new modules | All new modules |
| python-telegram-bot | >=22.7 | Bot command handlers | New /discover, /duediligence, /compare handlers |

No new dependencies required. All libraries already exist in `pyproject.toml`.

## Architecture Patterns

### Recommended Project Structure
```
src/
├── data/
│   ├── discovery.py          # Discovery scanner (IDX + crypto scanning)
│   ├── ownership_fetcher.py  # IDX disclosure filing scraper
│   └── due_diligence.py      # DD computation (sector bench, mgmt quality, competitive pos)
├── bot/handlers/
│   ├── discover.py           # /discover command handler
│   ├── duediligence.py       # /duediligence command handler
│   └── compare.py            # /compare command handler
├── db/
│   ├── models.py             # New models: DiscoveryCandidate, OwnershipSnapshot, DueDiligenceReport
│   └── migrations/versions/
│       ├── 012_discovery_candidates.py
│       └── 013_ownership_due_diligence.py
├── llm/
│   └── prompts.py            # Enhanced with DD flags section
└── report/
    └── formatter.py          # New format_discovery_card, format_dd_report, format_compare_table
```

### Pattern 1: Discovery Scanner as Post-Pipeline Function
**What:** Discovery scanner runs after all per-asset stages complete, scanning the full market universe rather than just watchlist assets.
**When to use:** The scanner operates on ~900 IDX stocks + 100 crypto -- these are NOT watchlist assets, so it cannot use the per-asset StageFunc pattern.
**Example:**
```python
# In src/pipeline/main.py async_main():
# After runner.run_pipeline() and before send_daily_report():
try:
    async with async_session_factory() as session:
        discovery_results = await run_discovery_scan(session, run_date)
except Exception:
    logger.exception("discovery_scan_error")
    discovery_results = []

# Pass discovery_results to send_daily_report for "New Opportunities" section
```

### Pattern 2: Batch yfinance Download with Rate Limiting
**What:** Download OHLCV for ~900 IHSG tickers in batches of 80 with inter-batch delays.
**When to use:** IDX discovery scanning.
**Example:**
```python
import yfinance as yf
import asyncio

BATCH_SIZE = 80
BATCH_DELAY = 3.0  # seconds between batches

async def _fetch_idx_screening_data(tickers: list[str]) -> pd.DataFrame:
    """Fetch last 30 days of OHLCV for all IHSG stocks in batches."""
    all_data = []
    for i in range(0, len(tickers), BATCH_SIZE):
        batch = tickers[i:i + BATCH_SIZE]
        # yfinance download is synchronous -- wrap in executor
        df = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda b=batch: yf.download(
                b, period="1mo", group_by="ticker", threads=True
            ),
        )
        all_data.append(df)
        if i + BATCH_SIZE < len(tickers):
            await asyncio.sleep(BATCH_DELAY)
    return pd.concat(all_data, axis=1) if all_data else pd.DataFrame()
```

### Pattern 3: CoinGecko Free-Tier Market Scan
**What:** Single API call to get top 100 crypto with price changes and volume.
**When to use:** Crypto discovery scanning.
**Example:**
```python
COINGECKO_MARKETS_URL = "https://api.coingecko.com/api/v3/coins/markets"

async def _fetch_crypto_screening_data() -> list[dict]:
    """Fetch top 100 crypto by market cap with 24h/7d changes."""
    params = {
        "vs_currency": "usd",
        "order": "market_cap_desc",
        "per_page": 100,
        "page": 1,
        "sparkline": "false",
        "price_change_percentage": "24h,7d",
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(COINGECKO_MARKETS_URL, params=params)
        resp.raise_for_status()
        return resp.json()
```

### Pattern 4: Bot Handler Following /valuation Template
**What:** New Telegram commands follow the established handler pattern: auth check, symbol parsing, async DB session, crypto rejection for DD commands, format with HTML parse_mode.
**When to use:** All three new commands.
**Example:**
```python
# src/bot/handlers/duediligence.py
async def duediligence_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_authorized(update):
        return
    if not context.args:
        await update.message.reply_text("Please specify an IDX stock symbol.", parse_mode="HTML")
        return
    symbol = context.args[0].upper()
    async with async_session_factory() as session:
        # Resolve asset (may or may not be on watchlist -- DD works for any IDX stock)
        asset = await _resolve_idx_asset(session, symbol)
        if asset is None:
            # ...
            return
        if asset.asset_type == "crypto":
            # "not applicable" per D-11
            return
        # Read DD data from DB tables
        dd_data = await _load_dd_data(session, asset)
        msg = format_dd_report(asset.symbol, asset.name, dd_data)
    await update.message.reply_text(msg, parse_mode="HTML")
```

### Pattern 5: DD Flags in LLM Decision Prompt
**What:** Add a "DUE DILIGENCE FLAGS" section to the LLM prompt after engine signals, before lessons.
**When to use:** When DD data exists for a stock asset being decided on.
**Example:**
```python
# Added to _format_engine_data in src/llm/prompts.py:
if dd_flags:
    lines.append("")
    lines.append("DUE DILIGENCE FLAGS:")
    for flag in dd_flags:
        severity = flag.get("severity", "info")  # warning, alert, info
        lines.append(f"  [{severity.upper()}] {flag['message']}")
```

### Anti-Patterns to Avoid
- **Running discovery as a StageFunc:** The scanner processes ~1000 assets that are not on the watchlist. StageFunc iterates over watchlist assets only. Use a post-pipeline function instead.
- **Downloading all 900 tickers at once:** yfinance will hit rate limits. Must batch with delays.
- **Importing pipeline modules from bot:** The two-process boundary must be maintained. Bot reads discovery results from DB, never imports scanner code.
- **Running full 15-engine analysis on discovered assets:** Per D-04, scanner uses lightweight screening criteria only. Full analysis happens only after user adds to watchlist.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Volume spike detection | Custom Z-score calculation | Reuse logic from `BehavioralEngine._analyze_impl()` | Already has 20-day mean/std Z-score calculation (lines 72-79) |
| RSI/MACD/Bollinger for breakouts | Custom TA indicators | pandas-ta-classic via `.ta` accessor | Already used by TechnicalEngine, production-tested |
| Sector classification mapping | Manual dictionary per ticker | Expand existing `IDX_SECTOR_MAP` in `src/engines/valuation.py` | Already started with 15 tickers, extend to full universe |
| Telegram message formatting | Raw HTML strings | Extend `src/report/formatter.py` functions | Maintains consistent card style, handles 4096-char splitting |
| IDX web scraping | Custom HTTP client setup | Reuse `httpx.AsyncClient` pattern from `idx_doc_fetcher.py` | Headers, timeouts, rate limiting already configured |

**Key insight:** Phase 11 is a composition phase -- most building blocks already exist. The volume anomaly detection logic, TA indicator calculation, IDX scraping patterns, bot handler architecture, and LLM prompt structure are all established. The work is connecting these pieces to new data sources and presenting results through new interfaces.

## Common Pitfalls

### Pitfall 1: yfinance Rate Limiting on ~900 Tickers
**What goes wrong:** Downloading all IHSG tickers triggers Yahoo Finance 429 errors, blocking the IP.
**Why it happens:** Yahoo Finance enforces ~360 requests/hour. 900 individual ticker downloads exceed this.
**How to avoid:** Use `yf.download()` with multi-ticker batch (passes list of tickers, not individual calls). Batch into groups of 80. Add 2-3 second delays between batches. Total scan time: ~35 seconds for 12 batches.
**Warning signs:** `YFRateLimitError` exceptions, empty DataFrames returned.

### Pitfall 2: CoinGecko Free Tier Rate Limits
**What goes wrong:** CoinGecko free tier allows only 30 calls/minute. Multiple calls in the same pipeline run may be throttled.
**Why it happens:** The pipeline already uses CoinGecko for crypto OHLCV fallback and metadata.
**How to avoid:** The discovery scan needs only ONE call to `/coins/markets` for all 100 coins. Ensure this runs before or after the ingest stage's CoinGecko calls, not concurrently. Add the standard 1s delay.
**Warning signs:** 429 responses, empty results.

### Pitfall 3: IDX Disclosure Filing Scraping Fragility
**What goes wrong:** IDX website structure changes break the scraper, or endpoints return unexpected HTML.
**Why it happens:** idx.co.id is not an official API -- it's an internal endpoint exposed through the website.
**How to avoid:** Implement graceful degradation per D-06 pattern. If ownership data is unavailable, DD report shows "Ownership data: unavailable" rather than crashing. Use weekly refresh cycle (D-12) to limit scraping frequency. Add User-Agent header matching `idx_doc_fetcher.py`.
**Warning signs:** HTTP 403/404 responses, HTML returned instead of JSON.

### Pitfall 4: Discovery Scanner Blocking Pipeline Completion
**What goes wrong:** Scanning 900 stocks takes too long and delays the daily report.
**Why it happens:** Network failures, rate limiting, or slow data processing.
**How to avoid:** Set a hard timeout on the discovery scan (e.g., 300 seconds). If it times out, proceed with the daily report without the "New Opportunities" section. Log the timeout but don't fail the pipeline.
**Warning signs:** Pipeline runs taking >10 minutes, missing daily reports.

### Pitfall 5: Sector Map Incomplete for Full IHSG Universe
**What goes wrong:** The current `IDX_SECTOR_MAP` has only 15 tickers. Sector benchmarking and `/compare` fail for unmapped tickers.
**Why it happens:** Phase 9 only mapped watchlist stocks.
**How to avoid:** Fetch IDX sector classification from idx.co.id stock list API (which returns sector/subsector for all listed companies). Store in DB and refresh weekly. Fall back to "Unknown" sector if mapping unavailable.
**Warning signs:** Empty sector benchmarks, `/compare` returning incomplete data.

### Pitfall 6: DD Data Missing for Non-Watchlist Assets
**What goes wrong:** User calls `/duediligence` for a stock not on their watchlist, but DD data was only computed for watchlist stocks.
**Why it happens:** Pipeline stages only run for watchlist assets.
**How to avoid:** DD data (sector benchmarking, management quality) should be computable on-demand from StockFundamental data. For ownership data, the weekly scraper should cover all stocks that have ever been queried via `/duediligence`, not just watchlist stocks. Store a "DD interest" flag or expand the Asset table.
**Warning signs:** "No DD data available" for valid IDX stocks.

## Code Examples

### Composite Discovery Score
```python
# Recommended weights for multi-trigger composite scoring (D-06)
TRIGGER_WEIGHTS = {
    "volume_spike": 0.30,    # >2x 20-day avg volume
    "price_breakout": 0.30,  # 52-week high, resistance break, Bollinger squeeze
    "momentum_surge": 0.25,  # RSI crossover, MACD signal cross
    "statistical_anomaly": 0.15,  # Z-score based anomaly
}

def compute_composite_score(triggers: dict[str, float]) -> float:
    """Compute weighted composite score from individual trigger scores.

    Each trigger score is 0.0-1.0 (signal strength).
    Multiple triggers boost overall score.
    """
    score = sum(
        triggers.get(t, 0.0) * w
        for t, w in TRIGGER_WEIGHTS.items()
    )
    # Bonus for multiple triggers (D-06)
    active_triggers = sum(1 for v in triggers.values() if v > 0.0)
    if active_triggers >= 3:
        score *= 1.3  # 30% bonus for 3+ triggers
    elif active_triggers >= 2:
        score *= 1.15  # 15% bonus for 2 triggers
    return min(score, 1.0)
```

### Management Quality Score from FinancialData
```python
def compute_management_quality(
    financial_data: list[dict],  # from FinancialData table, sorted by period_date
) -> dict[str, float | str]:
    """Compute management quality score from 3-5 year financial track record.

    Components (D-09):
    - Revenue CAGR (40% weight)
    - ROE trend (30% weight)
    - Capital allocation efficiency (30% weight)
    """
    if len(financial_data) < 4:  # Need at least 4 quarters
        return {"score": 0.0, "label": "Insufficient data", "detail": {}}

    revenues = [(d["period_date"], d["value"]) for d in financial_data if d["metric"] == "revenue"]
    roes = [(d["period_date"], d["value"]) for d in financial_data if d["metric"] == "roe"]

    # Revenue CAGR
    if len(revenues) >= 2:
        years = (revenues[-1][0] - revenues[0][0]).days / 365.25
        if years > 0 and revenues[0][1] > 0:
            cagr = (revenues[-1][1] / revenues[0][1]) ** (1 / years) - 1
        else:
            cagr = 0.0
    else:
        cagr = 0.0

    # Score: 0-1 based on CAGR (15%+ = 1.0, negative = 0.0)
    cagr_score = max(0.0, min(1.0, cagr / 0.15))

    # ROE trend: positive slope = good
    roe_score = 0.5  # default neutral
    if len(roes) >= 4:
        recent_avg = sum(r[1] for r in roes[-4:]) / 4
        roe_score = max(0.0, min(1.0, recent_avg / 20.0))  # 20% ROE = perfect

    # Capital allocation: net_profit / total_equity trend
    cap_score = 0.5  # default

    total = cagr_score * 0.4 + roe_score * 0.3 + cap_score * 0.3
    label = "Excellent" if total > 0.7 else "Good" if total > 0.5 else "Fair" if total > 0.3 else "Weak"

    return {
        "score": round(total, 2),
        "label": label,
        "detail": {"revenue_cagr": round(cagr * 100, 1), "roe_score": round(roe_score, 2)},
    }
```

### New DB Models
```python
class DiscoveryCandidate(Base):
    """Daily discovery scan results -- top candidates from market screening."""
    __tablename__ = "discovery_candidates"
    __table_args__ = (
        UniqueConstraint("scan_date", "symbol", name="uq_discovery_date_symbol"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    scan_date: Mapped[date] = mapped_column(Date, nullable=False)
    symbol: Mapped[str] = mapped_column(String(20), nullable=False)
    asset_type: Mapped[str] = mapped_column(String(10), nullable=False)  # "stock" or "crypto"
    composite_score: Mapped[float] = mapped_column(Float, nullable=False)
    triggers: Mapped[dict] = mapped_column(JSONB, nullable=False)
    # triggers: {"volume_spike": 0.8, "price_breakout": 0.6, ...}
    current_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    price_change_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    volume_ratio: Mapped[float | None] = mapped_column(Float, nullable=True)  # today/20d avg
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class OwnershipSnapshot(Base):
    """Shareholder composition snapshot from IDX disclosure filings."""
    __tablename__ = "ownership_snapshots"
    __table_args__ = (
        UniqueConstraint("asset_id", "snapshot_date", name="uq_ownership_asset_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    asset_id: Mapped[int] = mapped_column(Integer, ForeignKey("assets.id"), nullable=False)
    snapshot_date: Mapped[date] = mapped_column(Date, nullable=False)
    shareholders: Mapped[dict] = mapped_column(JSONB, nullable=False)
    # {"shareholders": [{"name": "...", "pct": 25.3}, ...], "public_float": 45.2}
    total_shares: Mapped[float | None] = mapped_column(Float, nullable=True)
    public_float_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class DueDiligenceReport(Base):
    """Computed due diligence report for IDX stocks (cached weekly)."""
    __tablename__ = "due_diligence_reports"
    __table_args__ = (
        UniqueConstraint("asset_id", "report_date", name="uq_dd_asset_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    asset_id: Mapped[int] = mapped_column(Integer, ForeignKey("assets.id"), nullable=False)
    report_date: Mapped[date] = mapped_column(Date, nullable=False)
    sector: Mapped[str | None] = mapped_column(String(30), nullable=True)
    sector_rank: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    # {"pe_vs_median": -15.2, "roe_vs_median": 8.3, "rank": 3, "of": 12}
    management_quality: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    # {"score": 0.72, "label": "Good", "revenue_cagr": 12.3, ...}
    ownership_changes: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    # {"major_changes": [...], "public_float_change": -2.1}
    competitive_position: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    # {"market_position": "leader", "moat_indicators": [...]}
    dd_flags: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    # [{"type": "insider_selling", "severity": "warning", "message": "..."}]
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
```

### Discovery Card Formatting
```python
# Trigger type icons for discovery cards (D-14)
TRIGGER_ICONS = {
    "volume_spike": "\U0001f4c8",     # chart increasing
    "price_breakout": "\U0001f680",   # rocket
    "momentum_surge": "\u26a1",       # lightning
    "statistical_anomaly": "\U0001f50d",  # magnifying glass
}

def format_discovery_card(
    symbol: str,
    asset_type: str,
    composite_score: float,
    triggers: dict[str, float],
    current_price: float,
    price_change_pct: float,
) -> str:
    """Format a compact discovery opportunity card.

    {icons} <b>{SYMBOL}</b> ({type})
       Score: {0.85} | Price: {Rp 8,450} ({+3.2%})
       Triggers: Volume 2.5x | Breakout | MACD cross
    """
    active = [t for t, v in triggers.items() if v > 0.0]
    icons = "".join(TRIGGER_ICONS.get(t, "") for t in active)

    trigger_labels = {
        "volume_spike": f"Vol {triggers.get('volume_spike', 0):.1f}x",
        "price_breakout": "Breakout",
        "momentum_surge": "Momentum",
        "statistical_anomaly": "Anomaly",
    }
    trigger_str = " | ".join(trigger_labels[t] for t in active if t in trigger_labels)

    sign = "+" if price_change_pct >= 0 else ""
    return (
        f"{icons} <b>{html.escape(symbol)}</b> ({asset_type})\n"
        f"   Score: {composite_score:.2f} | {sign}{price_change_pct:.1f}%\n"
        f"   {trigger_str}"
    )
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| IDX ownership disclosure >5% only | IDX ownership disclosure >1% | March 2026 | More granular shareholder data available for DD analysis |
| yfinance no rate limiting | yfinance aggressive rate limiting (360 req/hr) | Late 2025 | Must batch downloads, cannot fetch individually |
| CoinGecko top movers (paid only) | `/coins/markets` free tier with price_change_percentage | Available | Free tier sufficient for discovery scan |

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2+ with pytest-asyncio |
| Config file | `pyproject.toml` under `[tool.pytest.ini_options]` |
| Quick run command | `pytest tests/ -x --tb=short` |
| Full suite command | `pytest tests/` |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| DISC-01 | IDX volume spike + breakout detection | unit | `pytest tests/test_data/test_discovery.py -x` | Wave 0 |
| DISC-02 | Crypto top mover scanning | unit | `pytest tests/test_data/test_discovery.py::TestCryptoScanner -x` | Wave 0 |
| DISC-03 | Composite score ranking | unit | `pytest tests/test_data/test_discovery.py::TestCompositeScore -x` | Wave 0 |
| DISC-04 | New Opportunities report section | unit | `pytest tests/test_report/test_formatter_discovery.py -x` | Wave 0 |
| DUED-01 | Sector benchmarking computation | unit | `pytest tests/test_data/test_due_diligence.py::TestSectorBenchmark -x` | Wave 0 |
| DUED-02 | Ownership snapshot parsing | unit | `pytest tests/test_data/test_ownership_fetcher.py -x` | Wave 0 |
| DUED-03 | Management quality scoring | unit | `pytest tests/test_data/test_due_diligence.py::TestManagementQuality -x` | Wave 0 |
| DUED-04 | Competitive positioning | unit | `pytest tests/test_data/test_due_diligence.py::TestCompetitivePosition -x` | Wave 0 |
| LLM-06 | DD flags in LLM prompt | unit | `pytest tests/test_llm/test_prompts.py -x` | Wave 0 |
| TBOT-06 | /discover handler | unit | `pytest tests/test_bot/test_discover_handler.py -x` | Wave 0 |
| TBOT-10 | /compare handler | unit | `pytest tests/test_bot/test_compare_handler.py -x` | Wave 0 |
| TBOT-11 | /duediligence handler | unit | `pytest tests/test_bot/test_dd_handler.py -x` | Wave 0 |
| REPT-07 | Discovery section in report | unit | `pytest tests/test_report/test_formatter_discovery.py -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/ -x --tb=short`
- **Per wave merge:** `pytest tests/`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_data/test_discovery.py` -- covers DISC-01, DISC-02, DISC-03
- [ ] `tests/test_data/test_due_diligence.py` -- covers DUED-01, DUED-03, DUED-04
- [ ] `tests/test_data/test_ownership_fetcher.py` -- covers DUED-02
- [ ] `tests/test_bot/test_discover_handler.py` -- covers TBOT-06
- [ ] `tests/test_bot/test_dd_handler.py` -- covers TBOT-11
- [ ] `tests/test_bot/test_compare_handler.py` -- covers TBOT-10
- [ ] `tests/test_report/test_formatter_discovery.py` -- covers DISC-04, REPT-07
- [ ] `tests/test_llm/test_prompts.py` -- extend existing with DD flags test (LLM-06)

## Open Questions

1. **IDX Disclosure Filing API Endpoint Structure**
   - What we know: idx.co.id has a disclosure section and shareholder data is now publicly available for >1% holdings since March 2026. The IDX-BEI scraper project shows endpoint patterns exist.
   - What's unclear: Exact URL structure and response format for shareholder composition API. May require HTML scraping rather than JSON API.
   - Recommendation: Implement with graceful degradation. Try JSON endpoint first, fall back to HTML parsing, fall back to "unavailable" if both fail. Weekly refresh limits exposure to scraping fragility.

2. **IHSG Full Ticker List Source**
   - What we know: IDX has `GetStockData` or `GetConstituent` endpoints. The idx-bei scraper fetches all listed companies.
   - What's unclear: Whether the endpoint returns all ~900 tickers or just active ones, and what format sector classification comes in.
   - Recommendation: Fetch ticker list from IDX on startup or weekly, cache in a `idx_tickers` table or simple JSON file. Use the sector/subsector data returned for sector mapping.

3. **Sector Map Expansion Strategy**
   - What we know: Current `IDX_SECTOR_MAP` has 15 entries. Full IHSG has ~900 stocks across ~12 sectors.
   - What's unclear: Whether IDX API provides standardized sector classification for all stocks.
   - Recommendation: Fetch from IDX API and store in DB. Fall back to yfinance `.info['sector']` for unmapped stocks. Allow manual overrides via the existing hardcoded map.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| yfinance | IDX discovery scan | Already installed | >=1.2.0 | -- |
| httpx | IDX disclosure scraping, CoinGecko | Already installed | >=0.28.1 | -- |
| pandas-ta-classic | Breakout detection (RSI, MACD, BB) | Already installed | >=0.4.47 | -- |
| CoinGecko free API | Crypto discovery scan | External service | Free tier | Skip crypto discovery if unavailable |
| idx.co.id | Ownership data, ticker list | External service | Web API | DD reports show "unavailable" for ownership section |

**Missing dependencies with no fallback:** None
**Missing dependencies with fallback:** CoinGecko and idx.co.id are external services that may be temporarily unavailable -- all code must degrade gracefully.

## Sources

### Primary (HIGH confidence)
- Existing codebase: `src/engines/behavioral.py` -- volume anomaly Z-score pattern (lines 72-79)
- Existing codebase: `src/data/idx_doc_fetcher.py` -- IDX httpx scraping pattern
- Existing codebase: `src/bot/handlers/valuation.py` -- bot handler template
- Existing codebase: `src/llm/prompts.py` -- LLM decision prompt structure
- Existing codebase: `src/pipeline/main.py` -- pipeline stage wiring, post-pipeline functions

### Secondary (MEDIUM confidence)
- [CoinGecko /coins/markets API docs](https://docs.coingecko.com/reference/coins-markets) -- free tier, top 100 by market cap
- [yfinance batch download patterns](https://github.com/ranaroussi/yfinance) -- `yf.download()` multi-ticker
- [yfinance rate limiting](https://github.com/ranaroussi/yfinance/issues/2614) -- batch size ~80, 360 req/hr limit
- [IDX disclosure changes March 2026](https://investasi.kontan.co.id/news/klik-idxcoididberita-publik-bisa-lihat-investor-kakap-pemegang-saham-di-atas-1) -- ownership >1% now public

### Tertiary (LOW confidence)
- IDX API endpoint structure (`GetConstituent`, `GetStockData`) -- inferred from third-party scrapers, needs validation against live endpoint

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- all libraries already in project, no new dependencies needed
- Architecture: HIGH -- patterns well-established from Phases 5, 8, 9, 10 (bot handlers, post-pipeline functions, IDX scraping)
- Discovery scanner: MEDIUM-HIGH -- yfinance batch download is well-documented; rate limiting strategy validated by community
- Due diligence data: MEDIUM -- IDX disclosure filing API structure needs runtime validation; management quality formula is straightforward computation on existing data
- Pitfalls: HIGH -- rate limiting issues well-documented, graceful degradation pattern established in project

**Research date:** 2026-03-26
**Valid until:** 2026-04-26 (30 days -- stable domain, established patterns)
