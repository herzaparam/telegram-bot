# Phase 11: Asset Discovery + Due Diligence - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-03-26
**Phase:** 11-asset-discovery-due-diligence
**Areas discussed:** Discovery scanning scope, Due diligence data sources, Telegram command design, Opportunity ranking & LLM integration

---

## Discovery Scanning Scope

### IHSG Scan Breadth

| Option | Description | Selected |
|--------|-------------|----------|
| All IHSG stocks (~900) | Full IDX universe daily via yfinance bulk fetch | ✓ |
| LQ45 + IDX80 (~100) | Liquid stocks only, faster scan | |
| Tiered: liquid daily, full weekly | LQ45 daily, full IHSG weekly | |

**User's choice:** All IHSG stocks (~900)

### Discovery Triggers

| Option | Description | Selected |
|--------|-------------|----------|
| Volume spike (>2x avg) | Unusual trading volume vs 20-day average | ✓ |
| Price breakout | 52-week high, resistance break, Bollinger breakout | ✓ |
| Momentum surge | RSI crossing, MACD crossover, price acceleration | ✓ |
| Anomaly detection | Statistical outliers in price/volume patterns | ✓ |

**User's choice:** All four trigger types selected

### Crypto Discovery Universe

| Option | Description | Selected |
|--------|-------------|----------|
| Top 100 by market cap | CoinGecko top 100, major and mid-cap tokens | ✓ |
| Top 250 by market cap | Deeper into smaller-cap tokens | |
| Binance-listed only | Only coins on Binance (ccxt integrated) | |

**User's choice:** Top 100 by market cap

### Report Presentation

| Option | Description | Selected |
|--------|-------------|----------|
| Top 5 ranked cards | Compact cards matching existing report style | ✓ |
| Categorized sections | Grouped by trigger type | |
| Single summary table | Dense table with all discoveries | |

**User's choice:** Top 5 ranked cards

---

## Due Diligence Data Sources

### Insider/Ownership Data Source

| Option | Description | Selected |
|--------|-------------|----------|
| IDX disclosure filings | Scrape idx.co.id, reuse httpx patterns from Phase 9 | ✓ |
| yfinance institutional holders | Less detailed but no new scraping | |
| Both sources combined | IDX for insider, yfinance for institutional | |

**User's choice:** IDX disclosure filings (Recommended)

### Management Quality Assessment

| Option | Description | Selected |
|--------|-------------|----------|
| Financial track record only | Revenue CAGR, ROE trend, capital allocation over 3-5 years | ✓ |
| Track record + LLM analysis | Financial metrics plus LLM reads management discussion | |
| Lightweight proxy metrics | Dividend growth, debt reduction, margin expansion heuristics | |

**User's choice:** Financial track record only

### Sector Benchmarking

| Option | Description | Selected |
|--------|-------------|----------|
| Sector median comparison | Compare against IDX sector median, highlight above/below | ✓ |
| Top-5 peer comparison | Side-by-side with 5 closest peers by market cap | |
| Both: median + peers | Sector median plus top-5 peers | |

**User's choice:** Sector median comparison

### DD Scope (Asset Types)

| Option | Description | Selected |
|--------|-------------|----------|
| IDX stocks only | DD concepts are equity-specific, crypto gets "not applicable" | ✓ |
| IDX stocks + crypto basics | Stocks full DD, crypto lightweight (token distribution, team) | |

**User's choice:** IDX stocks only (Recommended)

### DD Refresh Frequency

| Option | Description | Selected |
|--------|-------------|----------|
| Weekly | Matches Phase 9 weekly pattern, insider disclosures periodic | ✓ |
| Daily | Check every pipeline run | |
| On-demand only | Only when user runs /duediligence | |

**User's choice:** Weekly (Recommended)

### DD Alert Behavior

| Option | Description | Selected |
|--------|-------------|----------|
| Report + commands only | DD flags in daily report and /duediligence only | ✓ |
| Push alert for major flags | Immediate Telegram for significant insider selling | |

