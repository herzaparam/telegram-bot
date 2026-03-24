# Phase 6: Accuracy Tracking + Scorecard - Context

**Gathered:** 2026-03-24
**Status:** Ready for planning

<domain>
## Phase Boundary

The system compares yesterday's decisions against actual prices every morning and reports honest accuracy stats. Covers: evaluate stage function, multi-window evaluation (24h, 3d, 7d, 30d), per-engine accuracy tracking, accuracy_stats computation, /scorecard command, yesterday's scorecard section in daily report. Does NOT include: LLM self-analysis of mistakes (Phase 7), lesson extraction (Phase 7), lesson injection (Phase 7), /lessons command (Phase 7).

</domain>

<decisions>
## Implementation Decisions

### Correctness Criteria
- **D-01:** Direction-based classification — BUY/STRONG BUY correct if price went up, SELL/STRONG SELL correct if price went down
- **D-02:** Asset-specific HOLD bands — stocks: ±2%, crypto: ±5%. HOLD is correct if price stayed within the band, wrong if it moved outside
- **D-03:** Multi-window evaluation at 24h, 3d, 7d, and 30d intervals. Each decision gets evaluated at all four windows as they mature
- **D-04:** HOLD threshold scales with window length. Longer windows get wider bands (e.g., stocks: ±2% at 24h, ±3% at 3d, ±5% at 7d, ±8% at 30d). Claude to pick reasonable scaling for crypto bands too
- **D-05:** Per-engine accuracy tracked independently — each engine's score direction compared against actual price movement. Enables best/worst engine stats in scorecard and feeds Phase 7's feedback loop

### Evaluation Windows & Timing
- **D-06:** IDX trading calendar via static holiday table in database. Pre-populate known IDX holidays for the year. Non-holiday weekdays are trading days. Manually update once/year
- **D-07:** Crypto evaluation uses exact 24h snapshot — find the closest price from `price_history_hourly` table 24 hours after `decision_price_at` timestamp. Not daily close
- **D-08:** For multi-day crypto windows (3d, 7d, 30d), use hourly candle closest to the exact N*24h mark after decision
- **D-09:** Evaluate what's ready each morning, skip pending windows. 24h decisions evaluated next day, 7-day decisions after 7 days, etc. No backfill of missed evaluations
- **D-10:** Decision price (`decision_price`, `decision_price_at`) captured during the decide stage (Phase 4), not during evaluation. Evaluation stage only fills `evaluation_price` fields. Prevents look-ahead bias
- **D-11:** Evaluate stage runs as the FIRST pipeline stage each morning (before ingest), per ARCHITECTURE.md daily flow

### Scorecard Command (/scorecard)
- **D-12:** Default display: multi-window summary showing win rate for each evaluation window (24h, 3d, 7d, 30d), total decisions, best/worst engine (by 24h accuracy), and per-asset buy-and-hold comparison
- **D-13:** Command syntax: `/scorecard [period] [asset]` — optional period (7d, 30d, 90d, all; default 30d) and optional asset filter (BTC, BBCA, etc.)
- **D-14:** Buy-and-hold baseline calculated per-asset over the scorecard period. Compare signal-based return vs simply holding each asset

### Daily Report Scorecard Section
- **D-15:** Per-asset results in the daily report — each asset shows verdict, price change %, and correct/wrong emoji (e.g., "✅ BTC — BUY → +3.2%")
- **D-16:** Separate sections per evaluation window that matured. Yesterday's 24h results first, then 7-day results for decisions from 7 days ago, etc.
- **D-17:** Brief trend line included: "Trending: 68% win rate this week (↑ from 60% last week)"
- **D-18:** When no prior decisions exist (first day), skip the scorecard section entirely — report starts with today's signals
- **D-19:** All report text in English (carrying forward Phase 5 D-05)

