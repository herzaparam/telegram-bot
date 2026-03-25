# Phase 10: Remaining Specialized Engines - Context

**Gathered:** 2026-03-25
**Status:** Ready for planning

<domain>
## Phase Boundary

Build the remaining 8 engines to complete the full 15-engine suite: ML/AI prediction (ENGN-04), on-chain crypto (ENGN-06), options flow (ENGN-07), behavioral anomaly (ENGN-08), alternative data (ENGN-10), network/graph (ENGN-11), game theory order book (ENGN-13), and emerging methods (ENGN-14). All follow the existing BaseEngine contract. Engines wire into _get_engines_for_asset() in analyze.py. Stub engines for options and game theory where data sources are unavailable. Does NOT include: asset discovery (Phase 11), due diligence (Phase 11), portfolio risk (Phase 12), or new Telegram commands beyond /scorecard updates.

</domain>

<decisions>
## Implementation Decisions

### ML/AI Engine (ENGN-04)
- **D-01:** Price-derived features only — use existing OHLCV data to generate features (returns, volatility, RSI, MACD, volume ratios, lagged values). No external feature sources, keeps it self-contained
- **D-02:** Offline train, ONNX deploy — training scripts (CLI) generate ONNX models from historical data. Users retrain manually when performance degrades. Matches PROJECT.md ONNX decision
- **D-03:** One model per asset class — one XGBoost + one LSTM for stocks, one of each for crypto. 4 total ONNX models. Fits RAM budget easily
- **D-04:** Include both inference code and training scripts as end-to-end deliverable
- **D-05:** Predict direction + magnitude — next-day return direction and estimated magnitude. Score maps to -1/+1 range, confidence from model probability
- **D-06:** Weighted average ensemble — 60% XGBoost, 40% LSTM. Confidence = min of both model confidences. Transparent and easy to tune

### On-Chain Engine (ENGN-06)
- **D-07:** DeFiLlama for TVL (free, no auth) + CoinGecko for exchange flow data (free tier, already used). No paid APIs needed
- **D-08:** Exchange flow proxy for whale tracking — track net exchange inflows/outflows. Large inflows = sell pressure, outflows = accumulation. Available from aggregated data
- **D-09:** On-chain engine focuses on TVL, exchange flows, whale activity. Leave NVT to ValuationEngine. Clean separation, no duplicate signals
- **D-10:** Support BTC + ETH + SOL — the 3 most common watchlist cryptos. DeFiLlama has TVL for all three ecosystems
- **D-11:** TVL trend + ratio scoring — track TVL 7-day and 30-day trends. Rising TVL = bullish, falling = bearish. Market cap / TVL ratio for relative valuation
- **D-12:** Daily fetch with pipeline — on-chain data fetched during daily pipeline run alongside other fetchers

### Options Engine (ENGN-07) — Stub
- **D-13:** Documented stub — returns score=0/confidence=0 with reasoning "Options flow data not available for IDX market". Includes TODO comments with data sources that would enable real implementation (Deribit for crypto options, etc.)

### Behavioral Anomaly Engine (ENGN-08)
- **D-14:** Detect volume + price anomalies — unusual volume spikes (>2 std dev), price gap anomalies, and volume/price divergence (rising price on falling volume). All derivable from existing OHLCV data

### Alternative Data Engine (ENGN-10)
- **D-15:** GitHub activity only for crypto — track commit frequency, contributor count, and repo stars for major crypto projects via GitHub API. Rising dev activity = bullish signal. Returns score=0/confidence=0 for stocks (not applicable)

### Network/Graph Engine (ENGN-11)
- **D-16:** Rolling correlation matrix — compute rolling 30-day pairwise correlations across all watchlist assets. Signal when an asset's correlations spike or break (regime change). Uses only existing price data

### Game Theory Order Book Engine (ENGN-13) — Stub
- **D-17:** Documented stub — returns score=0/confidence=0 with reasoning "Real-time order book data not available in daily cadence pipeline". Includes TODO comments for future Binance WebSocket integration

### Emerging Methods Engine (ENGN-14)
- **D-18:** Fractal dimension (Hurst exponent) for trend/mean-reversion detection + wavelet decomposition for multi-scale trend analysis. Both work on price data, no external sources needed

### Data Fetcher Wiring
- **D-19:** Extend existing ingest stage — add on-chain and GitHub fetchers as sub-steps alongside price/macro/news fetchers. Same pattern as Phase 8. Data cached in new DB tables, engines read from DB
- **D-20:** 2-3 new tables: on_chain_data (TVL, exchange flows per asset), github_activity (repo metrics per project), ml_predictions (cached model outputs). Minimal schema expansion
- **D-21:** One Alembic migration per table — separate migrations for on_chain_data, github_activity, ml_predictions. Clean rollback per feature

