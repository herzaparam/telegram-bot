# Phase 6: Accuracy Tracking + Scorecard - Research

**Researched:** 2026-03-24
**Domain:** Evaluation logic, accuracy computation, trading calendar, Telegram reporting
**Confidence:** HIGH

## Summary

Phase 6 adds the self-evaluation loop: every morning the pipeline compares prior decisions against actual prices at multiple time windows (24h, 3d, 7d, 30d), tracks per-engine accuracy, exposes a `/scorecard` command, and prepends yesterday's scorecard to the daily report. This is a data-layer and presentation phase -- no LLM calls needed (LLM analysis is Phase 7), no new external APIs, no new heavy dependencies.

The core challenge is correctness: direction-based classification with asset-specific HOLD bands that scale per window, exact-hour crypto price lookups from `price_history_hourly`, IDX trading calendar awareness to avoid evaluating against non-trading days, and multi-window maturity tracking (only evaluate windows whose time has elapsed). The `DailyDecision` model already has `evaluation_price` / `evaluation_price_at` columns ready for the 24h primary evaluation. Multi-window evaluations need a new `evaluations` table. Per-engine accuracy needs an `accuracy_stats` table and an `engine_evaluations` tracking mechanism keyed on signals.

**Primary recommendation:** Implement as a new pipeline stage (`evaluate`) that runs BEFORE `fetch` in the stage ordering, with three new DB tables (`evaluations`, `accuracy_stats`, `idx_holidays`), a new `EvaluationRepository`, new scorecard formatting in `src/report/formatter.py`, and a new `/scorecard` bot handler.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Direction-based classification -- BUY/STRONG BUY correct if price went up, SELL/STRONG SELL correct if price went down
- **D-02:** Asset-specific HOLD bands -- stocks: +/-2%, crypto: +/-5%. HOLD is correct if price stayed within the band, wrong if it moved outside
- **D-03:** Multi-window evaluation at 24h, 3d, 7d, and 30d intervals. Each decision gets evaluated at all four windows as they mature
- **D-04:** HOLD threshold scales with window length. Longer windows get wider bands (e.g., stocks: +/-2% at 24h, +/-3% at 3d, +/-5% at 7d, +/-8% at 30d). Claude to pick reasonable scaling for crypto bands too
- **D-05:** Per-engine accuracy tracked independently -- each engine's score direction compared against actual price movement. Enables best/worst engine stats in scorecard and feeds Phase 7's feedback loop
- **D-06:** IDX trading calendar via static holiday table in database. Pre-populate known IDX holidays for the year. Non-holiday weekdays are trading days. Manually update once/year
- **D-07:** Crypto evaluation uses exact 24h snapshot -- find the closest price from `price_history_hourly` table 24 hours after `decision_price_at` timestamp. Not daily close
- **D-08:** For multi-day crypto windows (3d, 7d, 30d), use hourly candle closest to the exact N*24h mark after decision
- **D-09:** Evaluate what's ready each morning, skip pending windows. 24h decisions evaluated next day, 7-day decisions after 7 days, etc. No backfill of missed evaluations
- **D-10:** Decision price (`decision_price`, `decision_price_at`) captured during the decide stage (Phase 4), not during evaluation. Evaluation stage only fills `evaluation_price` fields. Prevents look-ahead bias
- **D-11:** Evaluate stage runs as the FIRST pipeline stage each morning (before ingest), per ARCHITECTURE.md daily flow
- **D-12:** Default display: multi-window summary showing win rate for each evaluation window (24h, 3d, 7d, 30d), total decisions, best/worst engine (by 24h accuracy), and per-asset buy-and-hold comparison
- **D-13:** Command syntax: `/scorecard [period] [asset]` -- optional period (7d, 30d, 90d, all; default 30d) and optional asset filter (BTC, BBCA, etc.)
- **D-14:** Buy-and-hold baseline calculated per-asset over the scorecard period. Compare signal-based return vs simply holding each asset
- **D-15:** Per-asset results in the daily report -- each asset shows verdict, price change %, and correct/wrong emoji
- **D-16:** Separate sections per evaluation window that matured. Yesterday's 24h results first, then 7-day results for decisions from 7 days ago, etc.
- **D-17:** Brief trend line included: "Trending: 68% win rate this week (up from 60% last week)"
- **D-18:** When no prior decisions exist (first day), skip the scorecard section entirely -- report starts with today's signals
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

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| EVAL-01 | System reviews yesterday's decisions against actual prices every morning | Evaluate stage as first pipeline stage, direction-based classification, multi-window maturity tracking, IDX calendar, hourly crypto lookups |
| EVAL-05 | System tracks accuracy stats over time (win rate, best/worst engine) | `accuracy_stats` table, per-engine evaluation via `engine_evaluations` or signals-based computation, recomputed after each evaluation run |
| TBOT-04 | `/scorecard` shows accuracy stats + recent results | New bot handler following existing `report_handler` pattern, reads from `evaluations` + `accuracy_stats` tables |
| REPT-01 | Yesterday's scorecard (was I right/wrong, accuracy stats) | Scorecard section prepended to daily report via `format_scorecard_section()` in shared formatter |
</phase_requirements>

