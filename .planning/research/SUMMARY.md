# Project Research Summary

**Project:** Trade Signal Agent (IDX Stocks + Global Crypto)
**Domain:** Daily trading signal system with LLM decision synthesis and self-evaluation loop
**Researched:** 2026-03-23
**Confidence:** HIGH

## Executive Summary

This is a daily batch analysis system, not a real-time trading platform. The correct architecture for a daily-cadence signal agent on a constrained 2GB VPS is a two-process model: a lightweight always-on Telegram bot (~100MB) and an on-demand pipeline process (~1GB peak) that share state exclusively through PostgreSQL. Experts building this class of system emphasize that PostgreSQL + TimescaleDB as the sole integration layer eliminates the need for message queues, Redis, or microservices at this scale. The stack is mature and well-validated: Python 3.13, FastAPI, asyncpg + SQLAlchemy, LiteLLM for model-agnostic LLM calls, and system cron for scheduling (APScheduler 4.x remains in alpha and should be avoided).

The product's primary differentiators over existing signal bots (Stockbot, Steven Signal, Tickeron) are: (1) 15-engine multi-dimensional analysis instead of the industry-standard 1-3 technical indicators, (2) LLM-powered synthesis of contradictory engine outputs into nuanced verdicts, and (3) a self-evaluation feedback loop that extracts lessons from past decision outcomes to improve future decisions -- a capability absent in all surveyed competitors. The MVP must deliver the full daily loop end-to-end (data fetch, technical analysis, LLM verdict, Telegram delivery, decision tracking) before adding additional engines, even though additional engines are where the long-term value lies.

The dominant risks are operational, not algorithmic. yfinance is the only free IDX data source and has a documented history of breaking silently. The 2GB VPS memory budget is tight and requires strict per-asset sequential processing with explicit memory cleanup. The LLM structured output and self-evaluation feedback loop both have well-documented failure modes (validation errors crashing the pipeline; recency bias and overfitting in lessons) that must be addressed with defensive code from day one, not retrofitted later. All seven critical pitfalls identified in research have prevention strategies that should be built into Phase 1 rather than deferred.

## Key Findings

### Recommended Stack

The stack validates the existing architecture plan with one significant correction: replace APScheduler 4.x with system cron. APScheduler 4 has been in alpha for over a year (no stable release). For a single daily trigger, `0 6 * * * docker compose run --rm pipeline` is strictly more reliable. The dual-driver database approach (asyncpg for hot-path OHLCV queries, SQLAlchemy for relational tables) is correct -- asyncpg is 45% faster under load and the added complexity is justified for hypertable operations.

The pandas-ta library carries a flag: the original maintainer has warned of archival by July 2026. The community fork `pandas-ta-classic` (v0.4.47) is drop-in compatible and actively maintained. Pin the version and monitor. LLM costs are estimated at ~$0.50/month for the full daily pipeline at 20 assets, making GPT-4o-mini via LiteLLM the primary model with Gemini 2.0 Flash as a fallback -- cost is not a constraint.

**Core technologies:**
- Python 3.13 + uv: core runtime and package management -- fastest resolver, lockfile already present
- PostgreSQL 16 + TimescaleDB 2.25+: single database for relational and time-series -- avoids running InfluxDB/QuestDB
- asyncpg + SQLAlchemy 2.0: dual-driver pattern -- asyncpg for speed on OHLCV, SQLAlchemy for type-safe relational models
- LiteLLM ~1.82: model-agnostic LLM client -- swap GPT/Gemini/DeepSeek without code changes
- python-telegram-bot ~22.7: Telegram Bot API -- async, full Bot API 9.5 support
- ONNX Runtime ~1.24: ML inference -- ~50MB vs PyTorch's ~2GB, critical for VPS memory budget
- System cron + Docker Compose: scheduler -- replaces APScheduler 4.x which is still in alpha
- FastAPI + uvicorn: webhook server -- async-native, lightweight, ideal for the webhook-only role
- tenacity ~9.1: retry/resilience -- wrap every external API call from day one

### Expected Features

The MVP (v1) delivers the full daily signal loop. Additional engines are v1.x. Institutional-grade features (DCF valuation, portfolio VaR, ML/AI engine) are v2+.

