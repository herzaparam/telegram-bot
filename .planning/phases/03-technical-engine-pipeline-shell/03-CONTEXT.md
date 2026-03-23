# Phase 3: Technical Engine + Pipeline Shell - Context

**Gathered:** 2026-03-23
**Status:** Ready for planning

<domain>
## Phase Boundary

The pipeline orchestrator sequences stages end-to-end and the technical analysis engine and quantitative engine demonstrate the full BaseEngine interface contract — score, confidence, reasoning — on real price data. Covers: BaseEngine abstract class, TechnicalEngine implementation, QuantitativeEngine implementation, signals table migration, SignalRepository, analyze stage wiring into PipelineRunner, per-engine accuracy tracking storage. Does NOT include: LLM decision making (Phase 4), other engines (Phase 8+), Telegram delivery (Phase 5), or accuracy evaluation logic (Phase 6).

</domain>

<decisions>
## Implementation Decisions

### Technical Indicator Configuration
- RSI: Dual period — RSI(14) + RSI(7) for medium-term and short-term momentum
- MACD: Standard 12/26/9 configuration (fast EMA 12, slow EMA 26, signal line 9)
- Bollinger Bands: Dual bands — outer (20-period, 2σ) + inner (20-period, 1σ) for extremes and early signals
- EMA: Full set — 9, 21, 50, 100, 200 periods
- Volume: OBV (On-Balance Volume) trend direction + volume vs 20-day SMA
- Same parameters for both IDX stocks and crypto — no asset-class-specific tuning
- Stick to required indicators only (RSI, MACD, Bollinger, EMA, volume) — no extras like ATR/Stochastic in this phase

### Quantitative Engine Scope
- Auto-ARIMA via pmdarima: auto_arima finds best (p,d,q) params, produces 1-day-ahead forecast with confidence interval
- Momentum: Rate of Change (ROC) at 5, 10, 20 day windows + Hurst exponent for regime detection
- Mean reversion: Ornstein-Uhlenbeck half-life estimation + Z-score of price relative to rolling mean (20/50 day)
- Regime detection: Hurst-driven weighting — if H>0.5 (trending), weight momentum higher; if H<0.5 (mean-reverting), weight z-score higher
- Regime included in reasoning text (e.g., "BTC in trending regime (H=0.62), momentum weighted higher")
- Minimum data requirement: 200 trading days per asset
- Graceful degradation: skip ARIMA and Hurst if <200 days, run only ROC and basic z-score, lower confidence to reflect limited data

### Score Composition Method
- Weighted average with zone mapping: each indicator maps to a sub-score (-1 to +1) via predefined zones (e.g., RSI<30 = bullish sub-score), then combined via weighted average
- Confidence: signal agreement (how many indicators agree) + data quality penalty (missing data or stale prices reduce confidence)
- Indicator weights stored in pydantic-settings config, overridable via env vars
- Reasoning format: key indicators summary — concise, factual, lists the specific indicators that drove the score (e.g., "RSI(14)=28 oversold, MACD bullish cross, price at lower BB(1σ). Bullish bias with 4/6 indicators agreeing.")

### Accuracy Tracking Storage
- Full `signals` table created via Alembic migration matching ARCHITECTURE.md schema: (asset_id, date, category, score, confidence, reasoning, indicators, data_quality)
- Add `price_at_signal` column: store asset's latest close price when signal is generated, for later accuracy comparison without look-ahead bias
- `data_quality` JSONB tracks: sources available, sources failed, trading days of data used, indicators skipped
- `indicators` JSONB stores final computed values only (e.g., {"rsi_14": 28, "macd_signal": "bullish_cross"}) — no intermediate series
- Signals are idempotent: UPSERT on (asset_id, date, category), re-running overwrites previous signals
- Batch insert: all engine signals for one asset collected then bulk-inserted in one transaction
- SignalRepository class following price_repo pattern: get_signals_for_asset(), get_latest_signals(), upsert_signals()

