# Phase 11: Asset Discovery + Due Diligence - Context

**Gathered:** 2026-03-26
**Status:** Ready for planning

<domain>
## Phase Boundary

Scan beyond the watchlist to surface new trading opportunities across IHSG stocks and crypto, and provide full due diligence reports on IDX stocks including sector benchmarking, ownership analysis, management quality scoring, and competitive positioning. New Telegram commands: `/discover`, `/duediligence`, `/compare`. New daily report section: "New Opportunities" with top 5 ranked candidates. LLM decision maker enhanced with DD flags (LLM-06). Does NOT include: portfolio risk monitoring (Phase 12), backtesting (Phase 12), enhanced ratio dashboards (Phase 12), or real-time alerts (v2).

</domain>

<decisions>
## Implementation Decisions

### Discovery Scanning Scope
- **D-01:** Scan all ~900 IHSG stocks daily for unusual activity — full IDX universe, no filtering to LQ45/IDX80 subset. yfinance bulk fetch for screening data
- **D-02:** Scan top 100 crypto by market cap via CoinGecko for top movers and anomalies
- **D-03:** Four trigger types for flagging discoveries: volume spike (>2x 20-day avg), price breakout (52-week high, resistance break, Bollinger), momentum surge (RSI/MACD crossover), and statistical anomaly detection
- **D-04:** Screening criteria only — scanner uses lightweight checks (volume, price patterns) to flag candidates. Full 15-engine analysis only runs when user adds asset to watchlist. Keeps scan fast
- **D-05:** Top 5 opportunities presented as compact cards in daily report "New Opportunities" section, matching existing report card style from Phase 5
- **D-06:** Multi-trigger composite score for ranking — weight each trigger type and combine into single score. Assets with multiple triggers rank higher

### Due Diligence Data Sources
- **D-07:** Insider/ownership data from IDX disclosure filings on idx.co.id — reuse httpx scraping patterns from Phase 9 PDF fetcher
- **D-08:** Extract shareholder composition with percentages, plus quarter-over-quarter changes. Flag when major holders increase/decrease positions significantly. No individual insider transaction log
- **D-09:** Management quality scored on financial track record only — revenue CAGR, ROE trend, capital allocation efficiency over 3-5 years. All data already available from Phase 9 parsed financials
- **D-10:** Sector benchmarking uses IDX sector classification (Banking, Telco, Consumer, etc.) — compare company P/E, P/B, ROE, margins against sector median. Highlights above/below sector
- **D-11:** Due diligence is IDX stocks only. Crypto assets get "not applicable" response (consistent with /valuation in Phase 9)
- **D-12:** Weekly refresh cycle for ownership/DD data — matches Phase 9's weekly PDF check pattern. Insider transactions are disclosed periodically, not daily
- **D-13:** DD flags appear in daily report and /duediligence command only. No push alerts — consistent with daily-cadence design

### Telegram Commands
- **D-14:** `/discover` shows today's top 5 opportunities as compact cards (ticker, trigger type icon, signal strength, current price + change%). No filtering arguments — simple, show top 5 overall
- **D-15:** `/duediligence BBCA` returns single comprehensive message with all DD info: sector rank, ownership changes, management score, competitive position. Compact formatting like /valuation
- **D-16:** `/compare BBCA BBRI BMRI` displays side-by-side metrics table with tickers as columns, metrics as rows (P/E, P/B, ROE, margins, debt/equity). Best/worst highlighted
- **D-17:** `/compare` is IDX stocks only — comparison uses fundamental metrics (P/E, ROE, etc.) which are equity-specific

### LLM Integration
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

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

No external specs — requirements fully captured in decisions above and REQUIREMENTS.md requirements: DISC-01 through DISC-04, DUED-01 through DUED-04, LLM-06, TBOT-06, TBOT-10, TBOT-11, REPT-07.

### Key source files
- `src/engines/base.py` — BaseEngine contract (analyze -> Signal pattern)
- `src/data/analyze.py` — `_get_engines_for_asset()`, `analyze_stage()` — engine wiring
- `src/data/ingest.py` — ingest_stage pattern for data fetchers
- `src/bot/handlers/valuation.py` — /valuation command pattern (single comprehensive message, IDX-only)
- `src/bot/handlers/fundamentals.py` — /fundamentals command pattern
- `src/report/formatter.py` — Report card formatting, shared by bot and pipeline
- `src/config.py` — Settings class for API keys with graceful degradation
- `src/db/models.py` — Existing ORM models, SEED_ASSETS

### Prior phase patterns
- Phase 9 CONTEXT.md — IDX scraping patterns (httpx, weekly fetch, graceful degradation)
- Phase 10 CONTEXT.md — Stub engine pattern, data fetcher wiring, Settings extension

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/data/ingest.py` — ingest_stage pattern for adding new data fetchers (on-chain, GitHub already added in Phase 10)
- `src/engines/base.py` — BaseEngine contract for any new DD-related engine
- `src/bot/handlers/valuation.py` — Template for single-asset comprehensive Telegram command
- `src/report/formatter.py` — Card formatting for report sections
- Phase 9's IDX httpx scraping patterns — reusable for disclosure filing scraping
- `src/engines/behavioral.py` — Volume anomaly detection already exists (>2 std dev) — discovery scanner can reuse this logic

### Established Patterns
- Two-process boundary: bot reads from DB via signals table `indicators` JSONB, never imports pipeline modules
- HTML parse_mode for all Telegram messages
- One handler file per command group in `src/bot/handlers/`
- Sequential engine execution with `del + gc.collect()` for RAM management
- Settings class with optional API keys and graceful degradation
- StageFunc signature: `async (session, asset) -> None`

### Integration Points
- `_get_engines_for_asset()` in `src/data/analyze.py` — won't need changes (discovery doesn't run engines on non-watchlist assets)
- LLM decision prompt in `src/pipeline/` — needs DD flags context section added
- Daily report formatter — needs "New Opportunities" section appended
- Pipeline runner — needs discovery scan stage (runs on full universe, not per-watchlist-asset)
- Bot command registration — add /discover, /duediligence, /compare handlers

</code_context>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 11-asset-discovery-due-diligence*
*Context gathered: 2026-03-26*