**Must have (table stakes):**
- Daily signal delivery via Telegram -- core value; missing this means the product does not exist
- Watchlist management (/add, /remove, /watchlist) -- users choose what to track
- Technical analysis engine -- RSI, MACD, Bollinger, EMA, volume; first and most reliable engine type
- LLM final decision maker -- STRONG BUY to STRONG SELL with reasoning; the core differentiator even with one engine
- Decision tracking from day one -- required prerequisite for self-evaluation; collect data before evaluating
- Basic accuracy tracking / scorecard -- builds trust; users need to know if the system works
- Pipeline error handling and reliability -- retry logic, partial reports, failure alerts

**Should have (competitive):**
- Self-evaluation feedback loop -- the strongest differentiator; no competitor has this
- Fundamental analysis engine (IDX laporan keuangan PDF parsing) -- IDX-specific edge
- Macro/economic engine (FRED, BI rate, DXY) -- context for both asset classes
- Sentiment engine (Reddit, Fear & Greed) -- adds behavioral dimension after core is validated
- News-driven signals (Kontan, CNBC Indonesia RSS) -- LLM-scored news impact
- On-chain analysis engine -- crypto-specific depth (TVL, whale tracking, exchange flows)

**Defer (v2+):**
- Valuation engine (DCF + peer comparison) -- requires solid fundamental data pipeline first
- Due diligence module (ownership, insider tracking) -- depends on IDX scraping reliability
- Portfolio risk monitor (VaR, correlation matrix) -- institutional-grade; defer until users track positions
- ML/AI engine (XGBoost + LSTM via ONNX) -- requires training data and offline training pipeline
- Asset discovery / screener -- needs broad data fetching across all IHSG; defer until per-asset analysis is solid
- Scenario analysis (bull/base/bear) -- layered on valuation engine, not independent

### Architecture Approach

The system is a two-process batch architecture where PostgreSQL serves as the sole integration bus. The pipeline process runs once daily via cron, executes 5 sequential stages (Evaluate, Ingest, Analyze, Decide, Report), and terminates. The bot process runs always-on, responds to Telegram commands, and reads exclusively from PostgreSQL -- it never imports pipeline modules or engine code. This isolation is mandatory, not optional: the pipeline's peak RAM (~1GB) cannot coexist with the bot in the same process on a 2GB VPS. Each pipeline stage is idempotent and checkpointed in the `pipeline_runs` table, enabling restartability from the last successful asset on failure.

**Major components:**
1. Telegram Bot (Process 1, always-on ~100MB) -- handles commands, serves reports, manages watchlist via DB reads only
2. Pipeline Orchestrator (Process 2, daily cron ~1GB peak) -- sequences 5 stages with per-stage checkpointing
3. Data Fetchers -- yfinance (IDX), ccxt (crypto), FRED (macro), feedparser (news); write to TimescaleDB
4. Signal Engines x15 (sequential per-asset, one at a time) -- uniform EngineResult interface: score [-1,+1], confidence, reasoning
5. LLM Decision Maker -- LiteLLM structured output via Pydantic; deterministic fallback when LLM unavailable
6. Self-Evaluator -- compares decisions to actual prices, extracts lessons, injects into next-day LLM context
7. PostgreSQL + TimescaleDB -- hypertables for price_history, relational tables for everything else; the integration bus

### Critical Pitfalls

1. **yfinance breaks silently** -- validate every response (row count, date freshness, non-null OHLCV); cache aggressively; pipeline must send "DATA STALE" report rather than crash; data freshness monitor alerts if >2 trading days stale.

2. **OOM kills on 2GB VPS** -- process one asset at a time; after each: `del df`, `gc.collect()`, `ctypes.CDLL("libc.so.6").malloc_trim(0)`; set PostgreSQL shared_buffers=256MB; set pipeline RAM limit with resource.setrlimit; monitor RSS between assets.

3. **LLM structured output failures crash the pipeline** -- wrap every LLM call in 3-retry loop with exponential backoff; Pydantic validation in try/except; deterministic weighted-average fallback with LLM_UNAVAILABLE flag; 30-second hard timeout.

