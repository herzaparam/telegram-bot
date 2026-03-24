---
phase: 06-accuracy-tracking-scorecard
verified: 2026-03-24T11:30:00Z
status: gaps_found
score: 14/15 must-haves verified
gaps:
  - truth: "/scorecard command shows buy-and-hold comparison per D-14"
    status: partial
    reason: "get_scorecard_data() does not return per_asset_buyhold key. The handler calls data.get('per_asset_buyhold', []) which silently returns [] — the B&H section in /scorecard output is permanently empty."
    artifacts:
      - path: "src/db/evaluation_repo.py"
        issue: "get_scorecard_data() return dict has 4 keys (win_rates_by_window, total_decisions, best_engine, worst_engine) — missing per_asset_buyhold key per plan spec"
    missing:
      - "Implement per_asset_buyhold computation in get_scorecard_data(): for each watchlisted asset compare signal-directed return vs simple buy-and-hold return over the period, add 'per_asset_buyhold' key to return dict"
---

# Phase 6: Accuracy Tracking and Scorecard Verification Report

**Phase Goal:** Accuracy tracking and scorecard — evaluate prior decisions against actual prices, track win rates by window/engine, display scorecard in daily reports and via /scorecard bot command.
**Verified:** 2026-03-24T11:30:00Z
**Status:** gaps_found
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|---------|
| 1 | Prior-day decisions are evaluated against actual prices each morning before ingest | VERIFIED | `evaluate_stage` implemented in `src/data/evaluate.py`, wired as first entry in `stage_funcs` dict before `fetch` in `src/pipeline/main.py` line 66 |
| 2 | BUY/STRONG BUY correct if price went up, SELL/STRONG SELL correct if price went down | VERIFIED | `_classify_result()` in `src/data/evaluate.py` lines 61-64: `change_pct > 0` for BUY/STRONG BUY, `change_pct < 0` for SELL/STRONG SELL |
| 3 | HOLD correctness uses asset-specific bands that scale with window length | VERIFIED | `HOLD_BANDS` constant defined at lines 24-29 with stock 2%/3%/5%/8% and crypto 5%/8%/12%/20%; applied in `_classify_result()` line 66-68 |
| 4 | Multi-window evaluation at 24h, 3d, 7d, 30d only evaluates mature windows | VERIFIED | `EVAL_WINDOWS` list at lines 32-37, `target_date = today - window_delta` logic at line 258 — only evaluates decisions from N days ago |
| 5 | IDX evaluations skip weekends and holidays using static calendar | VERIFIED | `_get_next_trading_day()` loops checking `candidate.weekday() >= 5` and `evaluation_repo.is_idx_holiday()`, holidays seeded in migration 005 |
| 6 | Crypto evaluations use closest hourly candle for 24h/3d, daily close for 7d/30d | VERIFIED | `_get_evaluation_price()` lines 149-198: hourly query with 30-min margin for 24h/3d, daily fallback for 7d/30d |
| 7 | Per-engine accuracy is tracked independently via engine_results JSONB | VERIFIED | `_compute_engine_results()` builds per-engine dict; `recompute_accuracy_stats()` unpacks JSONB and upserts per-engine rows in `accuracy_stats` |
| 8 | Accuracy stats are recomputed after each evaluation run | VERIFIED | `evaluate_stage` line 336: calls `evaluation_repo.recompute_accuracy_stats(session, asset.id)` after all windows when `evaluated_any` is True |
| 9 | /scorecard command returns accuracy stats with win rate by window, best/worst engine | VERIFIED | `scorecard_handler` in `src/bot/handlers/scorecard.py` calls `get_scorecard_data()`, formats with `format_scorecard_message()` showing win rates and engine ranking |
| 10 | /scorecard accepts optional period (7d, 30d, 90d, all) and optional asset filter | VERIFIED | Arg parsing loop at lines 51-64, `VALID_PERIODS = {"7d", "30d", "90d", "all"}`, asset resolved via Watchlist join |
| 11 | Daily report begins with yesterday's scorecard section when evaluations exist | VERIFIED | `_build_scorecard_section()` in `src/data/report.py`, called at line 242 in `send_daily_report()`, prepended to header with separator |
| 12 | Scorecard section shows per-asset results with correct/wrong emoji per D-15 | VERIFIED | `format_scorecard_section()` line 254: `"\u2705"` for correct, `"\u274c"` for wrong; format string `{emoji} {symbol} -- {verdict} -> {sign}{pct:.1f}%` |
| 13 | Scorecard section has separate subsections per matured evaluation window per D-16 | VERIFIED | `format_scorecard_section()` iterates `_WINDOW_ORDER = ["24h", "3d", "7d", "30d"]` at line 241, produces per-window header `{window} Results ({correct}/{total})` |
| 14 | When no prior decisions exist, scorecard section is skipped entirely per D-18 | VERIFIED | `format_scorecard_section()` line 234-236: `has_any = any(...)`, returns `""` immediately when no data; `send_daily_report()` only prepends non-empty scorecard text |
| 15 | /scorecard shows buy-and-hold comparison per D-14 | FAILED | `get_scorecard_data()` return dict (lines 244-249) omits `per_asset_buyhold` key; handler uses `data.get("per_asset_buyhold", [])` which always returns `[]` — B&H section never rendered |