### Claude's Discretion
- Exact zone thresholds for each indicator (e.g., RSI <30 → +0.8 or +0.7)
- Exact indicator weight values (starting point, user can tune via config)
- BaseEngine abstract class implementation details
- Auto-ARIMA parameter bounds and fitting strategy
- Hurst exponent calculation method (R/S analysis vs DFA)
- SignalRepository method signatures and query patterns
- Analyze stage orchestration within PipelineRunner
- Error handling and logging for individual engine failures

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Architecture & Engine Interface
- `plan/ARCHITECTURE.md` §Core Interfaces — Signal dataclass, Decision dataclass, BaseEngine abstract class with analyze(), category, supports_stocks, supports_crypto, required_sources
- `plan/ARCHITECTURE.md` §Database Schema — signals table definition with all columns, data retention (1 year for signals)
- `plan/ARCHITECTURE.md` §Project Structure — `src/engines/` directory layout, one file per engine category
- `plan/ARCHITECTURE.md` §Concurrency Model — Engine execution is CPU-bound, must run synchronously (no asyncio.gather)
- `plan/ARCHITECTURE.md` §Daily Execution Flow — Stage 3 (ANALYZE) processes one asset at a time through all engines, releases DataFrames + gc.collect()

### Data Layer (Phase 2 foundation)
- `.planning/phases/02-data-layer/02-CONTEXT.md` — Price data is in price_history hypertable, fetched via ingest stage, PriceHistory model in models.py
- `src/db/price_repo.py` — PriceRepository pattern to follow for SignalRepository
- `src/db/models.py` — Existing models (Asset, PipelineRun, PipelineAssetRun, PriceHistory) that engines and signals will reference

### Pipeline Infrastructure (Phase 1 foundation)
- `.planning/phases/01-foundation/01-CONTEXT.md` — Pipeline runner, per-asset checkpointing, StageFunc interface, structlog logging
- `src/pipeline/runner.py` — PipelineRunner with run_stage(), StageFunc type alias, per-asset timeout handling
- `src/config.py` — Settings with timeout values, to be extended with indicator weights

### Project Decisions
- `.planning/PROJECT.md` §Key Decisions — Sequential engine execution per asset, asyncpg for hot paths
- `.planning/PROJECT.md` §Constraints — pandas-ta-classic for technical indicators, 1GB peak RAM budget

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/pipeline/runner.py` — PipelineRunner with StageFunc interface; analyze stage plugs in as a StageFunc
- `src/db/price_repo.py` — PriceRepository pattern (async methods, session-based) to replicate for SignalRepository
- `src/db/models.py` — Base ORM class with naming conventions, Asset model with asset_type field for stock/crypto branching
- `src/data/base.py` — BaseFetcher abstract class as reference pattern for BaseEngine design
- `src/config.py` — pydantic-settings Settings class to extend with indicator weight configs
- `src/pipeline/tiers.py` — SourceCriticalError for graceful degradation pattern

### Established Patterns
- SQLAlchemy async ORM with asyncpg driver for all DB operations
- Per-asset-per-stage checkpointing via PipelineAssetRun records
- pydantic-settings for configuration with .env support
- structlog for JSON logging with component binding
- Alembic for database migrations (001_initial_schema, 002_price_history_hypertables exist)

### Integration Points
- Analyze stage plugs into PipelineRunner.run_pipeline() as stage_funcs["analyze"]
- Signal model needs Alembic migration (003_signals_table)
- price_history data read from DB via PriceRepository → converted to DataFrame for pandas-ta
- Engine outputs stored as Signal rows in signals table via SignalRepository

</code_context>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches. Follow ARCHITECTURE.md BaseEngine interface pattern. Use pandas-ta-classic for all technical indicator computation.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 03-technical-engine-pipeline-shell*
*Context gathered: 2026-03-23*