4. **Self-evaluation feedback loop overfitting** -- require n=10 minimum before a lesson becomes active; cap active lessons at 15-20; tier lessons by sample size (hypothesis/pattern/rule); track lesson performance and demote underperformers.

5. **Look-ahead bias invalidates accuracy metrics** -- store decision_price and evaluation_price with exact timestamps in decisions table; define evaluation windows explicitly (IDX: next trading day close; crypto: 24h after decision); never use "latest price" for evaluation.

6. **15 engines producing noise, not signal** -- track per-engine directional accuracy independently from day one; require new engines to improve composite accuracy on a validation period before enabling; give LLM explicit engine quality metadata.

7. **Pipeline failure = missed morning reports** -- per-stage checkpointing in pipeline_runs table; send partial report on partial failure with INCOMPLETE flag; schedule automatic retry at 07:00 if 06:00 run fails; engines must return score=0/confidence=0 on data unavailability, not raise exceptions.

## Implications for Roadmap

Based on research, the architecture's dependency chain directly dictates phase order. Database first. Data fetchers second. One engine + pipeline shell third. LLM integration fourth. Telegram delivery fifth. Self-evaluation sixth. Additional engines seventh onwards, each validated before the next.

### Phase 1: Foundation
**Rationale:** Every other component depends on the database schema, Docker Compose setup, and config management. Pitfall prevention for OOM, data staleness, LLM failures, and look-ahead bias must be built into the infrastructure before any features are added -- retrofitting these is significantly more expensive.
**Delivers:** Running PostgreSQL + TimescaleDB, project structure, pydantic-settings config, Docker Compose with bot + pipeline + db services, LLM wrapper with retry/fallback, pipeline_runs checkpointing table, decision schema with price snapshots.
**Addresses:** FEATURES.md infrastructure prerequisites; PITFALLS.md P1-P7 prevention (all critical pitfalls have Phase 1 components)
**Avoids:** OOM (PostgreSQL tuning done now), LLM failures (wrapper built now), data staleness (validation schema built now), look-ahead bias (decision schema correct from start)

### Phase 2: Data Layer
**Rationale:** Engines cannot run without data. Data fetchers must exist and write to TimescaleDB before any analysis is possible.
**Delivers:** IDX price fetching (yfinance with validation + staleness detection), crypto price fetching (ccxt with exchange fallback), TimescaleDB storage with compression enabled, data freshness monitoring.
**Addresses:** FEATURES.md "Historical price data storage"; PITFALLS.md Pitfall 1 (yfinance unreliability)
**Avoids:** yfinance silent failures (validation from day one); disk growth (compression enabled immediately)
**Stack:** yfinance ~0.2.x, ccxt, asyncpg, TimescaleDB hypertables

### Phase 3: First Engine + Pipeline Shell
**Rationale:** Technical analysis is the simplest, most reliable engine (pure computation, no external API). Building the pipeline orchestrator around one engine proves the architecture before adding complexity. The engine interface contract established here applies to all 15 engines.
**Delivers:** Pipeline orchestrator with idempotent stage execution, BaseEngine interface (score/confidence/reasoning contract), Technical Analysis engine (RSI, MACD, Bollinger, EMA, volume), end-to-end: fetch → store → analyze → store signal.
**Addresses:** FEATURES.md "Technical analysis signals"; PITFALLS.md Pitfall 6 (engine noise) -- per-engine accuracy tracking starts here
**Avoids:** Engine quality dilution (accuracy baseline established before adding engines)
**Stack:** pandas-ta, pandas, numpy

### Phase 4: LLM Integration
**Rationale:** The LLM decision maker works with even one engine. Building this now validates the full signal loop before adding Telegram complexity. Structured output parsing, retry logic, and deterministic fallback are critical to get right before any user-facing delivery.
**Delivers:** LiteLLM client wrapper, LLM decision maker with structured Pydantic output, deterministic fallback (weighted average when LLM unavailable), end-to-end: fetch → analyze → decide → store decision.
**Addresses:** FEATURES.md "Clear buy/sell/hold verdict", "Signal reasoning/explanation"
**Avoids:** LLM structured output crashes (Pitfall 4 -- defensive parsing and fallback built here)
**Stack:** LiteLLM ~1.82, Pydantic v2