## Project Constraints (from CLAUDE.md)

- **Two-process boundary:** Bot MUST NOT import from `src/pipeline` or `src/llm`. Scorecard handler reads from DB only.
- **Alembic for all schema migrations:** New tables require a numbered migration file.
- **StageFunc signature:** `async def evaluate_stage(session: AsyncSession, asset: Asset) -> None`
- **Per-asset error isolation:** Evaluation failures produce fallback behavior, never crash pipeline.
- **structlog with component binding** for all logging.
- **pydantic-settings** for any new configuration thresholds.
- **HTML parse_mode** for all Telegram messages.
- **Python 3.13, uv, mypy strict, ruff.**
- **Frozen dataclasses** for immutable result types.
- **Google-style docstrings** with Args/Returns.
- **SQLAlchemy ORM with pg_insert UPSERT** for repository pattern.

## Standard Stack

### Core (no new dependencies needed)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| SQLAlchemy[asyncio] | 2.0.48+ | ORM for evaluations/accuracy_stats tables | Already in project |
| asyncpg | 0.31.0+ | Raw queries for price lookups during evaluation | Already used for hot-path price queries |
| pydantic-settings | 2.13.1+ | HOLD threshold configuration | Already in project |
| structlog | 25.5.0+ | Logging | Already in project |
| python-telegram-bot | v20+ | `/scorecard` command handler | Already in project (bot process) |
| httpx | 0.28.1+ | Scorecard in pipeline report | Already used for pipeline Telegram sends |
| Alembic | 1.18.4+ | Migration for new tables | Already in project |

### Supporting
No new dependencies. This phase is pure application logic using the existing stack.

**Installation:** No new packages needed.

## Architecture Patterns

### Recommended Project Structure (new files)
```
src/
  data/
    evaluate.py          # evaluate_stage() StageFunc + evaluation logic
  db/
    evaluation_repo.py   # EvaluationRepository + AccuracyStatsRepository
    models.py            # Add Evaluation, AccuracyStats, IDXHoliday models
    migrations/versions/
      005_evaluations.py # New tables migration
  report/
    formatter.py         # Add scorecard formatting functions
  bot/
    handlers/
      scorecard.py       # /scorecard command handler
    main.py              # Register /scorecard handler
  config.py              # Add HOLD threshold settings
tests/
  test_data/
    test_evaluate.py     # Evaluate stage tests
  test_db/
    test_evaluation_repo.py  # Repository tests
  test_report/
    test_formatter.py    # Extend with scorecard format tests (file exists)
  test_bot/
    test_handlers.py     # Extend with scorecard handler tests (file exists)
```

### Pattern 1: Evaluate Stage as StageFunc
**What:** `evaluate_stage(session, asset)` runs as a per-asset pipeline stage before `fetch`
**When to use:** Every pipeline run
**Why StageFunc (not post-pipeline hook):** Unlike the report stage which aggregates across all assets, evaluation is per-asset and benefits from per-asset checkpointing/error isolation. If BTC evaluation fails, BBCA evaluation should still proceed.

