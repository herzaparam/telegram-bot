# Roadmap: Trade Signal Agent

## Overview

Build a daily trading signal system for Indonesian stocks and global crypto by first establishing a bulletproof foundation, then completing the end-to-end signal loop (data fetch, technical analysis, LLM verdict, Telegram delivery), then activating the self-evaluation feedback loop that no competitor has, then deepening analysis quality with additional engines and valuation tools, and finally adding discovery, due diligence, and portfolio risk capabilities.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [ ] **Phase 1: Foundation** - Project infrastructure, pipeline resilience, and all critical pitfall prevention baked in before any feature work
- [ ] **Phase 2: Data Layer** - TimescaleDB hypertables, IDX and crypto price fetchers, data validation and staleness detection
- [ ] **Phase 3: Technical Engine + Pipeline Shell** - First signal engine proving the BaseEngine interface contract; pipeline orchestrator with per-stage checkpointing
- [ ] **Phase 4: LLM Decision Maker** - LiteLLM structured output, deterministic fallback, full verdict with contradiction detection and event awareness
- [ ] **Phase 5: Telegram Bot + Daily Delivery** - Watchlist management, report commands, scheduled delivery; completes the core daily signal loop
- [ ] **Phase 6: Accuracy Tracking + Scorecard** - Decision tracking vs actual prices, per-engine stats, /scorecard command; validates signal quality
- [ ] **Phase 7: Self-Evaluation Feedback Loop** - LLM lesson extraction, lesson injection into decisions, /lessons command; the primary product differentiator
- [ ] **Phase 8: Fundamental, Macro, Sentiment, and News Engines** - Four additional engines that deepen analysis for both asset classes
- [ ] **Phase 9: IDX Documents + Valuation Engine** - PDF laporan keuangan parsing, DCF and peer analysis, /valuation and /fundamentals commands
- [ ] **Phase 10: Remaining Specialized Engines** - ML/AI, on-chain, options, behavioral, quantitative, network, game theory, and emerging methods engines
- [ ] **Phase 11: Asset Discovery + Due Diligence** - IHSG and crypto scanning, sector benchmarking, insider tracking, /discover and /duediligence commands
- [ ] **Phase 12: Portfolio Risk + Advanced Commands** - Correlation matrix, VaR, stress testing, enhanced fundamentals, /portfolio and /backtest commands

## Phase Details

### Phase 1: Foundation
**Goal**: The project infrastructure is production-ready from day one — Docker Compose running two isolated processes, config management, LLM wrapper with retry and fallback, pipeline_runs checkpointing table, and decision schema that prevents look-ahead bias
**Depends on**: Nothing (first phase)
**Requirements**: DATA-04, DATA-05, DATA-06
**Success Criteria** (what must be TRUE):
  1. `docker compose up` starts three services (bot, pipeline, db) and all three pass health checks
  2. Pipeline can be killed mid-run and restarted from the last successful stage checkpoint without re-processing completed stages
  3. LLM wrapper returns a deterministic fallback result (LLM_UNAVAILABLE flag) rather than crashing when the OpenAI API is unreachable
  4. Data source failures are classified by tier (critical/important/supplementary) and the pipeline continues with degraded output instead of halting
  5. decisions table stores decision_price and evaluation_price with explicit timestamps so no look-ahead bias is possible in accuracy calculations
**Plans**: 3 plans
Plans:
- [x] 01-01-PLAN.md — Project setup, config, Docker, DB models, Alembic migrations
- [x] 01-02-PLAN.md — Pipeline runner with per-asset checkpointing and data tier classification
- [x] 01-03-PLAN.md — LLM wrapper with deterministic fallback, bot health stub, production Docker