### Phase 5: Telegram Bot + Daily Delivery
**Rationale:** The working pipeline needs a delivery mechanism. Telegram delivery completes the core daily loop. The two-process isolation (bot reads DB, never imports pipeline modules) is enforced here.
**Delivers:** FastAPI webhook, watchlist commands (/add, /remove, /watchlist), /report command, scheduled daily report delivery, /status command showing pipeline state, two-process deployment verified.
**Addresses:** FEATURES.md "Daily signal delivery", "Watchlist management", "Entry/exit context", "Error recovery and reliability"
**Avoids:** Bot/pipeline coupling (Pitfall: coupling bot to pipeline internals -- bot reads DB only); Telegram 4096-char limit (message splitting implemented)
**Stack:** python-telegram-bot ~22.7, FastAPI ~0.135, uvicorn

### Phase 6: Accuracy Tracking + Decision Tracking
**Rationale:** After 2-4 weeks of live decisions exist, the accuracy tracking system provides the data needed for self-evaluation. The /scorecard command builds user trust. This phase validates that the core loop produces meaningful signals before adding more engines.
**Delivers:** Yesterday's-decision vs. actual-price comparison, per-engine accuracy stats, /scorecard command (win rate, vs. buy-and-hold baseline), pipeline run history.
**Addresses:** FEATURES.md "Accuracy tracking / scorecard"
**Avoids:** Look-ahead bias (Pitfall 5 -- correct evaluation windows per asset type: IDX next-close, crypto 24h)

### Phase 7: Self-Evaluation Feedback Loop
**Rationale:** Requires accumulated decision data (Phase 6). The self-evaluation loop is the strongest product differentiator -- no competitor has it. Built after the core loop is stable to avoid complexity before the foundation is proven.
**Delivers:** Evaluator stage (compare decisions to actual outcomes), lesson extraction via LLM, lesson storage with confidence tiers (hypothesis/pattern/rule), lesson injection into decision prompts, lesson expiration and cap (max 20 active lessons).
**Addresses:** FEATURES.md "Self-evaluation feedback loop" (top differentiator)
**Avoids:** Feedback loop overfitting (Pitfall 3 -- lesson tiers, sample size minimum, performance tracking built in)

### Phase 8+: Additional Engines (Incremental)
**Rationale:** Each engine is independently valuable and the system works with any number. Build in order of data reliability: Fundamental (IDX PDF parsing), Macro (FRED, BI rate), Sentiment (Reddit, Fear & Greed), News (RSS), On-chain (DeFiLlama). Each engine requires a validation checkpoint before the next is added.
**Delivers:** Deepening analysis quality with each addition; laporan keuangan PDF parsing unlocks IDX fundamental edge.
**Addresses:** FEATURES.md differentiators (multi-engine analysis, IDX PDF parsing, on-chain for crypto)
**Avoids:** Engine noise (Pitfall 6 -- per-engine accuracy checkpoint before enabling each new engine)
**Stack:** pymupdf4llm, fredapi, praw, feedparser, httpx (DeFiLlama/Etherscan)

### Phase Ordering Rationale

- **Database and pitfall prevention before any features:** All 7 critical pitfalls have Phase 1 components. This is not premature defensive coding -- it is the minimum to avoid expensive rewrites.
- **Technical engine before LLM:** You need at least one engine output to test the LLM integration meaningfully. Technical engine has no external API dependencies, making it the least likely to introduce confounding failures.
- **LLM before Telegram:** Reports need decisions to display. Building delivery before the decision pipeline is backwards.
- **Self-evaluation requires accumulated data:** The feedback loop is meaningless with fewer than 10 decisions per category. Start tracking on day one; activate evaluation after 2-4 weeks.
- **Additional engines last:** Each engine adds value but the system works without them. Validate the core loop first; add engines once you can measure their contribution.

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 2 (Data Layer):** yfinance reliability for .JK suffix stocks is documented as fragile; IDX market calendar (holidays, trading halts) needs explicit handling; investigate delta-fetch logic to avoid re-fetching full history.
- **Phase 8 (Fundamental Engine):** IDX laporan keuangan PDFs vary significantly in structure; pymupdf4llm handles most but scanned PDFs need vision LLM fallback strategy; Bank Indonesia financial data API access needs verification.
- **Phase 8 (On-chain Engine):** DeFiLlama and Etherscan free tier limits need validation against actual call volume for 20 crypto assets at daily cadence.