```python
# src/data/evaluate.py
async def evaluate_stage(session: AsyncSession, asset: Asset) -> None:
    """Evaluate prior decisions for one asset at all mature windows."""
    run_date = date.today()
    windows = [
        EvalWindow("24h", timedelta(days=1)),
        EvalWindow("3d", timedelta(days=3)),
        EvalWindow("7d", timedelta(days=7)),
        EvalWindow("30d", timedelta(days=30)),
    ]
    for window in windows:
        target_date = run_date - window.delta
        decision = await decision_repo.get_decision(session, asset.id, target_date)
        if decision is None:
            continue
        # Check if already evaluated for this window
        existing = await eval_repo.get_evaluation(session, decision.id, window.name)
        if existing is not None:
            continue
        # Get evaluation price
        eval_price = await _get_evaluation_price(session, asset, decision, window)
        if eval_price is None:
            log.warning("eval_price_unavailable", asset=asset.symbol, window=window.name)
            continue
        # Classify result
        result = _classify_result(decision, eval_price, asset.asset_type, window.name)
        # Store evaluation
        await eval_repo.upsert_evaluation(session, decision.id, window.name, eval_price, result)
    # Recompute accuracy stats for this asset
    await _recompute_accuracy_stats(session, asset.id)
```

### Pattern 2: IDX Trading Calendar
**What:** Static holiday table queried to determine if a date is a trading day
**When to use:** When finding the "next trading day close" for IDX stock evaluation

```python
# src/data/evaluate.py
async def _get_next_trading_day(session: AsyncSession, after_date: date) -> date:
    """Find next IDX trading day after given date."""
    candidate = after_date + timedelta(days=1)
    for _ in range(10):  # max lookahead for holidays/weekends
        if candidate.weekday() < 5:  # Monday-Friday
            is_holiday = await _is_idx_holiday(session, candidate)
            if not is_holiday:
                return candidate
        candidate += timedelta(days=1)
    return candidate  # fallback
```

### Pattern 3: Direction-Based Classification with Scaled HOLD Bands
**What:** Pure function classifying verdict correctness against actual price movement

Recommended HOLD band scaling:

| Window | Stocks | Crypto |
|--------|--------|--------|
| 24h | +/-2% | +/-5% |
| 3d | +/-3% | +/-8% |
| 7d | +/-5% | +/-12% |
| 30d | +/-8% | +/-20% |

Rationale: Crypto is roughly 2.5x more volatile than IDX stocks. Window scaling uses approximately sqrt(N/1) growth factor, slightly compressed for longer windows to avoid overly generous bands.

```python
@dataclass(frozen=True)
class EvalResult:
    """Evaluation result for one decision at one window."""
    change_pct: float
    was_correct: bool
    eval_price: float
    eval_price_at: datetime

HOLD_BANDS: dict[str, dict[str, float]] = {
    "24h": {"stock": 0.02, "crypto": 0.05},
    "3d":  {"stock": 0.03, "crypto": 0.08},
    "7d":  {"stock": 0.05, "crypto": 0.12},
    "30d": {"stock": 0.08, "crypto": 0.20},
}

def _classify_result(
    verdict: str,
    decision_price: float,
    eval_price: float,
    asset_type: str,
    window: str,
) -> EvalResult:
    change_pct = (eval_price - decision_price) / decision_price
    band = HOLD_BANDS[window][asset_type]

    if verdict in ("BUY", "STRONG BUY"):
        was_correct = change_pct > 0
    elif verdict in ("SELL", "STRONG SELL"):
        was_correct = change_pct < 0
    elif verdict == "HOLD":
        was_correct = abs(change_pct) <= band
    else:
        was_correct = False

    return EvalResult(
        change_pct=change_pct,
        was_correct=was_correct,
        eval_price=eval_price,
        eval_price_at=...,
    )
```

### Pattern 4: Per-Engine Accuracy
**What:** Compare each engine's signal score direction against actual price movement
**How:** For each evaluation, look up the signals from the same asset+date. If signal score > 0 (bullish) and price went up, that engine was correct. Track in `engine_evaluations` or compute on-the-fly from signals+evaluations join.

Recommendation: Store per-engine correctness in the `evaluations` table as a JSONB column `engine_results` rather than a separate table. This avoids table explosion and keeps evaluation atomic.