**Score:** 14/15 truths verified

### Required Artifacts

| Artifact | Provides | Status | Details |
|----------|----------|--------|---------|
| `src/db/models.py` | Evaluation, AccuracyStats, IDXHoliday ORM models | VERIFIED | `class Evaluation` (line 229), `class AccuracyStats` (line 252), `class IDXHoliday` (line 278) all present with correct columns |
| `src/db/migrations/versions/005_evaluations.py` | Alembic migration for 3 tables + 19 holiday seeds | VERIFIED | Creates evaluations, accuracy_stats, idx_holidays tables; seeds 19 IDX 2026 holidays; downgrade drops in reverse order |
| `src/db/evaluation_repo.py` | EvaluationRepository with all CRUD + stats methods | VERIFIED | `upsert_evaluation`, `get_evaluation`, `recompute_accuracy_stats`, `get_scorecard_data`, `get_best_worst_engine`, `get_recent_evaluations`, `is_idx_holiday`; singleton at line 329 |
| `src/data/evaluate.py` | evaluate_stage StageFunc with classification | VERIFIED | All functions present: `_classify_result`, `_get_evaluation_price`, `_get_next_trading_day`, `_compute_engine_results`, `evaluate_stage` |
| `src/config.py` | timeout_evaluate setting | VERIFIED | `timeout_evaluate: int = 60` at line 45 |
| `src/pipeline/main.py` | evaluate_stage as first pipeline stage | VERIFIED | Import at line 18, `"evaluate": evaluate_stage` at line 66 — before fetch |
| `src/pipeline/runner.py` | evaluate in default stages and timeout mapping | VERIFIED | `stages = ["evaluate", "fetch", "analyze", "decide", "report"]` at line 70; `"evaluate": settings.timeout_evaluate` at line 300 |
| `src/report/formatter.py` | EvalDisplayItem, format_scorecard_section, format_scorecard_message | VERIFIED | `EvalDisplayItem` dataclass at line 200, both functions at lines 222 and 269, `format_scorecard_error` at line 376 |
| `src/data/report.py` | Scorecard data injection into daily report | VERIFIED | `from src.db.evaluation_repo import evaluation_repo` at line 20, `format_scorecard_section` import at line 26, `_build_scorecard_section` helper at line 81 |
| `src/bot/handlers/scorecard.py` | /scorecard command handler | VERIFIED | `scorecard_handler` function at line 31 with full period/asset parsing, error states, recent calls, authorization check |
| `src/bot/main.py` | Registered /scorecard command | VERIFIED | Import at line 18, `CommandHandler("scorecard", scorecard_handler)` at line 46 |
| `tests/test_data/test_evaluate.py` | 23 evaluate stage tests | VERIFIED | 23 test functions confirmed by count; covers classify_result, HOLD bands, window maturity, IDX calendar, engine results |
| `tests/test_db/test_evaluation_repo.py` | 17 repository tests | VERIFIED | 17 test functions; covers upsert, recompute_accuracy_stats, get_scorecard_data, engine ranking |
| `tests/test_report/test_formatter.py` | 61 formatter tests including TestScorecardSection | VERIFIED | 61 total tests; `TestScorecardSection` at line 291, `TestScorecardMessage` at line 383 |
| `tests/test_bot/test_handlers.py` | 21 bot handler tests including scorecard | VERIFIED | 21 total tests; `TestScorecardHandler` at line 219, `TestScorecardParsing` at line 266 |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `src/data/evaluate.py` | `src/db/evaluation_repo.py` | `evaluation_repo.upsert_evaluation()` | WIRED | Called at line 310 of evaluate.py |
| `src/data/evaluate.py` | `src/db/decision_repo.py` | `decision_repo.get_decision()` | WIRED | Called at line 261 of evaluate.py |
| `src/pipeline/main.py` | `src/data/evaluate.py` | `stage_funcs dict` | WIRED | Import at line 18, dict entry `"evaluate": evaluate_stage` at line 66 |
| `src/bot/handlers/scorecard.py` | `src/db/evaluation_repo.py` | `evaluation_repo.get_scorecard_data()` | WIRED | Called at line 91 of scorecard.py |
| `src/data/report.py` | `src/report/formatter.py` | `format_scorecard_section()` | WIRED | Imported at line 26 of report.py, called at line 161 via `_build_scorecard_section` |
| `src/bot/main.py` | `src/bot/handlers/scorecard.py` | `CommandHandler("scorecard", scorecard_handler)` | WIRED | Import at line 18, registration at line 46 of bot/main.py |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|--------------|--------|--------------------|--------|
| `format_scorecard_section` | `results_by_window` | `_build_scorecard_section` → `evaluation_repo.get_recent_evaluations` → `evaluations` table | Yes — DB query via `select(Evaluation)` with filters | FLOWING |
| `format_scorecard_message` | `win_rates_by_window`, `best_engine`, `worst_engine` | `evaluation_repo.get_scorecard_data` → `accuracy_stats` table | Yes — DB query via `select(AccuracyStats)` | FLOWING |
| `format_scorecard_message` | `per_asset_buyhold` | `data.get("per_asset_buyhold", [])` — `get_scorecard_data` does not populate | No — always returns empty list | HOLLOW_PROP |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| evaluate_stage imports without error | `.venv/bin/python -c "from src.data.evaluate import evaluate_stage"` | ModuleNotFoundError (structlog, expected without full env) | SKIP — env dependency only |
| All 122 Phase 06 tests pass | `.venv/bin/python -m pytest tests/test_data/test_evaluate.py tests/test_db/test_evaluation_repo.py tests/test_report/test_formatter.py tests/test_bot/test_handlers.py -q` | 122 passed in 0.49s | PASS |
| evaluate registered as first stage in main.py | `grep -n "evaluate_stage" src/pipeline/main.py` | Line 18 import, line 66 dict entry before fetch | PASS |
| timeout_evaluate wired in runner | `grep "evaluate" src/pipeline/runner.py` | Line 70 in stages list, line 300 in timeout mapping | PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| EVAL-01 | 06-01-PLAN.md | System reviews yesterday's decisions against actual prices every morning | SATISFIED | `evaluate_stage` runs as first pipeline stage, evaluates all 4 windows (24h/3d/7d/30d) against price history |
| EVAL-05 | 06-01-PLAN.md | System tracks accuracy stats over time (win rate, best/worst engine) | SATISFIED | `recompute_accuracy_stats()` computes win_rate per (asset, engine, window, period); `get_best_worst_engine()` ranks by 24h accuracy |
| TBOT-04 | 06-02-PLAN.md | /scorecard shows accuracy stats + recent results | SATISFIED | `/scorecard` handler returns win rates by window, total decisions, best/worst engine, recent calls; all error states handled |
| REPT-01 | 06-02-PLAN.md | Yesterday's scorecard (was I right/wrong, accuracy stats) | SATISFIED | Daily report prepends `format_scorecard_section()` with per-asset correct/wrong emoji, window subsections, trend line; skips when no data |