### Phase 2: Data Layer
**Goal**: IDX stock and crypto prices are fetched, validated, and stored in TimescaleDB hypertables with compression — the data foundation every engine depends on
**Depends on**: Phase 1
**Requirements**: DATA-01, DATA-02, DATA-03
**Success Criteria** (what must be TRUE):
  1. Running the ingest stage for BBCA.JK and BTC/USDT populates price_history hypertables with correct OHLCV rows and no null values
  2. If yfinance returns stale or malformed data, the pipeline sends a DATA_STALE alert rather than storing bad rows or crashing
  3. Rows older than 30 days are automatically compressed by TimescaleDB with measurable storage reduction
  4. Re-running the ingest stage for an already-fetched date produces no duplicate rows (idempotent)
**Plans**: 2 plans
Plans:
- [x] 02-01-PLAN.md — Schema models, Alembic hypertable migration, price repository, base fetcher contract, validation
- [x] 02-02-PLAN.md — IDX stock and crypto fetchers, staleness detection, alerts, ingest stage, backfill CLI

### Phase 3: Technical Engine + Pipeline Shell
**Goal**: The pipeline orchestrator sequences stages end-to-end and the technical analysis engine demonstrates the full BaseEngine interface contract — score, confidence, reasoning — on real price data
**Depends on**: Phase 2
**Requirements**: ENGN-01, ENGN-03
**Success Criteria** (what must be TRUE):
  1. Running the pipeline produces a signal record in the database for each watchlist asset containing RSI, MACD, Bollinger, EMA, and volume outputs as a composite score/confidence/reasoning triplet
  2. The quantitative engine (momentum, mean reversion, ARIMA) produces a valid score/confidence/reasoning for each asset alongside the technical engine
  3. Per-engine directional accuracy tracking is active from first run — each engine's outputs are stored with enough data to calculate accuracy once outcomes are known
  4. An engine that fails to fetch its data returns score=0/confidence=0 rather than raising an exception that halts the pipeline
**Plans**: 4 plans
Plans:
- [x] 03-01-PLAN.md — Dependencies, BaseEngine ABC, Signal dataclass, signals table migration, SignalRepository, config weights
- [x] 03-02-PLAN.md — TechnicalEngine with RSI, MACD, Bollinger, EMA, volume zone mapping and weighted scoring
- [x] 03-03-PLAN.md — QuantitativeEngine with momentum, mean reversion, ARIMA, and Hurst regime detection
- [ ] 03-04-PLAN.md — Analyze stage wiring into PipelineRunner with integration tests

### Phase 4: LLM Decision Maker
**Goal**: The LLM synthesizes all available engine scores into a final verdict with structured output, contradiction detection, event awareness, and a deterministic fallback — verdicts are stored and ready for delivery
**Depends on**: Phase 3
**Requirements**: LLM-01, LLM-02, LLM-03, LLM-05
**Success Criteria** (what must be TRUE):
  1. After the pipeline runs, each watchlist asset has a stored verdict (STRONG BUY / BUY / HOLD / SELL / STRONG SELL) with reasoning and fair value context
  2. When technical engine signals are bullish but a contradicting valuation score exists, the LLM flags the contradiction explicitly in its reasoning
  3. When the LLM API fails three times, the pipeline produces a verdict using a deterministic weighted-average fallback marked LLM_UNAVAILABLE rather than crashing
  4. LLM calls complete within 30 seconds per asset or abort with the fallback result
**Plans**: 2 plans
Plans:
- [x] 04-01-PLAN.md — DecisionRepository, prompt builder, contradiction detection, fallback logic, LLM response parsing
- [ ] 04-02-PLAN.md — Wire decide_stage into PipelineRunner