```python
engine_results = {}
signals = await signal_repo.get_signals_for_asset(session, asset.id, decision.date)
for sig in signals:
    engine_correct = (sig.score > 0 and change_pct > 0) or (sig.score < 0 and change_pct < 0)
    engine_results[sig.category] = {
        "score": sig.score,
        "correct": engine_correct,
    }
```

### Pattern 5: Buy-and-Hold Baseline
**What:** Compare signal returns vs buy-and-hold over the scorecard period
**How:** For each asset in the period, compute cumulative return of following signals vs just holding. Buy-and-hold = (latest_price - earliest_price) / earliest_price over the period.

### Anti-Patterns to Avoid
- **Look-ahead bias:** NEVER use prices from after the decision time to compute `decision_price`. Evaluation only writes `evaluation_price` fields.
- **Evaluating unavailable windows:** Do NOT try to evaluate a 30-day window if only 7 days have elapsed. Check maturity first.
- **Blocking on missing data:** If hourly candle data is missing for crypto, log a warning and skip that evaluation -- do not crash.
- **Monolithic accuracy computation:** Do not scan all decisions every morning. Only evaluate newly-matured windows.
- **Importing pipeline from bot:** The `/scorecard` handler MUST query the database directly, never import evaluation logic.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| IDX trading calendar | Custom holiday API integration | Static `idx_holidays` table with manual yearly update | No free reliable IDX holiday API exists; static table is accurate and simple |
| Timezone handling | Manual UTC offset math | Python `datetime` with `timezone.utc` and `zoneinfo.ZoneInfo("Asia/Jakarta")` | Already in stdlib, handles DST (not relevant for WIB but still correct) |
| Percentage calculation | Complex float math | Simple `(eval - decision) / decision` | Standard financial return formula |
| Message splitting | Custom split logic | Existing `split_report()` in `src/report/formatter.py` | Already handles Telegram 4096-char limit |

## Common Pitfalls

### Pitfall 1: IDX Weekend/Holiday Evaluation
**What goes wrong:** Evaluating an IDX stock decision made on Friday against Saturday's price (which doesn't exist)
**Why it happens:** Naive "add 1 day" logic ignores weekends and holidays
**How to avoid:** Use `_get_next_trading_day()` that skips weekends and holidays from `idx_holidays` table
**Warning signs:** Missing evaluation prices for Friday decisions

### Pitfall 2: Hourly Candle Gaps
**What goes wrong:** No hourly candle exists exactly 24h after `decision_price_at` for crypto
**Why it happens:** `price_history_hourly` has 7-day rolling retention (per Phase 2), and candles may have gaps
**How to avoid:** Use "closest candle within +/-30 minutes of target time" query with `ORDER BY ABS(EXTRACT(EPOCH FROM time - target)) LIMIT 1`. If no candle within tolerance, skip evaluation.
**Warning signs:** Null evaluation prices for crypto assets

### Pitfall 3: Missing decision_price
**What goes wrong:** Phase 4 decide stage may not have populated `decision_price` / `decision_price_at` on older decisions
**Why it happens:** These columns were defined in Phase 1 schema but only populated from Phase 4 onward
**How to avoid:** Check `decision.decision_price is not None` before attempting evaluation. Skip decisions with null decision price.
**Warning signs:** Division by zero or null reference errors

### Pitfall 4: Evaluating Same Window Twice
**What goes wrong:** Pipeline re-run evaluates an already-evaluated window, overwriting correct results
**Why it happens:** No idempotency check on (decision_id, window) pair
**How to avoid:** UPSERT with `ON CONFLICT (decision_id, window) DO UPDATE` or check-before-insert. The UPSERT approach is cleaner and matches existing patterns.
**Warning signs:** Duplicate evaluation records

### Pitfall 5: HOLD Band Too Generous at Long Windows
**What goes wrong:** 30-day HOLD band of +/-20% for crypto means HOLD is almost always "correct"
**Why it happens:** Scaling bands linearly with time creates overly generous thresholds
**How to avoid:** Use sqrt-based scaling (recommended values above). Monitor and adjust based on actual data.
**Warning signs:** HOLD win rate near 100% at 30d window