Phases with standard patterns (skip research-phase):
- **Phase 1 (Foundation):** TimescaleDB setup, Docker Compose, pydantic-settings -- all well-documented with clear examples.
- **Phase 3 (Technical Engine):** pandas-ta indicators are well-documented; RSI/MACD/Bollinger are textbook implementations.
- **Phase 4 (LLM Integration):** LiteLLM structured output pattern is well-documented; Pydantic v2 response_format is standard.
- **Phase 5 (Telegram Bot):** python-telegram-bot v22 has thorough documentation and examples for webhook + command handling.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Existing architecture plan validated; all versions pinned and checked against March 2026 PyPI state; one significant correction (APScheduler 4.x → system cron) |
| Features | HIGH | Competitor analysis complete; MVP scope is conservative and testable; feature dependencies mapped explicitly |
| Architecture | HIGH | Two-process pattern is well-established for this class of system; memory budget analysis is concrete with actual numbers |
| Pitfalls | HIGH | Seven critical pitfalls each backed by public post-mortems, GitHub issues, and production incident reports; prevention strategies are specific and actionable |

**Overall confidence:** HIGH

### Gaps to Address

- **yfinance IDX delta-fetch logic:** The correct approach for fetching only new days since last stored date for .JK tickers needs prototyping early (Phase 2) to confirm yfinance supports date-range queries reliably for IDX.
- **pandas-ta archival timeline:** Library may be archived July 2026. If timeline overlaps with development, migrate to `pandas-ta-classic` during Phase 3 rather than at archival. Monitor monthly.
- **TimescaleDB compression chunk interval:** Research recommends 7-day chunk intervals for daily data. Verify this matches actual query patterns (most queries span 30-200 days) before setting in Phase 1 migration.
- **LLM prompt token budget with 15 engines:** At full 15 engines, each with reasoning text, plus lessons, the prompt may exceed GPT-4o-mini's context window. Token counting strategy needed before Phase 7+ (prompt truncation or summarization of engine reasoning).
- **IDX trading calendar for evaluation windows:** Evaluating IDX decisions against "next trading day close" requires an accurate IDX holiday calendar. No free API for this was identified; may need a static calendar maintained in the database.

## Sources

### Primary (HIGH confidence)
- python-telegram-bot v22.7 official docs -- Telegram integration patterns
- LiteLLM PyPI v1.82.4 -- model-agnostic LLM client, structured output
- TimescaleDB releases v2.25.2 -- hypertable patterns, compression
- SQLAlchemy 2.0.48 changelog -- async session, Alembic 1.18.4
- ONNX Runtime v1.24.4 PyPI -- inference deployment for Python 3.11+
- FastAPI v0.135.1 PyPI -- webhook endpoint patterns
- pymupdf4llm v1.27.2.2 PyPI -- PDF parsing for LLM pipelines
- tenacity v9.1.4 PyPI -- retry patterns
- pydantic-settings v2.13.1 PyPI -- environment config validation

### Secondary (MEDIUM confidence)
- yfinance GitHub Issues -- reliability concerns, Feb 2025 and Sep 2025 breakages documented
- pandas-ta PyPI / pandas-ta-classic PyPI -- archival warning and fork status
- APScheduler PyPI -- 4.0.0a6 alpha confirmed (no stable 4.x release)
- Macrosynergy research on signal quality measurement
- 888 algorithmic strategies study on backtest reliability (fxreplay.com)

### Tertiary (requires validation during implementation)
- IDX laporan keuangan PDF structure consistency -- pymupdf4llm handles most; scanned PDFs unverified
- DeFiLlama / Etherscan free tier limits for daily crypto analysis at 20-asset scale -- call volume not measured
- Google Trends official API (post-July 2025) -- pytrends archived April 2025; free programmatic access unverified

---
*Research completed: 2026-03-23*
*Ready for roadmap: yes*