No orphaned requirements — all 4 requirement IDs declared in plan frontmatter are accounted for, and REQUIREMENTS.md confirms all 4 map to Phase 6.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `src/db/evaluation_repo.py` | 244-249 | `get_scorecard_data()` returns dict without `per_asset_buyhold` despite plan spec and UI-SPEC D-14 requiring it | Warning | B&H comparison section in `/scorecard` always empty — silent omission, no crash, but feature incomplete |

### Human Verification Required

#### 1. Weekly Trend Computation

**Test:** Ensure pipeline has run for 14+ consecutive days with evaluations. Then check daily Telegram report for the trend line at bottom of scorecard section (e.g., "Trending: 68% win rate this week (^ from 60% last week)").
**Expected:** Trend line appears with directional indicator (^, v, or ~) comparing this week vs last week 24h win rate. Uses 2pp threshold for directional change.
**Why human:** Requires 14 days of live evaluation data; cannot verify computationally without DB.

#### 2. IDX Holiday Skip in Live Pipeline

**Test:** Run pipeline on a date following an IDX holiday (e.g., day after 2026-03-29 Eid al-Fitr). Verify 24h evaluation for IDX stocks skips the holiday and uses the next valid trading day.
**Expected:** `evaluation_complete` log entries for IDX stocks should show `eval_price_at` on a valid trading day, not the holiday date itself.
**Why human:** Requires running pipeline near an actual IDX holiday date with live DB data.