### Pitfall 6: Stale Hourly Data for Multi-Day Crypto Windows
**What goes wrong:** 7d/30d crypto evaluations fail because `price_history_hourly` only keeps 7 days
**Why it happens:** Phase 2 hourly candle retention is 7 days rolling
**How to avoid:** For windows > 7 days, fall back to `price_history` daily close. Use hourly candles only for 24h and 3d windows. Document this compromise clearly.
**Warning signs:** All 7d+ crypto evaluations returning null

## Code Examples

### Database Schema: evaluations table

```sql
-- 005_evaluations.py migration
CREATE TABLE evaluations (
    id SERIAL PRIMARY KEY,
    decision_id INTEGER NOT NULL REFERENCES daily_decisions(id),
    window VARCHAR(5) NOT NULL,  -- '24h', '3d', '7d', '30d'
    eval_price NUMERIC(20, 8) NOT NULL,
    eval_price_at TIMESTAMPTZ NOT NULL,
    change_pct NUMERIC(8, 4) NOT NULL,
    was_correct BOOLEAN NOT NULL,
    engine_results JSONB,  -- per-engine correctness snapshot
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(decision_id, window)
);

CREATE TABLE accuracy_stats (
    id SERIAL PRIMARY KEY,
    asset_id INTEGER REFERENCES assets(id),  -- NULL for global stats
    engine_name VARCHAR(30),  -- NULL for overall stats
    window VARCHAR(5) NOT NULL,
    period VARCHAR(10) NOT NULL,  -- '7d', '30d', '90d', 'all'
    total INTEGER NOT NULL DEFAULT 0,
    correct INTEGER NOT NULL DEFAULT 0,
    win_rate NUMERIC(5, 2),
    computed_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(asset_id, engine_name, window, period)
);

CREATE TABLE idx_holidays (
    id SERIAL PRIMARY KEY,
    holiday_date DATE NOT NULL UNIQUE,
    name VARCHAR(100),
    year INTEGER NOT NULL
);

CREATE INDEX idx_evaluations_decision ON evaluations(decision_id);
CREATE INDEX idx_evaluations_created ON evaluations(created_at DESC);
CREATE INDEX idx_accuracy_stats_lookup ON accuracy_stats(asset_id, window, period);
CREATE INDEX idx_idx_holidays_date ON idx_holidays(holiday_date);
```

### Crypto Price Lookup (closest hourly candle)

```python
async def _get_crypto_eval_price(
    conn: Any,
    asset_id: int,
    target_time: datetime,
    table: str = "price_history_hourly",
    tolerance_minutes: int = 30,
) -> tuple[float, datetime] | None:
    """Find closest hourly candle to target time."""
    sql = f"""
        SELECT close, time
        FROM {table}
        WHERE asset_id = $1
          AND time BETWEEN $2 - INTERVAL '{tolerance_minutes} minutes'
                       AND $2 + INTERVAL '{tolerance_minutes} minutes'
        ORDER BY ABS(EXTRACT(EPOCH FROM time - $2))
        LIMIT 1
    """
    row = await conn.fetchrow(sql, asset_id, target_time)
    if row is None:
        return None
    return float(row["close"]), row["time"]
```

### IDX Holiday Population (2026)

```python
# Initial seed data for 2026 IDX holidays
# Source: OJK/IDX annual holiday calendar
IDX_HOLIDAYS_2026 = [
    ("2026-01-01", "New Year's Day"),
    ("2026-01-29", "Chinese New Year"),
    ("2026-02-17", "Isra Mi'raj"),
    ("2026-03-20", "Nyepi"),
    ("2026-03-29", "Eid al-Fitr"),
    ("2026-03-30", "Eid al-Fitr"),
    ("2026-03-31", "Eid al-Fitr"),
    ("2026-04-01", "Eid al-Fitr"),
    ("2026-04-02", "Eid al-Fitr"),
    ("2026-04-03", "Good Friday"),
    ("2026-05-01", "Labour Day"),
    ("2026-05-14", "Ascension of Christ"),
    ("2026-05-26", "Waisak"),
    ("2026-06-01", "Pancasila Day"),
    ("2026-06-05", "Eid al-Adha"),
    ("2026-06-26", "Islamic New Year"),
    ("2026-08-17", "Independence Day"),
    ("2026-09-05", "Prophet Muhammad's Birthday"),
    ("2026-12-25", "Christmas Day"),
]
```