**User's choice:** Report + commands only (Recommended)

### Sector Classification Source

| Option | Description | Selected |
|--------|-------------|----------|
| IDX sector classification | IDX's own groupings (Banking, Telco, etc.) | ✓ |
| yfinance sector/industry | GICS classification for .JK tickers | |
| Manual mapping table | Static ticker-to-sector mapping in DB | |

**User's choice:** IDX sector classification (Recommended)

### Ownership Data Depth

| Option | Description | Selected |
|--------|-------------|----------|
| Shareholder composition + changes | Top shareholders %, QoQ changes, flag significant moves | ✓ |
| Full insider transaction log | Individual buy/sell transactions with dates/amounts | |
| Both composition and transactions | Most complete | |

**User's choice:** Shareholder composition + changes

---

## Telegram Command Design

### /discover Format

| Option | Description | Selected |
|--------|-------------|----------|
| Compact cards | Ticker, trigger icon, signal strength, price+change% | ✓ |
| Summary table | Dense table with all discoveries | |
| Detailed per-asset | Mini-report per opportunity | |

**User's choice:** Compact cards (Recommended)

### /duediligence Depth

| Option | Description | Selected |
|--------|-------------|----------|
| Single comprehensive message | All DD in one message, compact like /valuation | ✓ |
| Multi-section with pagination | 3-4 separate messages per section | |
| Summary + deep dive option | Short summary, reply for details | |

**User's choice:** Single comprehensive message

### /compare Layout

| Option | Description | Selected |
|--------|-------------|----------|
| Side-by-side metrics table | Tickers as columns, metrics as rows, best/worst highlighted | ✓ |
| Per-metric comparison cards | Grouped by metric category | |
| Ranked leaderboard | Position indicators per metric | |

**User's choice:** Side-by-side metrics table

### /compare Scope

| Option | Description | Selected |
|--------|-------------|----------|
| IDX stocks only | Fundamental metrics are equity-specific | ✓ |
| Both stocks and crypto | Different metric sets per asset type | |

**User's choice:** IDX stocks only (Recommended)

---

## Opportunity Ranking & LLM Integration

### Ranking Method

| Option | Description | Selected |
|--------|-------------|----------|
| Multi-trigger composite score | Weight trigger types, combine into single score | ✓ |
| Strongest single trigger | Rank by most significant trigger per asset | |
| LLM-ranked | Quick LLM pass to rank by opportunity quality | |

**User's choice:** Multi-trigger composite score (Recommended)

### DD Flags in LLM

| Option | Description | Selected |
|--------|-------------|----------|
| Include in LLM prompt context | Add DD flags as additional context section | ✓ |
| Pre-filter before LLM | Adjust engine scores before LLM sees them | |
| Separate DD verdict | Independent DD assessment alongside signal verdict | |

**User's choice:** Include in LLM prompt context (Recommended)

### Scan Depth for Discoveries

| Option | Description | Selected |
|--------|-------------|----------|
| Screening criteria only | Lightweight checks, full engines only on watchlist add | ✓ |
| Run technical engine on candidates | Quick TechnicalEngine on top candidates | |
| Full engine suite on top 10 | All engines on top 10 discoveries | |

**User's choice:** Screening criteria only (Recommended)

### /discover Filtering

| Option | Description | Selected |
|--------|-------------|----------|
| No filter, show top 5 overall | Simple /discover, no arguments | ✓ |
| /discover breakouts for filtered view | Optional trigger type argument | |

**User's choice:** No filter, show top 5 overall (Recommended)

---

## Claude's Discretion

- Discovery scanner batch sizes and rate limiting
- Composite score weights for trigger types
- Volume spike/breakout/momentum thresholds
- Anomaly detection statistical method
- IDX disclosure scraping implementation
- Sector classification mapping maintenance
- Management quality score formula
- DD flag severity levels
- New DB tables schema
- Alembic migrations
- Error handling and graceful degradation
- Telegram formatting and icons

## Deferred Ideas

None — discussion stayed within phase scope