### Phase 5: Telegram Bot + Daily Delivery
**Goal**: Users receive the daily signal report automatically every morning via Telegram and can query it on demand — the core daily signal loop is complete end-to-end
**Depends on**: Phase 4
**Requirements**: WTCH-01, WTCH-02, WTCH-03, TBOT-01, TBOT-02, TBOT-03, TBOT-07, REPT-02, REPT-04
**Success Criteria** (what must be TRUE):
  1. A user can add BBCA.JK to their watchlist via Telegram, and the next morning's report includes BBCA.JK's signal without any manual intervention
  2. Sending /report delivers today's full signal report for all watchlist assets, including each asset's verdict and LLM reasoning, within 10 seconds
  3. Sending /report BTC delivers a single-asset detailed report for BTC
  4. The bot process never imports pipeline modules — querying pg_stat_activity confirms the bot process holds only bot-related queries
  5. Reports longer than Telegram's 4096-character limit are automatically split into multiple messages without truncation
**Plans**: 3 plans
Plans:
- [x] 05-01-PLAN.md — Watchlist + BotSettings models, Alembic migration, shared report formatter, config
- [ ] 05-02-PLAN.md — PTB webhook integration, auth, all bot command handlers (/start, /add, /remove, /watchlist, /report, /settings)
- [x] 05-03-PLAN.md — Pipeline report stage with Telegram delivery via httpx, wire into pipeline
**UI hint**: yes

### Phase 6: Accuracy Tracking + Scorecard
**Goal**: The system compares yesterday's decisions against actual prices every morning and reports honest accuracy stats — users know whether the signals are working
**Depends on**: Phase 5
**Requirements**: EVAL-01, EVAL-05, TBOT-04, REPT-01
**Success Criteria** (what must be TRUE):
  1. Every morning after market data is fetched, each prior-day decision is evaluated against its correct price window (IDX: next trading day close; crypto: 24h after decision) with no look-ahead bias
  2. /scorecard shows win rate, total decisions, best and worst performing engine, and comparison against a buy-and-hold baseline
  3. The daily report begins with an honest yesterday's scorecard section showing which calls were right and which were wrong
  4. Per-engine accuracy is tracked independently so the LLM can be given engine quality metadata in future phases
**Plans**: 2 plans
Plans:
- [x] 06-01-PLAN.md — Evaluation models, migration, repository, evaluate stage with classification and pipeline wiring
- [x] 06-02-PLAN.md — Scorecard formatting, daily report integration, /scorecard bot command

### Phase 7: Self-Evaluation Feedback Loop
**Goal**: The LLM reviews its past mistakes, extracts concrete lessons, stores them in tiers, and injects them into future decisions — the system improves over time without human intervention
**Depends on**: Phase 6
**Requirements**: EVAL-02, EVAL-03, EVAL-04, LLM-04, TBOT-05, REPT-05
**Success Criteria** (what must be TRUE):
  1. After each morning's evaluation, the LLM produces a written analysis of what went right and wrong for recent decisions, stored in the database
  2. A lesson does not become active until it has been observed at least 10 times, preventing overfitting on small samples
  3. Active lessons (up to 20 maximum) are injected into the LLM decision prompt for the current day's analysis
  4. /lessons shows the current active lesson set with their confidence tier (hypothesis / pattern / rule) and sample count
  5. The daily report includes a "lessons applied today" section listing which lessons were active
**Plans**: 2 plans
Plans:
- [x] 07-01-PLAN.md — Lesson model, migration, repository, reflect stage with two-pass LLM analysis and pipeline wiring
- [ ] 07-02-PLAN.md — Lesson injection into decide prompt, /lessons command, daily report lessons section