Note: These dates should be verified against the official OJK/IDX 2026 calendar when available. Islamic holidays shift each year. The migration should include a seed function. Update annually.

### Scorecard Formatter

```python
def format_scorecard_section(
    results_by_window: dict[str, list[EvalDisplayItem]],
    weekly_trend: str | None,
) -> str:
    """Format yesterday's scorecard section for daily report."""
    if not any(results_by_window.values()):
        return ""  # D-18: skip if no prior decisions

    lines = ["<b>Yesterday's Scorecard</b>", ""]

    for window, items in results_by_window.items():
        if not items:
            continue
        correct = sum(1 for i in items if i.was_correct)
        lines.append(f"<b>{window} Results ({correct}/{len(items)})</b>")
        for item in items:
            emoji = "\u2705" if item.was_correct else "\u274c"
            sign = "+" if item.change_pct >= 0 else ""
            lines.append(
                f"{emoji} {html.escape(item.symbol)} -- "
                f"{item.verdict} -> {sign}{item.change_pct:.1%}"
            )
        lines.append("")

    if weekly_trend:
        lines.append(f"<i>{weekly_trend}</i>")

    return "\n".join(lines)
```

### Pipeline Integration

```python
# src/pipeline/main.py - updated stage_funcs
stage_funcs = {
    "evaluate": evaluate_stage,  # NEW: runs first
    "fetch": ingest_stage,
    "analyze": analyze_stage,
    "decide": decide_stage,
}

# Default stage order updated
# runner.py stages default: ["evaluate", "fetch", "analyze", "decide", "report"]
```

### Scorecard Bot Handler Pattern

```python
# src/bot/handlers/scorecard.py
async def scorecard_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show accuracy scorecard (TBOT-04)."""
    if not is_authorized(update):
        return
    # Parse args: /scorecard [period] [asset]
    period = "30d"
    asset_filter = None
    if context.args:
        for arg in context.args:
            if arg.lower() in ("7d", "30d", "90d", "all"):
                period = arg.lower()
            else:
                asset_filter = arg.upper()
    # Query accuracy_stats + evaluations from DB
    async with async_session_factory() as session:
        stats = await eval_repo.get_scorecard_data(session, period, asset_filter)
    # Format and send
    msg = format_scorecard_message(stats)
    await update.message.reply_text(msg, parse_mode="HTML")
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Single eval window | Multi-window (24h/3d/7d/30d) | This phase | More nuanced accuracy picture |
| Overall accuracy only | Per-engine tracking | This phase | Enables engine quality metadata for Phase 7 |
| No baseline comparison | Buy-and-hold baseline | This phase | Honest comparison of signal value |

## Open Questions

1. **Hourly candle retention vs multi-day crypto windows**
   - What we know: `price_history_hourly` has 7-day rolling retention (Phase 2 TimescaleDB policy)
   - What's unclear: Can we extend retention or do we fall back to daily candles for 7d/30d windows?
   - Recommendation: Fall back to `price_history` daily close for 7d and 30d crypto windows. Hourly precision only matters for 24h and 3d windows. Document this in code comments.

2. **IDX 2026 holiday accuracy**
   - What we know: Islamic holidays vary year-to-year based on lunar calendar; OJK publishes official calendar
   - What's unclear: Exact dates for 2026 Islamic holidays
   - Recommendation: Use best-estimate dates in seed migration, add a `--verify-holidays` CLI flag or manual SQL update path. Holidays only affect IDX stock eval timing, not crypto.

3. **`DailyDecision.evaluation_price` column purpose**
   - What we know: The existing `evaluation_price` / `evaluation_price_at` columns on `daily_decisions` were designed for a single evaluation price
   - What's unclear: Whether these should hold the 24h eval price or be deprecated in favor of the `evaluations` table
   - Recommendation: Populate these with the 24h evaluation (primary window) for backward compatibility. The `evaluations` table holds all four windows.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2+ with pytest-asyncio (auto mode) |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` |
