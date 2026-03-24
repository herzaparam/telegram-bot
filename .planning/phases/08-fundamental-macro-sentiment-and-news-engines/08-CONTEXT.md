# Phase 8: Fundamental, Macro, Sentiment, and News Engines - Context

**Gathered:** 2026-03-24
**Status:** Ready for planning

<domain>
## Phase Boundary

Four additional engines deepen signal quality: fundamentals for IDX stocks, macro context for both asset classes, sentiment from social sources, and news-driven event signals. Also includes news ingestion (Indonesian RSS + Finnhub), LLM-based news impact scoring, and a daily news digest in the Telegram report. Covers: FundamentalEngine, MacroEngine, SentimentEngine, EventEngine, macro data fetcher, news fetcher (RSS + Finnhub), sentiment fetcher (Fear & Greed + Reddit), news_events table migration, macro_data table migration, LLM news analyzer, daily report news section. Does NOT include: on-chain engine (Phase 10), ML/AI engine (Phase 10), IDX PDF parsing (Phase 9), valuation engine (Phase 9), or remaining specialized engines (Phase 10).

</domain>

<decisions>
## Implementation Decisions

### Fundamental Engine — Data Source
- **D-01:** Use yfinance `.info` dict as the sole data source for IDX stock fundamentals (P/E, P/B, revenue growth, ROE, dividend yield, debt/equity)
- **D-02:** Cache fundamentals in a new `stock_fundamentals` table. Weekly refresh — skip fetch if data is <7 days old
- **D-03:** For crypto assets, return score=0/confidence=0 with reasoning "Fundamentals not applicable for crypto" (not supports_crypto=False — keep engine visible to LLM)
- **D-04:** Six ratios: P/E, P/B, revenue growth, ROE, dividend yield, and debt/equity. Zone-map each ratio to a sub-score (-1 to +1), combine via weighted average (same pattern as TechnicalEngine)

### Macro Engine — Architecture
- **D-05:** Fetch-then-cache pattern: new macro fetcher runs during fetch stage, stores macro indicators in a new `macro_data` table. MacroEngine.analyze() reads cached macro data from DB (not the price DataFrame). Same BaseEngine contract preserved
- **D-06:** FRED as the sole macro data source — covers Fed funds rate, US CPI, DXY index, and USD/IDR exchange rate. Single API, free, well-documented `fredapi` library. No Bank Indonesia or World Bank APIs needed
- **D-07:** One global macro score per pipeline run. Reasoning highlights IDX-relevant factors (BI rate proxy, rupiah via USD/IDR) for stocks and global factors (Fed rate, DXY, risk appetite) for crypto. LLM interprets the contextual difference
- **D-08:** FRED API key required — add `FRED_API_KEY` to Settings and .env

### Sentiment Engine — Sources & Method
- **D-09:** Two sentiment sources: Crypto Fear & Greed Index (alternative.me, free, no auth) + Reddit via PRAW (r/cryptocurrency for crypto, r/finansial for IDX stocks). Skip Stockbit scraping — too fragile
- **D-10:** Reddit sentiment analyzed via LLM batch call: fetch top ~20 posts per subreddit daily, one LLM call per subreddit, returns sentiment score per mentioned asset. Uses existing `llm_completion()` with JSON mode. ~$0.02/day
- **D-11:** Reddit API keys needed — add `REDDIT_CLIENT_ID` and `REDDIT_CLIENT_SECRET` to Settings and .env. User will register a Reddit app
- **D-12:** Graceful degradation: if Reddit API unavailable, engine still produces a score from Fear & Greed alone with lowered confidence

### News Ingestion & LLM Scoring
- **D-13:** News fetchers (RSS for Indonesian + Finnhub for global) run as part of the existing fetch stage, alongside price and macro fetchers. News is global data, cached in `news_events` table
- **D-14:** Batch LLM scoring: collect all today's headlines (RSS + Finnhub), send in one LLM call with the watchlist. LLM returns impact_score + affected_assets + category per headline. ~$0.03/day. Matches ARCHITECTURE.md news_analyzer flow
- **D-15:** Indonesian news from three RSS feeds: Kontan (rss.kontan.co.id), CNBC Indonesia (cnbcindonesia.com/news/rss), Bisnis (bisnis.com/rss) via `feedparser` library
- **D-16:** Global crypto/financial news from Finnhub REST API. Free tier (60 calls/min, plenty for daily batch). User will register for API key — add `FINNHUB_API_KEY` to Settings and .env

### Event Engine — Design
- **D-17:** EventEngine reads from `news_events` table (populated by news fetchers + LLM scoring). Signals upcoming earnings, BI rate meetings, and crypto halvings based on news category tags (central_bank, earnings, etc.)
- **D-18:** Event engine is news-derived, not calendar-based — events surface through LLM classification of news headlines rather than maintaining a static event calendar

