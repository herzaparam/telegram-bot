# Phase 9: IDX Documents + Valuation Engine - Context

**Gathered:** 2026-03-25
**Status:** Ready for planning

<domain>
## Phase Boundary

Parse Indonesian financial PDFs (laporan keuangan) from idx.co.id, extract structured financial data, and build a valuation engine producing DCF, peer comparison, and scenario analysis. Expose via `/valuation` and `/fundamentals` Telegram commands and a valuation summary in the daily report. Covers: IDX PDF scraper/fetcher, LLM-based PDF parsing (pymupdf4llm + GPT), financial_docs and financial_data tables, ValuationEngine (DCF, peer comparison, scenario analysis, crypto proxies), QoQ ratio tracking with alerts, `/valuation` command, `/fundamentals` command, daily report valuation summary section. Does NOT include: on-chain engine (Phase 10), ML/AI engine (Phase 10), asset discovery (Phase 11), due diligence module (Phase 11), or portfolio risk (Phase 12).

</domain>

<decisions>
## Implementation Decisions

### PDF Sourcing Strategy
- **D-01:** Auto-scrape idx.co.id for laporan keuangan using direct HTTP requests via httpx (not headless browser). Reverse-engineer download URLs for each watchlist stock
- **D-02:** Fetch both quarterly (Q1, Q2, Q3 interim) and annual reports. Keep last 4 quarterly + 2 annual reports per stock for trend analysis
- **D-03:** Weekly check frequency — run the IDX doc fetcher once per week (financial reports update quarterly, daily is wasteful)
- **D-04:** Store both raw PDFs (in `data/financial_docs/` directory) and extracted data in DB. Allows re-parsing if extraction logic improves
- **D-05:** Graceful degradation on scraper failure — fall back to existing yfinance fundamentals (FundamentalEngine), log error, send Telegram alert to user. Valuation runs with available data

### Financial Data Extraction
- **D-06:** Extract core fields: revenue (pendapatan), net profit (laba bersih), total debt (utang), operating cash flow (arus kas operasi), equity (ekuitas) PLUS margins (gross, operating, net), management outlook/guidance text, and capex
- **D-07:** LLM handles Bahasa Indonesia in-prompt — send Indonesian text to GPT-4o-mini with extraction prompt using Indonesian field names, LLM returns structured numeric/English output. Vision LLM fallback for complex/scanned pages per architecture
- **D-08:** PDF-extracted data enhances (not replaces) existing FundamentalEngine. FundamentalEngine keeps using yfinance for quick ratios. ValuationEngine reads PDF-extracted financials for DCF/peer analysis. Two complementary sources
- **D-09:** Cross-validate key metrics — compare PDF-extracted revenue/profit with yfinance reported values when available. Flag discrepancies >10% for review
- **D-10:** Database schema: `financial_docs` table (PDF metadata: stock, period, download date, file path, parse status) + `financial_data` table (extracted fields per doc, one row per metric per period). Normalized and queryable

### Valuation Methodology
- **D-11:** DCF discount rate: formula-based WACC from risk-free rate (BI rate or US 10Y) + equity risk premium + beta. Growth rate from historical revenue CAGR capped at GDP growth. Transparent and reproducible
- **D-12:** Peer groups: sector-based from IDX classification (Banking, Telco, Consumer, etc.). Compare P/E, P/B, EV/EBITDA within sector using existing asset metadata
- **D-13:** Crypto valuation: lightweight proxies only — NVT ratio for BTC/ETH, market cap / TVL for DeFi tokens. On-chain engine (Phase 10) will add more depth
- **D-14:** Scenario analysis: base = historical revenue CAGR, bull = +1 standard deviation, bear = -1 SD. Probability weights: 25% bull / 50% base / 25% bear. Data-driven and reproducible
- **D-15:** ValuationEngine follows BaseEngine contract: `analyze(asset_id, symbol, df) -> Signal` with score reflecting margin of safety (undervalued = positive, overvalued = negative)

### Telegram Commands & Daily Report
- **D-16:** `/valuation BBCA` shows summary: fair value estimate, current price, margin of safety %, DCF range (bull/base/bear), peer comparison rank. Fits in one Telegram message
- **D-17:** `/fundamentals BBCA` shows ratio dashboard: P/E, P/B, ROE, margins, debt/equity, QoQ changes with trend arrows. Complementary to /valuation
- **D-18:** `/valuation` and `/fundamentals` are IDX stocks only. Crypto assets get: "Valuation not available for crypto assets — use /report BTC for signal analysis"
- **D-19:** Daily report valuation summary (REPT-03): compact table per IDX stock — ticker, current price, fair value, margin of safety %, verdict arrow. Quick scan format
- **D-20:** When no financial docs available (first run or scraper failed): show yfinance-based rough estimate with clear disclaimer "estimated from market data only — no financial reports parsed yet"
- **D-21:** QoQ ratio change alerts (VALN-05): included in daily report only when significant changes detected after new quarterly report parsing. No push notifications