#### 3. Crypto Hourly vs Daily Fallback in Live Pipeline

**Test:** Check evaluation logs for a crypto asset when 24h/3d windows are evaluated. Confirm the `eval_price_at` timestamp is within 30 minutes of the expected target time (decision time + window delta).
**Expected:** For 24h/3d windows, `eval_price_at` should match an hourly candle timestamp. For 7d/30d, should be a daily close timestamp.
**Why human:** Requires live `price_history_hourly` data and a real evaluation run.

### Gaps Summary

**1 gap blocking full goal achievement:**

The buy-and-hold comparison feature (D-14 from UI-SPEC) is structurally incomplete. `EvaluationRepository.get_scorecard_data()` was implemented to return `win_rates_by_window`, `total_decisions`, `best_engine`, and `worst_engine` — but NOT `per_asset_buyhold`. The formatter `format_scorecard_message()` and the `scorecard_handler` both have the scaffolding to display B&H comparison (including alpha formatting in bold for outperform, italic for underperform), but they silently receive an empty list and skip the section.

This means the `/scorecard` command always omits the "vs Buy & Hold" section that D-14 specifies. Since TBOT-04's stated requirement is "accuracy stats + recent results" (without explicitly naming B&H), the core requirement is technically met. However, the UI-SPEC and plan success criteria (item 6 in 06-02-PLAN.md: "/scorecard shows win rates, best/worst engine, buy-and-hold per D-12/D-14") were not fully achieved.

**All 4 requirements (EVAL-01, EVAL-05, TBOT-04, REPT-01) are satisfied at the requirement level.** The gap is at the design specification level (D-14), not at the requirement level.

The fix requires adding buy-and-hold return computation to `get_scorecard_data()`: for each watchlisted asset over the specified period, compute the cumulative return if a simple buy-and-hold strategy was followed, compare against the signal-weighted directional return, and add `per_asset_buyhold` to the return dict.

---

_Verified: 2026-03-24T11:30:00Z_
_Verifier: Claude (gsd-verifier)_