### Daily Report — News Section
- **D-19:** Separate "News & Events" section at the bottom of the daily report. Top 5-10 high-impact headlines grouped by category (central_bank, earnings, regulation). Each shows headline + source + affected assets + impact direction
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

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Architecture & Engine Interface
- `plan/ARCHITECTURE.md` — Full system architecture, all 15 engine categories, news_events table schema, news analyzer flow, data source table with rate limits and libraries, LLM cost estimates
- `plan/ARCHITECTURE.md` §Database Schema — `news_events` table definition (headline, source, url, impact_score, affected_assets JSONB, category, raw_content)
- `plan/ARCHITECTURE.md` §Data Sources — RSS feeds (Kontan, CNBC ID, Bisnis), Finnhub, FRED, alternative.me Fear & Greed, Reddit PRAW, data tier classifications
- `plan/ARCHITECTURE.md` §News Analyzer Flow — LLM prompt design for per-headline impact scoring with affected assets and categories
- `plan/ARCHITECTURE.md` §Project Structure — Planned file layout: `src/data/news_id.py`, `src/data/news_global.py`, `src/data/macro_global.py`, `src/data/sentiment.py`, `src/engines/fundamental.py`, `src/engines/sentiment.py`, `src/engines/macro.py`, `src/llm/news_analyzer.py`

### Existing Engine Pattern (Phase 3 foundation)
- `src/engines/base.py` — BaseEngine ABC, Signal dataclass (frozen), category property, supports_stocks/supports_crypto
- `src/engines/technical.py` — TechnicalEngine implementation with zone-mapping and weighted average scoring pattern to replicate
- `src/engines/quantitative.py` — QuantitativeEngine with graceful degradation pattern
- `src/data/analyze.py` — `_get_engines_for_asset()`, `_failed_signal()`, `analyze_stage()` StageFunc — new engines plug in here

### Data & Pipeline Infrastructure
- `src/data/ingest.py` — Existing fetch stage StageFunc; macro and news fetchers should follow this pattern
- `src/data/idx_stocks.py` — IDXStockFetcher pattern (yfinance wrapped in run_in_executor) for fundamental data fetch
- `src/data/crypto.py` — CryptoFetcher with fallback pattern
- `src/pipeline/runner.py` — PipelineRunner with StageFunc interface, per-asset timeout handling
- `src/pipeline/tiers.py` — Data tier classification: macro_data = IMPORTANT, news_sentiment = SUPPLEMENTARY, social_metrics = SUPPLEMENTARY

### LLM Infrastructure
- `src/llm/client.py` — `llm_completion()` with JSON mode, retry, fallback. Used for Reddit sentiment analysis and news impact scoring
- `src/llm/prompts.py` — Prompt builder patterns

### Report Infrastructure
- `src/report/formatter.py` — Shared formatter for daily report. Add news digest section here
- `src/bot/handlers/report.py` — Report command handlers

### Configuration
- `src/config.py` — Settings class to extend with FRED_API_KEY, FINNHUB_API_KEY, REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET
- `src/db/models.py` — Existing ORM models; add news_events, macro_data, stock_fundamentals models

### Prior Phase Context
- `.planning/phases/03-technical-engine-pipeline-shell/03-CONTEXT.md` — BaseEngine contract, Signal dataclass, zone-mapping scoring, weighted average, indicator weights in pydantic-settings
- `.planning/phases/07-self-evaluation-feedback-loop/07-CONTEXT.md` — Lessons feed into LLM decisions, reflect stage ordering

### Requirements
- `.planning/REQUIREMENTS.md` — ENGN-02 (fundamental), ENGN-05 (sentiment), ENGN-09 (event-driven), ENGN-12 (macro), NEWS-01 through NEWS-04 (news ingestion and reporting)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/engines/base.py` — BaseEngine ABC and Signal dataclass; all four new engines subclass this
- `src/engines/technical.py` — Zone-mapping + weighted average scoring pattern to replicate for fundamental engine
- `src/data/analyze.py` — `_get_engines_for_asset()` list to extend with new engines, `_failed_signal()` for error fallback
- `src/llm/client.py` — `llm_completion()` with JSON mode for Reddit sentiment analysis and news impact scoring
- `src/data/idx_stocks.py` — yfinance wrapper with `run_in_executor` pattern for fundamental data fetch
- `src/report/formatter.py` — Shared formatter to extend with news digest section
- `src/config.py` — Settings class to extend with new API keys and engine weights

### Established Patterns
- BaseEngine.analyze(asset_id, symbol, df) -> Signal (frozen dataclass)
- Sequential engine execution per asset with gc.collect() after each
- `_failed_signal()` fallback on any engine exception — never crashes pipeline
- Data source tiers: IMPORTANT (macro) degrades gracefully, SUPPLEMENTARY (news, sentiment) silently skips
- Fetch-then-cache: fetchers store raw data in DB, engines read from DB during analyze
- Per-asset error isolation via try/except in analyze_stage
- pydantic-settings for all configuration with .env support
- Alembic for database migrations
- structlog JSON logging with component binding
- Two-process boundary: bot MUST NOT import pipeline/llm modules

### Integration Points
- New engines plug into `_get_engines_for_asset()` in `src/data/analyze.py`
- Macro and news fetchers run during fetch stage (extend `ingest_stage` or add parallel fetch functions)
- `news_events` table needs Alembic migration
- `macro_data` table needs Alembic migration
- `stock_fundamentals` table needs Alembic migration
- News digest section added to `src/report/formatter.py`
- New API keys (FRED, Finnhub, Reddit) added to `src/config.py` Settings

</code_context>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches. Follow existing BaseEngine pattern, zone-mapping scoring from TechnicalEngine, and fetch-then-cache data architecture.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 08-fundamental-macro-sentiment-and-news-engines*
*Context gathered: 2026-03-24*