### Claude's Discretion
- idx.co.id URL structure and scraping implementation details
- pymupdf4llm extraction parameters and Vision LLM fallback trigger conditions
- LLM prompt design for financial data extraction and news analysis
- financial_docs and financial_data table column details and indexes
- WACC calculation specifics (risk premium values, beta source)
- Peer comparison metric weights and ranking algorithm
- NVT and TVL data sources for crypto proxies
- Scenario analysis terminal value methodology
- Telegram message formatting and emoji usage
- QoQ change threshold values for "significant" alerts
- Error handling and retry logic for each new component
- Alembic migration details for new tables
- How to wire ValuationEngine into `_get_engines_for_asset()` in analyze.py

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Architecture & Valuation Design
- `plan/ARCHITECTURE.md` — Full system architecture, IDX Financial Doc Parser Flow, LLM cost estimates for PDF parsing
- `plan/ARCHITECTURE.md` §IDX Financial Doc Parser Flow — pymupdf4llm + Vision LLM fallback pipeline, extraction prompt design
- `plan/ARCHITECTURE.md` §Data Sources — idx.co.id PDF download, data tiers, rate limits
- `plan/ARCHITECTURE.md` §Database Schema — financial_docs table reference
- `plan/ARCHITECTURE.md` §Project Structure — Planned file layout: `src/data/idx_fundamentals.py`, `src/llm/doc_parser.py`

### Existing Engine Pattern
- `src/engines/base.py` — BaseEngine ABC, Signal dataclass (frozen), category property, supports_stocks/supports_crypto
- `src/engines/fundamental.py` — Existing FundamentalEngine with zone-mapping scoring (yfinance-based, not replaced by Phase 9)
- `src/engines/technical.py` — Zone-mapping + weighted average pattern to reference
- `src/data/analyze.py` — `_get_engines_for_asset()`, `_failed_signal()`, `analyze_stage()` — new engine plugs in here

### Data Fetcher Pattern
- `src/data/base.py` — BaseFetcher ABC, OHLCVRow dataclass
- `src/data/idx_stocks.py` — IDXStockFetcher (yfinance with run_in_executor) — reference for new IDX doc fetcher
- `src/data/fundamental_fetcher.py` — Existing fundamental data fetcher pattern
- `src/data/ingest.py` — Fetch stage StageFunc; new IDX doc fetcher integrates here

### LLM Infrastructure
- `src/llm/client.py` — `llm_completion()` with JSON mode, retry, fallback — used for PDF parsing and extraction
- `src/llm/prompts.py` — Prompt builder patterns

### Bot & Report
- `src/bot/handlers/report.py` — Report command handlers to extend with /valuation and /fundamentals
- `src/report/formatter.py` — Shared formatter for daily report, add valuation summary section

### Database & Config
- `src/db/models.py` — Existing ORM models; add financial_docs and financial_data models
- `src/config.py` — Settings class (no new API keys needed for Phase 9 — uses existing LLM config)
- `src/db/migrations/` — Alembic migrations for new tables

### Prior Phase Context
- `.planning/phases/08-fundamental-macro-sentiment-and-news-engines/08-CONTEXT.md` — FundamentalEngine decisions (yfinance-based, D-01 through D-04), fetch-then-cache pattern
- `.planning/phases/04-llm-decision-maker/04-CONTEXT.md` — LLM JSON mode, structured output, English-only prompts

### Requirements
- `.planning/REQUIREMENTS.md` — IDXD-01/02/03 (PDF download/parse/extract), ENGN-15 (valuation engine), VALN-01/02/03/04/05 (DCF, peer, crypto, scenarios, QoQ), TBOT-09/13 (/valuation, /fundamentals), REPT-03 (report valuation summary)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/engines/base.py` — BaseEngine ABC and Signal dataclass; ValuationEngine subclasses this
- `src/engines/fundamental.py` — FundamentalEngine with zone-mapping scoring; provides complementary yfinance ratios
- `src/data/idx_stocks.py` — yfinance wrapper with `run_in_executor` pattern for async I/O; reference for IDX doc fetcher
- `src/data/fundamental_fetcher.py` — Existing fundamental data fetcher; reference for new financial doc fetcher
- `src/llm/client.py` — `llm_completion()` with JSON mode for PDF extraction and Vision LLM fallback
- `src/report/formatter.py` — Shared formatter to extend with valuation summary section
- `src/config.py` — Settings class to extend with valuation-specific config (thresholds, weights)
- `src/db/models.py` — ORM models to extend with financial_docs and financial_data

### Established Patterns
- BaseEngine.analyze(asset_id, symbol, df) -> Signal (frozen dataclass)
- Sequential engine execution per asset with gc.collect() after each
- `_failed_signal()` fallback on any engine exception — never crashes pipeline
- Fetch-then-cache: fetchers store raw data in DB, engines read from DB during analyze
- Per-asset error isolation via try/except in analyze_stage
- pydantic-settings for all configuration with .env support
- Alembic for database migrations
- structlog JSON logging with component binding
- Two-process boundary: bot MUST NOT import pipeline/llm modules

### Integration Points
- ValuationEngine plugs into `_get_engines_for_asset()` in `src/data/analyze.py`
- IDX doc fetcher runs during fetch stage (weekly schedule, separate from daily price fetch)
- `financial_docs` and `financial_data` tables need Alembic migration
- `/valuation` and `/fundamentals` commands added to bot handlers
- Valuation summary section added to `src/report/formatter.py`
- Cross-validation logic compares PDF-extracted vs yfinance values

</code_context>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches. Follow existing BaseEngine pattern, fetch-then-cache architecture, and zone-mapping scoring from FundamentalEngine. Architecture doc provides detailed IDX Financial Doc Parser Flow to follow.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 09-idx-documents-valuation-engine*
*Context gathered: 2026-03-25*