| Quick run command | `pytest tests/test_data/test_evaluate.py -x` |
| Full suite command | `pytest` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| EVAL-01 | Direction classification (BUY correct if up, SELL correct if down) | unit | `pytest tests/test_data/test_evaluate.py::TestClassifyResult -x` | Wave 0 |
| EVAL-01 | HOLD band correctness (within band = correct, outside = wrong) | unit | `pytest tests/test_data/test_evaluate.py::TestHoldBands -x` | Wave 0 |
| EVAL-01 | Multi-window maturity (skip pending, eval ready) | unit | `pytest tests/test_data/test_evaluate.py::TestWindowMaturity -x` | Wave 0 |
| EVAL-01 | IDX trading calendar (skip weekends/holidays) | unit | `pytest tests/test_data/test_evaluate.py::TestIDXCalendar -x` | Wave 0 |
| EVAL-01 | Crypto hourly price lookup (closest candle) | unit | `pytest tests/test_data/test_evaluate.py::TestCryptoPriceLookup -x` | Wave 0 |
| EVAL-01 | No look-ahead bias (only writes eval_price, never decision_price) | unit | `pytest tests/test_data/test_evaluate.py::TestNoLookAhead -x` | Wave 0 |
| EVAL-05 | Accuracy stats computation (win rate, per-engine) | unit | `pytest tests/test_db/test_evaluation_repo.py::TestAccuracyStats -x` | Wave 0 |
| EVAL-05 | Best/worst engine identification | unit | `pytest tests/test_db/test_evaluation_repo.py::TestEngineRanking -x` | Wave 0 |
| TBOT-04 | /scorecard returns formatted message | unit | `pytest tests/test_bot/test_handlers.py::TestScorecardHandler -x` | Wave 0 |
| TBOT-04 | /scorecard period and asset filtering | unit | `pytest tests/test_bot/test_handlers.py::TestScorecardParsing -x` | Wave 0 |
| REPT-01 | Scorecard section in daily report (non-empty) | unit | `pytest tests/test_report/test_formatter.py::TestScorecardSection -x` | Wave 0 |
| REPT-01 | Scorecard skipped when no prior decisions (D-18) | unit | `pytest tests/test_report/test_formatter.py::TestScorecardEmpty -x` | Wave 0 |
| REPT-01 | Buy-and-hold baseline in scorecard | unit | `pytest tests/test_report/test_formatter.py::TestBuyAndHold -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/test_data/test_evaluate.py tests/test_db/test_evaluation_repo.py tests/test_report/test_formatter.py tests/test_bot/test_handlers.py -x`
- **Per wave merge:** `pytest`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_data/test_evaluate.py` -- covers EVAL-01 (evaluation logic, classification, calendar, crypto lookup)
- [ ] `tests/test_db/test_evaluation_repo.py` -- covers EVAL-05 (accuracy stats, engine ranking)
- [ ] Extend `tests/test_report/test_formatter.py` -- covers REPT-01 (scorecard formatting)
- [ ] Extend `tests/test_bot/test_handlers.py` -- covers TBOT-04 (scorecard command handler)
- [ ] `tests/test_data/conftest.py` -- needs new fixtures for decisions, evaluations, signals

## Sources

### Primary (HIGH confidence)
- Existing codebase: `src/db/models.py`, `src/db/decision_repo.py`, `src/db/signal_repo.py`, `src/db/price_repo.py` -- all examined for schema and patterns
- Existing codebase: `src/pipeline/runner.py`, `src/pipeline/main.py` -- stage registration and execution flow
- Existing codebase: `src/report/formatter.py`, `src/data/report.py` -- report formatting patterns
- Existing codebase: `src/bot/handlers/report.py`, `src/bot/main.py` -- bot handler registration pattern
- `plan/ARCHITECTURE.md` -- evaluations/accuracy_stats/lessons table schemas, daily execution flow with evaluate as stage 1

### Secondary (MEDIUM confidence)
- IDX holiday dates for 2026 -- based on typical Indonesian holiday calendar, Islamic dates approximate

### Tertiary (LOW confidence)
- None

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- no new dependencies, all patterns established in prior phases
- Architecture: HIGH -- follows existing StageFunc, repository, handler, and formatter patterns exactly
- Pitfalls: HIGH -- derived from direct codebase analysis (hourly retention, schema columns, calendar logic)
- HOLD band scaling values: MEDIUM -- reasonable values but may need tuning after real data

**Research date:** 2026-03-24
**Valid until:** 2026-04-24 (stable -- no external dependency changes expected)
