---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
status: Ready to execute
stopped_at: Completed 10-04-PLAN.md
last_updated: "2026-03-25T17:43:12.037Z"
progress:
  total_phases: 12
  completed_phases: 9
  total_plans: 32
  completed_plans: 30
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-23)

**Core value:** The daily signal loop must work reliably: fetch data, run engines, produce LLM verdicts, and deliver a Telegram report every morning
**Current focus:** Phase 10 — remaining-specialized-engines

## Current Position

Phase: 10 (remaining-specialized-engines) — EXECUTING
Plan: 4 of 5

## Performance Metrics

**Velocity:**

- Total plans completed: 0
- Average duration: —
- Total execution time: 0 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| - | - | - | - |

**Recent Trend:**

- Last 5 plans: —
- Trend: —

*Updated after each plan completion*
| Phase 01 P01 | 8min | 2 tasks | 19 files |
| Phase 01 P03 | 3min | 2 tasks | 9 files |
| Phase 01-foundation P02 | 5min | 2 tasks | 6 files |
| Phase 02 P01 | 6min | 2 tasks | 11 files |
| Phase 02 P02 | 17min | 2 tasks | 14 files |
| Phase 03 P01 | 4min | 2 tasks | 11 files |
| Phase 03 P03 | 3min | 2 tasks | 2 files |
| Phase 03 P02 | 4min | 2 tasks | 2 files |
| Phase 03 P04 | 3min | 2 tasks | 3 files |
| Phase 04 P01 | 5min | 2 tasks | 8 files |
| Phase 04 P02 | 2min | 1 tasks | 2 files |
| Phase 05 P01 | 4min | 2 tasks | 9 files |
| Phase 05 P03 | 3min | 2 tasks | 4 files |
| Phase 05 P02 | 3min | 2 tasks | 12 files |
| Phase 06 P01 | 6min | 2 tasks | 9 files |
| Phase 06 P02 | 5min | 2 tasks | 6 files |
| Phase 07 P01 | 6min | 2 tasks | 8 files |
| Phase 07 P02 | 6min | 2 tasks | 11 files |
| Phase 08 P01 | 2min | 2 tasks | 5 files |
| Phase 08 P02 | 5min | 2 tasks | 11 files |
| Phase 08 P03 | 8min | 2 tasks | 10 files |
| Phase 08 P04 | 11min | 2 tasks | 7 files |
| Phase 09 P01 | 3min | 2 tasks | 5 files |
| Phase 09 P03 | 4min | 1 tasks | 2 files |
| Phase 09 P02 | 5min | 2 tasks | 3 files |
| Phase 09 P04 | 6min | 2 tasks | 5 files |
| Phase 09 P05 | 7min | 2 tasks | 10 files |
| Phase 10 P01 | 4min | 2 tasks | 7 files |
| Phase 10 P02 | 7min | 2 tasks | 10 files |
| Phase 10 P04 | 5min | 2 tasks | 9 files |

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- [Pre-Phase 1]: Replace APScheduler 4.x with system cron — APScheduler 4 is still in alpha (no stable release); system cron is strictly more reliable for a single daily trigger
- [Pre-Phase 1]: Use pandas-ta-classic (v0.4.47) — original pandas-ta maintainer warned of archival by July 2026; community fork is drop-in compatible and actively maintained
- [Pre-Phase 1]: Two-process model enforced — bot process never imports pipeline modules; PostgreSQL is the sole integration bus; mandatory for 2GB VPS RAM budget
- [Phase 01]: Used trade_dev as default DB password matching Docker Compose
- [Phase 01]: Separate pipeline_asset_runs table for per-asset-per-stage checkpointing
- [Phase 01]: SQLAlchemy naming conventions on Base metadata for reversible Alembic migrations
- [Phase 01]: LLM wrapper catches all exceptions and returns LLM_UNAVAILABLE -- never crashes the pipeline
- [Phase 01]: Pipeline service uses Docker Compose profiles -- only runs when explicitly triggered
- [Phase 01-foundation]: Unknown data sources default to SUPPLEMENTARY tier (safe default)
- [Phase 01-foundation]: Per-asset processing uses individual DB sessions to prevent cross-asset rollback
- [Phase 01-foundation]: aiosqlite + JSONB-to-JSON swap for async SQLite unit test fixtures
- [Phase 02]: asyncpg conn typed as Any to avoid missing py.typed stubs
- [Phase 02]: Migration smoke tests use inspect.getsource() for DDL verification without TimescaleDB
- [Phase 02]: structlog.testing.capture_logs() for log assertions in tests
- [Phase 02]: tenacity wait_none() in tests for fast retry testing
- [Phase 02]: CoinGecko OHLC fallback sets volume=0, tagged source=coingecko
- [Phase 02]: Monday detection for weekly re-fetch trigger
- [Phase 03]: SignalRepository uses SQLAlchemy ORM with pg_insert for UPSERT (not raw asyncpg)
- [Phase 03]: Signal dataclass is frozen for immutability after engine computation
- [Phase 03]: signals table is regular PostgreSQL (not hypertable) — low-volume relational data
- [Phase 03]: Lazy import of pmdarima inside _arima_forecast to avoid loading heavy ML stack until needed
- [Phase 03]: Regime detection thresholds at H>0.55 trending, H<0.45 mean-reverting (0.05 buffer around 0.5)
- [Phase 03]: Zone thresholds: RSI <20/30/45/55/70/80 mapped to scores, EMA shorter periods weighted more
- [Phase 03]: pandas_ta_classic must be imported at module level to register .ta DataFrame accessor
- [Phase 03]: analyze_stage follows StageFunc(session, asset) pattern -- per-engine error isolation with _failed_signal fallback
- [Phase 03]: DataFrame memory released with del + gc.collect() after each asset to stay within 1GB RAM
- [Phase 04]: response_format passed via kwargs dict to litellm.acompletion for clean JSON mode support
- [Phase 04]: timeout_decide_per_call=12s per LLM call so initial + retry fits within 30s stage timeout
- [Phase 04]: Contradiction detection uses D-08 thresholds: score >+0.3/<-0.3 and confidence >0.5
- [Phase 04]: Fallback confidence capped at 0.5 with spread-based calculation
- [Phase 05]: HTML parse_mode for Telegram messages (avoids MarkdownV2 escape issues with financial data)
- [Phase 05]: Formatter in src/report/ shared by both bot and pipeline processes (not duplicated)
- [Phase 05]: Reasoning truncation at word boundary with 100-char limit for compact cards
- [Phase 05]: Report stage runs as post-pipeline hook (not StageFunc) since it aggregates across all assets
- [Phase 05]: httpx for Telegram API in pipeline (not PTB) per D-16 two-process boundary
- [Phase 05]: PTB Application with updater(None) and lifespan context manager for FastAPI integration
- [Phase 05]: Lazy imports of yfinance/ccxt in validation functions with run_in_executor for async safety
- [Phase 06]: Evaluation uses SQLAlchemy ORM (not raw asyncpg) matching decision_repo pattern
- [Phase 06]: HOLD bands scale per window: stock 2%/3%/5%/8%, crypto 5%/8%/12%/20%
- [Phase 06]: evaluate_stage as first pipeline stage before fetch; catches all exceptions (error isolation)
- [Phase 06]: EvalDisplayItem frozen dataclass for type-safe evaluation display items
- [Phase 06]: Scorecard section prepended to daily report header with --- separator
- [Phase 06]: Asset filter resolved via Watchlist join (only watchlisted assets valid for /scorecard)
- [Phase 07]: Lesson scoring weights: recency 0.25, accuracy 0.30, asset-type 0.25, engine relevance 0.20
- [Phase 07]: Tier promotion thresholds: hypothesis <10, pattern 10-29, rule >=30 observations
- [Phase 07]: Reflect stage placed after evaluate, before fetch in pipeline ordering
- [Phase 07]: Batch cross-cutting runs post-pipeline as separate function, not StageFunc
- [Phase 07]: Lessons split into ASSET-SPECIFIC and GENERAL sections in LLM prompt
- [Phase 07]: /lessons command uses same positional arg filter pattern as /scorecard
- [Phase 08]: Phase 08-01: API keys default to empty string (not None) so Settings always instantiates; fetcher engines degrade gracefully when missing
- [Phase 08]: Phase 08-01: StockFundamental unique on asset_id (one cached record per asset, weekly upsert); MacroData unique on (series_id, observation_date) for safe backfill
- [Phase 08]: Phase 08-02: SentimentSnapshot not stored in DB -- passed directly to SentimentEngine as constructor arg
- [Phase 08]: Phase 08-02: session.add() for NewsEvent INSERT (URL dedup happens before); pg_insert used for StockFundamental and MacroData UPSERT
- [Phase 08]: FundamentalEngine returns score=0/confidence=0 with 'not applicable for crypto' when fundamentals=None (D-03)
- [Phase 08]: MacroEngine uses _is_stock_symbol() heuristic to differentiate IDX stocks from crypto for reasoning emphasis
- [Phase 08]: SentimentEngine duck-types SentimentSnapshot via getattr() to avoid circular imports
- [Phase 08]: analyze_stage loads fundamentals only for stock assets (conditional check before _load_fundamentals)
- [Phase 08]: _sentiment_cache module global in analyze.py, set by fetch_global_data -- avoids DB storage for ephemeral SentimentSnapshot
- [Phase 08]: News digest appended as last card in report cards list (D-19 bottom-of-report placement)
- [Phase 09]: httpx.AsyncClient with 30s timeout for IDX API and PDF downloads; 1s sleep between requests for rate limiting
- [Phase 09]: Bear scenario uses (1-cagr-std_dev) multiplier for bull>base>bear ordering
- [Phase 09]: Vision fallback triggers at <500 chars extracted text threshold
- [Phase 09]: GPT-4o used for vision fallback (not GPT-4o-mini which lacks vision)
- [Phase 09]: QoQ thresholds: 3pp for margins, 10% for revenue/profit, 15% for debt/cashflow
- [Phase 09]: Cross-validation compares PDF-extracted revenue/net_profit vs yfinance with 10% threshold
- [Phase 09]: Bot reads valuation data from signals table indicators JSONB, not engine imports (two-process boundary)
- [Phase 09]: ValuationEngine stores enriched indicators dict with fair_value, peer_comparison, sector, has_pdf_data for bot consumption
- [Phase 10]: mypy overrides added for xgboost, onnxmltools, pywt (no py.typed stubs)
- [Phase 10]: Stub engines document future data sources in data_quality.todo field
- [Phase 10]: NetworkEngine receives pre-computed correlation_data via constructor (same as MacroEngine pattern)
- [Phase 10]: EmergingMethodsEngine implements own _hurst_exponent locally to avoid circular imports
- [Phase 10]: PyWavelets (pywt) added as dependency for wavelet decomposition
- [Phase 10]: Separated _create_session factory for testability of ONNX inference

### Pending Todos

None yet.

### Blockers/Concerns

- [Research]: yfinance IDX delta-fetch reliability for .JK suffix tickers needs prototyping early in Phase 2 to confirm date-range queries work reliably
- [Research]: LLM prompt token budget with all 15 engines active may approach GPT-4o-mini context limits — prompt truncation strategy needed before Phase 10
- [Research]: IDX trading calendar (holidays, halts) required for correct evaluation windows in Phase 6; no free API identified — may need static calendar in database

## Session Continuity

Last session: 2026-03-25T17:43:12.033Z
Stopped at: Completed 10-04-PLAN.md
Resume file: None