### Memory & Performance
- **D-22:** Lazy load ONNX models — load only during ML engine's analyze(), release after. Other engines use lightweight computations. Add memory measurement test asserting peak < 1GB

### API Keys & Configuration
- **D-23:** Same pattern as Phase 8 — add to Settings class, optional with graceful degradation. DeFiLlama needs no key. GitHub API works without auth (60 req/hour) or with optional GITHUB_TOKEN (5000 req/hour)

### Scorecard Integration
- **D-24:** All 15 engines appear in /scorecard. Stub engines (options, game theory) show "N/A - data source unavailable" instead of accuracy %. Real engines show actual accuracy. Transparent to user

### Claude's Discretion
- XGBoost feature engineering specifics (which lagged features, window sizes)
- LSTM architecture (layers, hidden size, sequence length)
- Training script CLI interface and hyperparameter defaults
- DeFiLlama and CoinGecko endpoint selection and parsing
- GitHub repo mapping (which repos represent which crypto projects)
- Volume anomaly detection thresholds and scoring weights
- Correlation matrix computation method and regime change thresholds
- Hurst exponent and wavelet implementation details (library choice: pywt vs scipy)
- On-chain and GitHub data table column schemas and indexes
- How to wire 8 new engines into _get_engines_for_asset() in analyze.py
- Error handling and retry logic for new API calls

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Engine contract
- `src/engines/base.py` — BaseEngine ABC and Signal dataclass. All 8 new engines must follow this contract
- `src/data/analyze.py` lines 36-69 — _get_engines_for_asset() function where new engines must be registered

### Existing engine implementations (patterns to follow)
- `src/engines/technical.py` — TechnicalEngine, reference for OHLCV-only engines (behavioral, emerging methods)
- `src/engines/macro.py` — MacroEngine, reference for DB-cached data pattern (on-chain, GitHub)
- `src/engines/sentiment.py` — SentimentEngine, reference for external API fetcher pattern
- `src/engines/valuation.py` — ValuationEngine, reference for constructor-injected data pattern

### Pipeline and data layer
- `src/data/ingest.py` — Ingest stage where new fetchers will be added
- `src/pipeline/runner.py` — PipelineRunner with per-asset checkpointing
- `src/pipeline/tiers.py` — DataTier enum for source failure classification
- `src/config.py` — Settings class where new API keys are added

### Project constraints
- `.planning/PROJECT.md` — ONNX Runtime decision, 1GB RAM budget, sequential execution
- `.planning/REQUIREMENTS.md` — ENGN-04, ENGN-06, ENGN-07, ENGN-08, ENGN-10, ENGN-11, ENGN-13, ENGN-14 requirements

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `BaseEngine` ABC (`src/engines/base.py`): Well-defined contract — `analyze(asset_id, symbol, df) -> Signal` with `supports_stocks`/`supports_crypto` properties
- 7 existing engine implementations: TechnicalEngine, QuantitativeEngine, FundamentalEngine, MacroEngine, SentimentEngine, EventEngine, ValuationEngine — all follow identical patterns
- `_get_engines_for_asset()` in `analyze.py`: Central registry function — new engines just get appended to `all_engines` list
- `_failed_signal()` helper in `analyze.py`: Standard error signal factory for engine failures
- Existing fetcher pattern: `BaseFetcher` ABC in `src/data/base.py`, tenacity retry, tier-based failure handling

### Established Patterns
- **Fetch-then-analyze separation:** Fetchers run during ingest stage, store in DB. Engines read from DB during analyze stage. No engine should fetch its own data
- **Constructor injection:** Engines receive pre-fetched data via constructor (e.g., `MacroEngine(macro_data=...)`, `ValuationEngine(financial_data=...)`)
- **Graceful degradation:** Missing data = score=0/confidence=0, pipeline continues. Source tier system classifies failures
- **Sequential execution:** Engines run one at a time per asset in `_get_engines_for_asset()` return order

### Integration Points
- `_get_engines_for_asset()` in `analyze.py` — add 8 new engines to the `all_engines` list
- `ingest_stage()` in `ingest.py` — add on-chain and GitHub fetch sub-steps
- `Settings` class in `config.py` — add optional `GITHUB_TOKEN`
- `src/bot/commands/` — update `/scorecard` to show all 15 engines including stub status
- Alembic migrations — 3 new migration files for on_chain_data, github_activity, ml_predictions tables

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

*Phase: 10-remaining-specialized-engines*
*Context gathered: 2026-03-25*