### Phase 8: Fundamental, Macro, Sentiment, and News Engines
**Goal**: Four additional engines deepen signal quality — fundamentals for IDX stocks, macro context for both asset classes, sentiment from social sources, and news-driven event signals
**Depends on**: Phase 7
**Requirements**: ENGN-02, ENGN-05, ENGN-09, ENGN-12, NEWS-01, NEWS-02, NEWS-03, NEWS-04
**Success Criteria** (what must be TRUE):
  1. The fundamental engine (P/E, P/B, revenue growth, ROE) produces a valid score for IDX stocks and score=0/confidence=0 for crypto assets where fundamentals do not apply
  2. The macro engine ingests BI rate, Fed rate, CPI, DXY, and rupiah data from FRED and produces a context score that the LLM incorporates into its reasoning
  3. The sentiment engine ingests Reddit, Stockbit sentiment, and Fear & Greed index and produces a score with stated data sources
  4. The event engine signals upcoming earnings, BI rate meetings, and crypto halvings in the LLM's event-awareness context
  5. Indonesian news (Kontan, CNBC Indonesia, Bisnis) and global crypto news (Finnhub) are fetched, LLM-scored for impact per asset, and summarized in the daily report
**Plans**: 4 plans
Plans:
- [x] 08-01-PLAN.md — Dependencies, config extensions, DB models (NewsEvent, MacroData, StockFundamental), Alembic migration 007
- [ ] 08-02-PLAN.md — Data fetchers: fundamental (yfinance), macro (FRED), news (RSS+Finnhub), sentiment (Fear&Greed+Reddit)
- [ ] 08-03-PLAN.md — Four engines (Fundamental, Macro, Sentiment, Event) and LLM news impact scorer
- [ ] 08-04-PLAN.md — Wiring: analyze_stage with 6 engines, global data fetch in pipeline, news digest in daily report

### Phase 9: IDX Documents + Valuation Engine
**Goal**: The system parses Indonesian financial PDFs directly from IDX and produces DCF, peer comparison, and scenario valuation — users can query fair value for any IDX stock
**Depends on**: Phase 8
**Requirements**: IDXD-01, IDXD-02, IDXD-03, ENGN-15, VALN-01, VALN-02, VALN-03, VALN-04, VALN-05, TBOT-09, TBOT-13, REPT-03
**Success Criteria** (what must be TRUE):
  1. The system automatically downloads the latest quarterly laporan keuangan for each IDX watchlist stock from idx.co.id
  2. GPT parses the PDF in Bahasa Indonesia and extracts revenue, net profit, debt, cash flow, and management outlook into structured database fields
  3. /valuation BBCA returns a DCF estimate, comparable company analysis, bull/base/bear scenario returns, and margin of safety versus current price
  4. The daily report includes a valuation summary showing fair value vs market price and margin of safety for each IDX stock
  5. Quarter-over-quarter ratio changes trigger alerts when they exceed defined thresholds
**Plans**: 2 plans
Plans:
- [ ] 04-01-PLAN.md — DecisionRepository, prompt builder, contradiction detection, fallback logic, LLM response parsing
- [ ] 04-02-PLAN.md — Wire decide_stage into PipelineRunner

### Phase 10: Remaining Specialized Engines
**Goal**: The full 15-engine suite is operational — ML/AI prediction, on-chain crypto analysis, options flow, behavioral anomalies, network correlation, game theory order book, and emerging quantitative methods
**Depends on**: Phase 9
**Requirements**: ENGN-04, ENGN-06, ENGN-07, ENGN-08, ENGN-10, ENGN-11, ENGN-13, ENGN-14
**Success Criteria** (what must be TRUE):
  1. The ML/AI engine runs XGBoost and ONNX-deployed LSTM inference within the memory budget (pipeline peak RAM stays under 1GB measured end-to-end)
  2. The on-chain engine fetches TVL, whale wallet movements, and exchange inflow/outflow for each crypto asset and produces a score
  3. All 15 engines produce a valid score/confidence/reasoning for each applicable asset in a single pipeline run
  4. Any engine that fails its data source returns score=0/confidence=0 — the pipeline completes the full run without that engine's contribution
  5. Per-engine accuracy is tracked for all 15 engines and visible in /scorecard
**Plans**: 2 plans
Plans:
- [ ] 04-01-PLAN.md — DecisionRepository, prompt builder, contradiction detection, fallback logic, LLM response parsing
- [ ] 04-02-PLAN.md — Wire decide_stage into PipelineRunner