### Claude's Discretion
- Exact HOLD threshold scaling values for each window and asset type
- `evaluations` table schema details (can follow ARCHITECTURE.md's design or adapt)
- `accuracy_stats` table schema and computation logic
- IDX holiday data source and initial population approach
- Evaluate stage implementation as StageFunc or post-pipeline hook
- How to query hourly candles for exact 24h crypto snapshots
- Error handling when evaluation prices are unavailable (missing data)
- /scorecard message formatting and Telegram message splitting
- Buy-and-hold return calculation method

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Architecture & Evaluation Design
- `plan/ARCHITECTURE.md` — Full system architecture, Stage 6: EVALUATE in daily execution flow, `evaluations` table schema, `accuracy_stats` table schema, `lessons` table (Phase 7 but adjacent)
- `plan/ARCHITECTURE.md` §Daily Execution Flow — Stage 1 (EVALUATE) runs at 06:00 before data ingest, compares verdicts vs actual prices

### Decision Storage (Phase 4 output)
- `src/db/models.py` — `DailyDecision` model with `decision_price`, `decision_price_at`, `evaluation_price`, `evaluation_price_at` columns (look-ahead bias prevention from Phase 1)
- `src/db/decision_repo.py` — `DecisionRepository` with `save_decision()` and `get_decision()` methods
- `src/db/migrations/versions/001_initial_schema.py` — Initial migration including `daily_decisions` table with evaluation price columns

### Price Data (evaluation source)
- `src/db/price_repo.py` — Raw asyncpg OHLCV repository for querying evaluation prices
- `src/db/models.py` — `PriceHistory` (daily) and `PriceHistoryHourly` (hourly candles) models
- `src/db/migrations/versions/002_price_history_hypertables.py` — TimescaleDB hypertable setup

### Signal Data (per-engine tracking)
- `src/engines/base.py` — `BaseEngine` ABC, `Signal` dataclass (score, confidence, reasoning, indicators)
- `src/db/signal_repo.py` — `SignalRepository` for reading per-engine signals
- `src/db/models.py` — `Signal` model in signals table (engine_name, score, confidence per asset per date)

### Pipeline Infrastructure
- `src/pipeline/runner.py` — `PipelineRunner` with `StageFunc` interface, per-asset checkpointing
- `src/pipeline/main.py` — Stage registration (`stage_funcs` dict), CLI entry point

### Bot & Report Infrastructure
- `src/bot/handlers/report.py` — Report command handlers (existing pattern for /scorecard handler)
- `src/report/formatter.py` — Shared report formatter (add scorecard section rendering here)
- `src/data/report.py` — Pipeline report stage (add scorecard data injection here)

### Prior Phase Context
- `.planning/phases/04-llm-decision-maker/04-CONTEXT.md` — D-06: JSON schema for verdict output, D-12-16: Fallback behavior
- `.planning/phases/05-telegram-bot-daily-delivery/05-CONTEXT.md` — D-05: English only, D-06: Compact card format, D-07: Market overview header, D-08: Message splitting

### Requirements
- `.planning/REQUIREMENTS.md` — EVAL-01 (evaluate vs actual prices), EVAL-05 (accuracy stats), TBOT-04 (/scorecard), REPT-01 (yesterday's scorecard in report)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/db/models.py` — `DailyDecision` already has `decision_price`, `decision_price_at`, `evaluation_price`, `evaluation_price_at` columns ready for this phase
- `src/db/decision_repo.py` — `DecisionRepository` pattern for reading/writing decisions. Extend for evaluation queries
- `src/db/price_repo.py` — Raw asyncpg repository for querying price data. Use for evaluation price lookups
- `src/db/signal_repo.py` — `SignalRepository` pattern for reading per-engine signals. Use for per-engine accuracy computation
- `src/report/formatter.py` — Shared report formatter between bot and pipeline. Add scorecard section rendering here
- `src/bot/handlers/report.py` — Existing bot command handler pattern. Follow for `/scorecard` handler

### Established Patterns
- StageFunc signature: `async def evaluate_stage(session: AsyncSession, asset: Asset) -> None`
- Per-asset error isolation: failures produce fallback behavior, never crash pipeline
- structlog with component binding for logging
- pydantic-settings for configuration (thresholds, bands)
- Two-process boundary: bot MUST NOT import from `src/pipeline` or `src/llm`
- Alembic for all schema migrations
- HTML parse_mode for Telegram messages (Phase 5 D-01)

### Integration Points
- Evaluate stage plugs into PipelineRunner as `stage_funcs["evaluate"]` in `src/pipeline/main.py` — runs BEFORE ingest
- Reads from `daily_decisions` table (decisions to evaluate) and `price_history`/`price_history_hourly` tables (actual prices)
- Writes to new `evaluations` table and updates `evaluation_price`/`evaluation_price_at` on `daily_decisions`
- New `accuracy_stats` table computed after evaluations complete
- New `idx_holidays` table for IDX trading calendar
- `/scorecard` handler reads from `accuracy_stats` and `evaluations` tables via bot-side repository
- Report formatter enhanced with scorecard section that reads evaluation results

</code_context>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches. Follow existing patterns (StageFunc, per-asset processing, structlog logging, Alembic migrations).

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 06-accuracy-tracking-scorecard*
*Context gathered: 2026-03-24*