### Phase 11: Asset Discovery + Due Diligence
**Goal**: The system scans beyond the watchlist to surface new opportunities and provides full due diligence reports on IDX stocks including ownership, management, and competitive positioning
**Depends on**: Phase 10
**Requirements**: DISC-01, DISC-02, DISC-03, DISC-04, DUED-01, DUED-02, DUED-03, DUED-04, LLM-06, TBOT-06, TBOT-10, TBOT-11, REPT-07
**Success Criteria** (what must be TRUE):
  1. Every morning the pipeline scans all IHSG stocks for unusual volume and breakout patterns, and the daily report includes a "New Opportunities" section with up to 5 ranked candidates
  2. The crypto scanner identifies top movers and anomalies and recommends assets based on signal strength
  3. /duediligence BBCA returns a report including sector benchmarking, insider ownership changes, management quality score, and competitive positioning
  4. The LLM incorporates due diligence flags (insider selling, management changes, earnings quality warnings) when they exist for an asset
  5. /compare BBCA BBRI BMRI returns a side-by-side sector comparison across key metrics
**Plans**: 2 plans
Plans:
- [ ] 04-01-PLAN.md — DecisionRepository, prompt builder, contradiction detection, fallback logic, LLM response parsing
- [ ] 04-02-PLAN.md — Wire decide_stage into PipelineRunner

### Phase 12: Portfolio Risk + Advanced Commands
**Goal**: Users can monitor their portfolio's risk exposure with correlation alerts, VaR estimates, and stress tests — and access historical backtesting and deep ratio analysis
**Depends on**: Phase 11
**Requirements**: RISK-01, RISK-02, RISK-03, RISK-04, RISK-05, FUND-01, FUND-02, FUND-03, TBOT-08, TBOT-12, REPT-06
**Success Criteria** (what must be TRUE):
  1. /portfolio shows a correlation matrix across all watchlist assets with highlighted spikes, sector concentration percentage, and currency exposure breakdown
  2. Daily portfolio VaR (daily and weekly) and maximum drawdown tracking appear in the daily report's portfolio risk snapshot section
  3. /backtest BTC 30d replays historical signals over the specified period and reports win rate, return, and comparison against buy-and-hold
  4. /fundamentals BBCA shows a 5-year trend dashboard of profitability, leverage, efficiency, and growth ratios alongside earnings quality and dividend analysis
  5. Stress testing runs historical scenario shocks (e.g., 2020 COVID crash, 2022 crypto winter) against the current portfolio and reports projected drawdown
**Plans**: 2 plans
Plans:
- [ ] 04-01-PLAN.md — DecisionRepository, prompt builder, contradiction detection, fallback logic, LLM response parsing
- [ ] 04-02-PLAN.md — Wire decide_stage into PipelineRunner
**UI hint**: yes


## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4 → 5 → 6 → 7 → 8 → 9 → 10 → 11 → 12

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Foundation | 0/3 | Planning complete | - |
| 2. Data Layer | 0/2 | Planning complete | - |
| 3. Technical Engine + Pipeline Shell | 0/4 | Planning complete | - |
| 4. LLM Decision Maker | 1/2 | In Progress|  |
| 5. Telegram Bot + Daily Delivery | 2/3 | In Progress|  |
| 6. Accuracy Tracking + Scorecard | 0/2 | Planning complete | - |
| 7. Self-Evaluation Feedback Loop | 0/2 | Planning complete | - |
| 8. Fundamental, Macro, Sentiment, and News Engines | 1/4 | In Progress|  |
| 9. IDX Documents + Valuation Engine | 0/TBD | Not started | - |
| 10. Remaining Specialized Engines | 0/TBD | Not started | - |
| 11. Asset Discovery + Due Diligence | 0/TBD | Not started | - |
| 12. Portfolio Risk + Advanced Commands | 0/TBD | Not started | - |
