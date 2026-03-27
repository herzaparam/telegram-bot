# Phase 12: Portfolio Risk + Advanced Commands - Research

**Researched:** 2026-03-27
**Domain:** Portfolio risk analytics, historical backtesting, enhanced fundamentals
**Confidence:** HIGH

## Summary

Phase 12 adds portfolio-level risk monitoring (correlation matrix, VaR, concentration, stress testing), a historical backtest command, and enhanced fundamentals (5-year trends, earnings quality, dividends). All computation uses existing infrastructure: numpy/pandas for math, PriceHistory + FinancialData tables for source data, and the established Telegram bot handler pattern for delivery.

The critical design constraint is the two-process boundary: risk computations that need the full pipeline (backtest) must run in the pipeline process and store results in DB, while the bot process reads pre-computed results. For on-demand computations (VaR, correlation matrix), the bot can compute directly from price data since it already queries PriceHistory via SQLAlchemy.

**Primary recommendation:** Create a new `src/risk/` module for portfolio risk computations (VaR, correlation, concentration, stress tests) that can be imported by both the bot process (on-demand queries) and pipeline process (daily risk snapshot). Backtest must run as a pipeline-side computation triggered via bot message queue or inline with progress feedback.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Correlation matrix displayed as compact ASCII/emoji heatmap grid showing high/medium/low correlation between each asset pair. Fits ~8-10 assets within Telegram message limits
- **D-02:** VaR computed using historical simulation method -- use actual past returns from price_history to estimate worst-case loss at 95% and 99% confidence. No distribution assumptions, works well with crypto fat tails
- **D-03:** Concentration risk shows all three dimensions: sector percentage, largest single-asset position %, and IDR vs USD currency exposure breakdown
- **D-04:** Daily and weekly VaR numbers plus maximum drawdown tracking included in output
- **D-05:** Risk-adjusted return metrics: Sharpe ratio and Sortino ratio computed from historical returns
- **D-06:** Portfolio risk snapshot section in daily report shows concentration %, correlation alerts (pairs >0.8), and VaR summary. Compact format matching existing report card style
- **D-07:** Stress test results are NOT included in daily report -- on-demand only via command
- **D-08:** Full pipeline replay -- re-run all 15 engines + LLM verdict on historical data for each day in the backtest period. Most accurate representation of actual signal quality
- **D-09:** Fixed time period options: 7d, 30d, 90d. User invokes as `/backtest BTC 30d`. Simple preset periods, no custom date ranges
- **D-10:** Output as summary stats only: win rate, total return, buy-and-hold comparison return, max drawdown, Sharpe ratio. Compact, fits one Telegram message
- **D-11:** Preset historical scenarios only -- hardcoded set: 2020 COVID crash, 2022 crypto winter, 2013 taper tantrum, 2008 GFC. Apply actual historical drawdowns to current portfolio positions
- **D-12:** On-demand delivery only -- user runs a command to see stress test projected drawdowns. Not in daily report
- **D-13:** No custom factor shocks -- preset scenarios are sufficient
- **D-14:** Add 5-year ratio trend history with text sparklines or trend arrows per year for profitability, leverage, efficiency, and growth ratios
- **D-15:** Add earnings quality analysis section: cash flow vs earnings divergence detection, one-off/extraordinary item identification
- **D-16:** Add dividend analysis section within /fundamentals: payout ratio, dividend yield, growth rate, FCF coverage. No separate /dividends command
- **D-17:** IDX stocks only for enhanced fundamentals. Crypto assets get existing signal analysis

### Claude's Discretion
- Correlation heatmap emoji/symbol choices and formatting within Telegram limits
- Historical simulation VaR lookback window (e.g., 252 trading days)
- VaR confidence level presentation (95% vs 99% or both)
- Sector classification mapping for concentration analysis
- Currency exposure calculation method (IDR assets vs USD-denominated crypto)
- Backtest full pipeline replay implementation (batch processing, LLM cost management, caching strategy)
- Backtest progress feedback mechanism (long-running operation)
- Stress test scenario data (exact drawdown percentages per scenario per asset type)
- How stress test applies IDX-specific vs crypto-specific shocks
- 5-year trend data source (parsed financials from Phase 9 vs yfinance historical)
- Earnings quality detection algorithm specifics
- Sparkline/trend arrow rendering for 5-year history
- New DB tables schema (portfolio_snapshots, backtest_results, stress_scenarios, etc.)
- Alembic migration details
- Error handling and graceful degradation
- Telegram message formatting and splitting for large outputs
- How /portfolio sub-sections are organized (single message vs multiple)

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| RISK-01 | Correlation matrix across all watchlist assets with spike alerts | Existing `_compute_correlation_data()` computes pairwise correlations. Extend to full NxN matrix. Emoji heatmap formatting per D-01 |
| RISK-02 | Concentration risk analysis (sector, single-asset, currency exposure) | `IDX_SECTOR_MAP` (53 tickers, 12 sectors) for sector mapping. Asset.asset_type distinguishes IDR/USD. No position sizes exist -- use equal-weight assumption or price-weighted |
| RISK-03 | Portfolio VaR (daily and weekly), maximum drawdown tracking | Historical simulation from PriceHistory close prices. numpy percentile for VaR. Rolling max drawdown from cumulative returns |
| RISK-04 | Risk-adjusted return metrics (Sharpe ratio, Sortino ratio) | Standard formulas on daily log returns from PriceHistory. Risk-free rate from MacroData (fed_funds_rate) |
| RISK-05 | Stress testing with historical scenarios and factor shocks | Hardcoded scenario drawdowns applied to current positions. Per D-11/D-13 preset only |
| FUND-01 | Ratio dashboard per stock (5-year trends) | FinancialData table has period-by-period metrics. StockFundamental has yfinance current data. 5-year trend requires historical FinancialData or yfinance historical |
| FUND-02 | Earnings quality analysis | Compare operating_cash_flow vs net_profit from FinancialData. Flag divergence |
| FUND-03 | Dividend analysis | StockFundamental.dividend_yield exists. Need payout ratio (dividends/earnings), FCF coverage (FCF/dividends). FinancialData has free_cash_flow |
| TBOT-08 | `/backtest BTC 30d` runs historical signal replay | Full pipeline replay via analyze_stage + decide equivalent. Needs progress feedback and cost management for LLM calls |
| TBOT-12 | `/portfolio` portfolio risk overview | New bot handler reading pre-computed risk data from DB + on-demand computation |
| REPT-06 | Daily report risk snapshot (concentration, correlation alerts) | Append to daily report in send_daily_report() like news/discovery sections |
</phase_requirements>

## Project Constraints (from CLAUDE.md)

- Two-process model: bot process MUST NOT import from `src/pipeline` or `src/llm`
- HTML parse_mode for all Telegram messages
- Per-asset processing with memory release (`del df; gc.collect()`) to stay within 1GB RAM
- Sequential engine execution per asset
- SQLAlchemy ORM for structured data, raw asyncpg for hot-path bulk operations
- Alembic for all schema changes with naming conventions from Base metadata
- structlog for logging
- mypy strict mode, ruff linting
- Frozen dataclasses for immutable results
- pytest with asyncio_mode="auto"

## Standard Stack

### Core (Already in Project)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| numpy | (existing) | VaR percentile, correlation matrix, returns computation | Already used by engines (network, emerging, valuation) |
| pandas | 3.0.1+ | DataFrame operations for price history, returns series | Already core dependency |
| SQLAlchemy | 2.0.48+ | ORM for new risk tables, queries | Already core dependency |
| python-telegram-bot | (existing) | Bot handler registration | Already used for all commands |

### No New Dependencies Required
All risk computations (VaR, correlation, Sharpe, Sortino, drawdown, stress test) use standard numpy/pandas operations already available. No additional packages needed.

## Architecture Patterns

### Recommended New Module Structure
```
src/
  risk/                        # NEW: Portfolio risk computation module
    __init__.py
    correlation.py             # NxN correlation matrix, heatmap formatting
    var.py                     # Historical simulation VaR, max drawdown
    concentration.py           # Sector, single-asset, currency exposure
    stress.py                  # Preset scenario stress testing
    metrics.py                 # Sharpe, Sortino, risk-adjusted returns
  data/
    backtest.py                # NEW: Full pipeline replay for backtesting
  bot/handlers/
    portfolio.py               # NEW: /portfolio command handler
    backtest.py                # NEW: /backtest command handler
  report/
    formatter.py               # EXTEND: add format_portfolio_risk_snapshot(), format_correlation_heatmap(), etc.
  db/
    models.py                  # EXTEND: PortfolioRiskSnapshot, BacktestResult
    migrations/versions/
      014_portfolio_risk.py    # NEW: risk snapshot + backtest tables
```

### Pattern 1: Risk Module as Shared Library
**What:** `src/risk/` contains pure computation functions that accept DataFrames/arrays and return result dataclasses. No DB imports. Both bot and pipeline can import it.
**When to use:** For all risk computations (VaR, correlation, Sharpe, etc.)
**Why:** Respects two-process boundary. Bot process computes on-demand from queried price data. Pipeline process computes daily snapshot and stores results.

```python
# src/risk/var.py
from dataclasses import dataclass
import numpy as np
import pandas as pd

@dataclass(frozen=True)
class VaRResult:
    daily_var_95: float
    daily_var_99: float
    weekly_var_95: float
    weekly_var_99: float
    max_drawdown: float
    max_drawdown_period: str  # "2025-01-15 to 2025-02-03"

def compute_historical_var(
    returns: pd.Series,
    confidence_levels: tuple[float, ...] = (0.95, 0.99),
) -> VaRResult:
    """Historical simulation VaR from daily returns.

    No distribution assumptions -- uses actual return percentiles.
    Weekly VaR = daily VaR * sqrt(5) approximation.
    """
    daily_95 = float(np.percentile(returns, (1 - 0.95) * 100))
    daily_99 = float(np.percentile(returns, (1 - 0.99) * 100))
    # ...
```

### Pattern 2: Bot Handler Reads Pre-Computed + Computes On-Demand
**What:** `/portfolio` handler reads the daily risk snapshot from DB (pre-computed by pipeline) but can also compute fresh VaR/correlation on-demand from PriceHistory.
**When to use:** When data freshness matters but pipeline may not have run yet.
**Why:** Risk snapshot in daily report needs to be pre-computed (pipeline context). But `/portfolio` command should work even if pipeline hasn't run today.

```python
# src/bot/handlers/portfolio.py -- reads from DB, computes on-demand
from src.risk.correlation import compute_correlation_matrix, format_correlation_heatmap
from src.risk.var import compute_historical_var
from src.risk.concentration import compute_concentration

# Load price data for all watchlist assets from PriceHistory via SQLAlchemy
# Compute risk metrics using src/risk/ functions
# Format and send via Telegram
```

**IMPORTANT:** The `src/risk/` module does NOT import from `src/pipeline` or `src/llm`. It only depends on numpy/pandas. This means both processes can safely import it.

### Pattern 3: Backtest as Pipeline-Side Long-Running Task
**What:** `/backtest` triggers a pipeline-side computation. The bot sends a "processing" message, starts the backtest, and sends results when done.
**When to use:** For backtest which requires LLM calls (full pipeline replay per D-08).
**Why:** Bot process cannot import `src/llm`. Backtest requires LLM for verdict generation.

**Implementation options (Claude's discretion):**
1. **Inline async in bot with LLM exception:** Allow bot to import `src/llm` ONLY for backtest, or create a thin wrapper in `src/risk/` that calls litellm directly.
2. **Task queue via DB:** Bot writes a `backtest_requests` row, pipeline picks it up next run. Too slow.
3. **Direct subprocess:** Bot spawns `python -m src.data.backtest --asset BTC --period 30d` as subprocess. Results stored in DB, bot polls.
4. **Recommended: Bot imports src/risk/ which calls litellm directly.** The two-process boundary prevents importing `src/pipeline`, but `src/llm/client.py` is a standalone module. The bot already uses `async_session_factory` for DB access. Having the bot call `llm_completion()` for backtest is pragmatic -- it's a user-initiated action, not a pipeline stage.

### Pattern 4: Daily Report Risk Snapshot via Pipeline Post-Hook
**What:** After decide stage completes, compute portfolio risk snapshot and store in DB. send_daily_report() reads it and appends to report.
**When to use:** For REPT-06 daily report section.
**Why:** Follows existing pattern: discovery scan runs post-pipeline, results fed into send_daily_report().

```python
# In src/pipeline/main.py async_main():
# After discovery scan, before send_daily_report:
risk_snapshot = {}
try:
    async with async_session_factory() as session:
        risk_snapshot = await compute_daily_risk_snapshot(session, run_date)
except Exception:
    logger.exception("risk_snapshot_error")

# Pass to send_daily_report
await send_daily_report(session, run_date, ..., risk_snapshot=risk_snapshot)
```

### Anti-Patterns to Avoid
- **Do NOT put risk computation in engines:** Engines are per-asset. Portfolio risk is cross-asset. Keep in separate `src/risk/` module.
- **Do NOT store full correlation matrix in DB:** Store only the risk snapshot summary (high-correlation pairs, VaR numbers). Compute full matrix on-demand.
- **Do NOT make backtest a pipeline stage:** It's user-initiated, not daily. Run as ad-hoc command.
- **Do NOT import src/pipeline from bot:** Use src/risk/ as the shared layer. For backtest LLM calls, import src/llm/client.py directly (it's a standalone function, not a pipeline module).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Correlation matrix | Custom pairwise loop | `numpy.corrcoef()` or `pandas.DataFrame.corr()` | Handles NaN, optimized C implementation |
| VaR percentile | Sort + index | `numpy.percentile()` | Numerically stable, handles edge cases |
| Drawdown computation | Manual peak tracking | Vectorized cummax approach with pandas | 10x faster, no off-by-one errors |
| Sparkline rendering | Custom char mapping | Simple list comprehension with block chars | Standard approach: `_SPARK_CHARS = "  ....::::****####"` or similar |
| Log returns | Manual math | `numpy.log(prices / prices.shift(1))` | Handles division edge cases |

**Key insight:** All portfolio risk computations are standard financial math with well-known numpy/pandas implementations. No libraries beyond what's already installed are needed.

## Common Pitfalls

### Pitfall 1: Correlation Matrix Size Exceeds Telegram Limit
**What goes wrong:** With 8+ assets, a full NxN matrix in text format exceeds 4096 chars.
**Why it happens:** Each cell needs ~5 chars, 10x10 = 500 chars for grid alone, plus headers.
**How to avoid:** Use compact emoji format (one emoji per cell): green=low, yellow=medium, red=high correlation. Per D-01: "compact ASCII/emoji heatmap". Maximum ~10 assets fits in one message.
**Warning signs:** Message send fails with "message too long" error.

### Pitfall 2: Historical VaR With Insufficient Data
**What goes wrong:** VaR on 7 days of data is statistically meaningless.
**Why it happens:** New assets on watchlist may have limited price history.
**How to avoid:** Require minimum 60 trading days for VaR computation. Show "Insufficient data" for assets with less. Use 252-day lookback window (1 trading year) as default.
**Warning signs:** VaR values that change dramatically day-to-day.

### Pitfall 3: Backtest LLM Cost Explosion
**What goes wrong:** 90-day backtest x 8 assets x 1 LLM call/day = 720 LLM calls. At $0.01/call = $7.20 per backtest.
**Why it happens:** Full pipeline replay per D-08 means LLM verdict for each day.
**How to avoid:** Cache backtest results in DB (BacktestResult table). Only re-run if not cached. Rate-limit to max 1 backtest per 5 minutes. Consider caching engine signals per historical date and only calling LLM for the final verdict.
**Warning signs:** Unexpectedly high API bills, slow response times.

### Pitfall 4: Backtest Look-Ahead Bias
**What goes wrong:** Using future data when replaying historical signals.
**Why it happens:** Loading price_history with no date filter gives the engine access to prices after the backtest date.
**How to avoid:** When loading price data for backtest date D, filter `PriceHistory.time <= D`. Each replay day must see only data available on that day.
**Warning signs:** Backtest results that are unrealistically good.

### Pitfall 5: Concentration Risk Without Position Sizes
**What goes wrong:** The system has no actual portfolio positions or dollar amounts.
**Why it happens:** This is a signal system, not a portfolio management system. No buying/selling.
**How to avoid:** Use equal-weight assumption (each watchlist asset = 1/N of portfolio). Document this assumption clearly. Alternatively, use market prices to compute relative weights.
**Warning signs:** Users confused about why concentration shows equal percentages.

### Pitfall 6: Two-Process Boundary Violation for Backtest
**What goes wrong:** Bot handler imports `src/pipeline` or `analyze_stage` to replay signals.
**Why it happens:** Backtest needs to run engines and LLM, which live in pipeline context.
**How to avoid:** Import `src/risk/` and `src/llm/client.py` directly from bot. Create `src/risk/backtest.py` (or `src/data/backtest.py`) that uses engine classes directly (they're not in src/pipeline/). The bot CAN import `src/engines/*` and `src/llm/*` -- it just cannot import `src/pipeline/*`.
**Warning signs:** ImportError at bot startup.

**CORRECTION on two-process boundary:** Re-reading ARCHITECTURE.md: "Bot service MUST NOT import from: src/pipeline or src/llm". This means the bot CANNOT call LLM directly. Backtest must either:
1. Store a request in DB, have pipeline process it asynchronously
2. Run as a subprocess (`python -m src.data.backtest`)
3. Use an HTTP endpoint on the pipeline side

**Recommended:** Option 2 -- subprocess. Bot spawns `python -m src.data.backtest --asset BTC --period 30d`, stores result in `backtest_results` table, bot reads result. Send "Processing..." message first, poll DB for result.

### Pitfall 7: Stress Test Scenario Data Accuracy
**What goes wrong:** Using incorrect drawdown numbers for historical scenarios.
**Why it happens:** Peak-to-trough drawdowns differ depending on measurement period and asset class.
**How to avoid:** Use well-documented drawdowns:
- COVID 2020: S&P -34%, BTC -50%, IDX (IHSG) -37%
- Crypto Winter 2022: BTC -77%, ETH -82%, stocks -20%
- Taper Tantrum 2013: EM stocks -15%, BTC not relevant (early)
- GFC 2008: S&P -57%, IDX -60%, crypto N/A
**Warning signs:** Stress test results that seem unreasonable.

## Code Examples

### Correlation Matrix Computation
```python
# src/risk/correlation.py
import numpy as np
import pandas as pd
from dataclasses import dataclass

@dataclass(frozen=True)
class CorrelationResult:
    matrix: dict[str, dict[str, float]]  # symbol -> symbol -> correlation
    high_pairs: list[tuple[str, str, float]]  # pairs with |corr| > 0.8
    avg_correlation: float

def compute_correlation_matrix(
    price_data: dict[str, pd.Series],  # symbol -> close price series
    window: int = 30,
) -> CorrelationResult:
    """Compute NxN correlation matrix from close price returns."""
    # Build DataFrame of returns
    returns = pd.DataFrame({
        sym: prices.pct_change().dropna()
        for sym, prices in price_data.items()
    })

    # Use last `window` days
    returns = returns.tail(window)

    # Compute correlation matrix
    corr = returns.corr()

    # Extract high-correlation pairs
    high_pairs = []
    symbols = list(corr.columns)
    for i, s1 in enumerate(symbols):
        for j, s2 in enumerate(symbols):
            if i < j and abs(corr.loc[s1, s2]) > 0.8:
                high_pairs.append((s1, s2, float(corr.loc[s1, s2])))

    matrix = {s1: {s2: float(corr.loc[s1, s2]) for s2 in symbols} for s1 in symbols}
    avg = float(corr.values[np.triu_indices_from(corr.values, k=1)].mean())

    return CorrelationResult(matrix=matrix, high_pairs=high_pairs, avg_correlation=avg)
```

### Emoji Heatmap Formatting
```python
# src/risk/correlation.py
CORR_EMOJI = {
    "high_pos": "\U0001f534",   # red circle (>0.7)
    "med_pos": "\U0001f7e0",    # orange circle (0.4-0.7)
    "low": "\U0001f7e2",         # green circle (-0.3 to 0.4)
    "med_neg": "\U0001f535",    # blue circle (-0.7 to -0.3)
    "high_neg": "\U0001f7e3",   # purple circle (<-0.7)
}

def format_correlation_heatmap(result: CorrelationResult) -> str:
    """Format NxN correlation as compact emoji grid for Telegram (HTML)."""
    symbols = sorted(result.matrix.keys())
    # Header row: short symbols (3-4 chars)
    header = "     " + " ".join(f"{s[:4]:>4}" for s in symbols)

    rows = [f"<code>{header}</code>"]
    for s1 in symbols:
        row_emojis = []
        for s2 in symbols:
            if s1 == s2:
                row_emojis.append("\u2b1c")  # white square (diagonal)
            else:
                c = result.matrix[s1][s2]
                if c > 0.7: emoji = CORR_EMOJI["high_pos"]
                elif c > 0.4: emoji = CORR_EMOJI["med_pos"]
                elif c > -0.3: emoji = CORR_EMOJI["low"]
                elif c > -0.7: emoji = CORR_EMOJI["med_neg"]
                else: emoji = CORR_EMOJI["high_neg"]
                row_emojis.append(emoji)
        rows.append(f"<code>{s1[:4]:>4}</code> {''.join(row_emojis)}")

    return "\n".join(rows)
```

### Historical Simulation VaR
```python
# src/risk/var.py
import numpy as np
import pandas as pd
from dataclasses import dataclass

@dataclass(frozen=True)
class VaRResult:
    daily_var_95: float    # Negative number: worst daily loss at 95%
    daily_var_99: float
    weekly_var_95: float
    weekly_var_99: float
    max_drawdown: float    # Negative number: worst peak-to-trough
    max_drawdown_start: str
    max_drawdown_end: str

def compute_historical_var(
    returns: pd.Series,
    lookback: int = 252,
) -> VaRResult:
    """Historical simulation VaR. No distribution assumptions."""
    r = returns.tail(lookback).dropna()

    daily_95 = float(np.percentile(r, 5))   # 5th percentile = 95% VaR
    daily_99 = float(np.percentile(r, 1))   # 1st percentile = 99% VaR

    # Weekly VaR: use actual 5-day rolling returns if enough data
    weekly_returns = r.rolling(5).sum().dropna()
    weekly_95 = float(np.percentile(weekly_returns, 5)) if len(weekly_returns) > 20 else daily_95 * np.sqrt(5)
    weekly_99 = float(np.percentile(weekly_returns, 1)) if len(weekly_returns) > 20 else daily_99 * np.sqrt(5)

    # Max drawdown
    cumulative = (1 + r).cumprod()
    running_max = cumulative.cummax()
    drawdown = (cumulative - running_max) / running_max
    max_dd = float(drawdown.min())
    dd_end_idx = drawdown.idxmin()
    dd_start_idx = cumulative.loc[:dd_end_idx].idxmax()

    return VaRResult(
        daily_var_95=round(daily_95, 6),
        daily_var_99=round(daily_99, 6),
        weekly_var_95=round(weekly_95, 6),
        weekly_var_99=round(weekly_99, 6),
        max_drawdown=round(max_dd, 6),
        max_drawdown_start=str(dd_start_idx),
        max_drawdown_end=str(dd_end_idx),
    )
```

### Backtest via Subprocess
```python
# src/bot/handlers/backtest.py
import asyncio
import sys
from telegram import Update
from telegram.ext import ContextTypes

async def backtest_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /backtest BTC 30d -- spawn subprocess, poll for results."""
    # Parse args
    symbol = context.args[0].upper()
    period = context.args[1] if len(context.args) > 1 else "30d"

    # Send processing message
    msg = await update.message.reply_text(
        f"Running backtest for {symbol} ({period})... This may take a few minutes.",
        parse_mode="HTML",
    )

    # Spawn pipeline subprocess
    proc = await asyncio.create_subprocess_exec(
        sys.executable, "-m", "src.data.backtest",
        "--asset", symbol, "--period", period,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()

    # Read result from DB (backtest writes to backtest_results table)
    # Format and edit the message with results
```

### Sparkline for 5-Year Trends
```python
# src/report/formatter.py additions
_SPARK_CHARS = " .:-=+*#%@"  # 10 levels

def _sparkline(values: list[float], width: int = 5) -> str:
    """Render a text sparkline for a list of values."""
    if not values or all(v == values[0] for v in values):
        return "-" * width
    mn, mx = min(values), max(values)
    rng = mx - mn if mx != mn else 1.0
    return "".join(
        _SPARK_CHARS[min(int((v - mn) / rng * (len(_SPARK_CHARS) - 1)), len(_SPARK_CHARS) - 1)]
        for v in values[-width:]
    )
```

## DB Schema Design

### New Tables

```python
# PortfolioRiskSnapshot -- daily pre-computed risk summary for report
class PortfolioRiskSnapshot(Base):
    __tablename__ = "portfolio_risk_snapshots"
    __table_args__ = (UniqueConstraint("snapshot_date"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    snapshot_date: Mapped[date] = mapped_column(Date, nullable=False)
    concentration: Mapped[dict] = mapped_column(JSONB, nullable=False)
    # {"sector": {"banking": 40, "telco": 20}, "max_single": 15.5, "idr_pct": 60, "usd_pct": 40}
    correlation_alerts: Mapped[list] = mapped_column(JSONB, nullable=False)
    # [{"pair": ["BBCA", "BBRI"], "correlation": 0.92}]
    var_summary: Mapped[dict] = mapped_column(JSONB, nullable=False)
    # {"daily_95": -0.023, "daily_99": -0.045, "weekly_95": -0.051, "max_drawdown": -0.12}
    sharpe_ratio: Mapped[float | None] = mapped_column(Float, nullable=True)
    sortino_ratio: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

# BacktestResult -- cached backtest output
class BacktestResult(Base):
    __tablename__ = "backtest_results"
    __table_args__ = (UniqueConstraint("asset_id", "period", "run_date", name="uq_backtest_asset_period_date"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    asset_id: Mapped[int] = mapped_column(Integer, ForeignKey("assets.id"), nullable=False)
    period: Mapped[str] = mapped_column(String(5), nullable=False)  # "7d", "30d", "90d"
    run_date: Mapped[date] = mapped_column(Date, nullable=False)
    win_rate: Mapped[float] = mapped_column(Float, nullable=False)
    total_return: Mapped[float] = mapped_column(Float, nullable=False)
    buy_hold_return: Mapped[float] = mapped_column(Float, nullable=False)
    max_drawdown: Mapped[float] = mapped_column(Float, nullable=False)
    sharpe_ratio: Mapped[float | None] = mapped_column(Float, nullable=True)
    daily_results: Mapped[dict] = mapped_column(JSONB, nullable=True)  # detailed per-day results
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
```

### Migration Number
Next migration: `014_portfolio_risk.py` (after existing 013_ownership_due_diligence.py)

## Backtest Implementation Strategy

### Cost Management
- 90-day backtest = 90 LLM calls per asset. At ~$0.005-0.01/call with gpt-4o-mini, this is $0.45-0.90 per backtest.
- Cache aggressively: if a backtest for the same asset+period+run_date exists, return cached result.
- Engine signals can be pre-computed without LLM (pure computation). Only the final verdict requires LLM.
- Consider caching engine signals per (asset, date) to avoid recomputing for different period lengths.

### Progress Feedback
- Send initial "Processing..." message
- Edit message with progress every ~10 days processed: "Backtesting BTC: 20/90 days..."
- Final edit with results

### Pipeline Replay Logic
```python
# For each historical date in the backtest period:
# 1. Load price data up to that date (no look-ahead)
# 2. Run all applicable engines on that data slice
# 3. Call LLM to produce verdict (same prompt as decide_stage)
# 4. Compare verdict to actual next-day price movement
# 5. Aggregate: win rate, return, drawdown, Sharpe
```

## Concentration Risk Implementation

### Sector Mapping
Use existing `IDX_SECTOR_MAP` from `src/engines/valuation.py` (53 tickers, 12 sectors). Import it in `src/risk/concentration.py`.

### Currency Exposure
- `asset_type == "stock"` implies IDR denomination
- `asset_type == "crypto"` implies USD denomination
- Compute: IDR% = count(stock assets) / total assets, USD% = count(crypto assets) / total assets
- Equal-weight assumption since no actual position sizes exist

### Equal-Weight Assumption
The system tracks signals, not actual portfolio positions. For concentration and VaR:
- Each watchlist asset is assumed to be 1/N of the portfolio
- This must be clearly documented in output: "Based on equal-weight portfolio assumption"

## Enhanced Fundamentals Strategy

### 5-Year Trend Data Source
**Primary:** `FinancialData` table (parsed from IDX PDF reports). Ordered by `period_date DESC`, group by year to get annual figures.
**Fallback:** `StockFundamental` from yfinance (only has current snapshot, not historical). For yfinance historical, could query `yfinance.Ticker.financials` (annual data) but this requires yfinance calls which should happen in pipeline, not bot.

**Recommendation:** Enhance the pipeline's `fetch_fundamentals()` to also fetch 5-year historical ratios from yfinance and store them in a new column or table. The bot reads pre-computed 5-year trends from DB.

### Earnings Quality Algorithm
```python
def assess_earnings_quality(financials: list[dict]) -> dict:
    """Check for cash flow vs earnings divergence."""
    latest = financials[0]  # Most recent period

    net_profit = latest.get("net_profit", 0)
    operating_cf = latest.get("operating_cash_flow", 0)

    # Red flag: net profit positive but operating CF negative
    cf_divergence = False
    if net_profit > 0 and operating_cf < 0:
        cf_divergence = True

    # Red flag: operating CF significantly less than net profit (>50% gap)
    cf_ratio = operating_cf / net_profit if net_profit != 0 else 0
    low_cf_quality = cf_ratio < 0.5 and net_profit > 0

    return {
        "cf_divergence": cf_divergence,
        "low_cf_quality": low_cf_quality,
        "cf_to_earnings_ratio": round(cf_ratio, 2),
    }
```

### Dividend Analysis
```python
def analyze_dividends(fundamental: StockFundamental, financials: list[dict]) -> dict:
    """Compute dividend metrics from available data."""
    result = {}

    if fundamental.dividend_yield is not None:
        result["yield"] = fundamental.dividend_yield

    # Payout ratio = dividends per share / earnings per share
    # FCF coverage = FCF / total dividends
    latest = financials[0] if financials else {}
    fcf = latest.get("free_cash_flow", 0)
    dividends = latest.get("dividends_paid", 0)  # May need to add this metric

    if dividends and dividends != 0:
        result["fcf_coverage"] = round(fcf / abs(dividends), 2) if fcf else 0

    return result
```

## Stress Test Scenario Data

### Preset Drawdowns
```python
STRESS_SCENARIOS = {
    "covid_2020": {
        "name": "COVID-19 Crash (Mar 2020)",
        "stock_drawdown": -0.37,    # IHSG peak-to-trough
        "crypto_drawdown": -0.50,   # BTC peak-to-trough
        "duration_days": 30,
    },
    "crypto_winter_2022": {
        "name": "Crypto Winter (2022)",
        "stock_drawdown": -0.10,    # IDX relatively stable
        "crypto_drawdown": -0.77,   # BTC Nov 2021 to Nov 2022
        "duration_days": 365,
    },
    "taper_tantrum_2013": {
        "name": "Taper Tantrum (2013)",
        "stock_drawdown": -0.15,    # EM stocks correction
        "crypto_drawdown": -0.05,   # BTC was early, different dynamics
        "duration_days": 90,
    },
    "gfc_2008": {
        "name": "Global Financial Crisis (2008)",
        "stock_drawdown": -0.60,    # IHSG peak-to-trough
        "crypto_drawdown": 0.0,     # BTC didn't exist yet
        "duration_days": 365,
    },
}
```

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2+ with pytest-asyncio |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` |
| Quick run command | `pytest tests/test_risk/ -x` |
| Full suite command | `pytest` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| RISK-01 | Correlation matrix computation + high-pair alerts | unit | `pytest tests/test_risk/test_correlation.py -x` | Wave 0 |
| RISK-02 | Concentration: sector, single-asset, currency | unit | `pytest tests/test_risk/test_concentration.py -x` | Wave 0 |
| RISK-03 | Historical VaR (daily/weekly) + max drawdown | unit | `pytest tests/test_risk/test_var.py -x` | Wave 0 |
| RISK-04 | Sharpe + Sortino ratios | unit | `pytest tests/test_risk/test_metrics.py -x` | Wave 0 |
| RISK-05 | Stress test with preset scenarios | unit | `pytest tests/test_risk/test_stress.py -x` | Wave 0 |
| FUND-01 | 5-year trend sparklines | unit | `pytest tests/test_report/test_formatter_risk.py -x` | Wave 0 |
| FUND-02 | Earnings quality analysis | unit | `pytest tests/test_risk/test_earnings_quality.py -x` | Wave 0 |
| FUND-03 | Dividend analysis | unit | `pytest tests/test_risk/test_dividends.py -x` | Wave 0 |
| TBOT-08 | /backtest handler + subprocess | unit | `pytest tests/test_bot/test_backtest_handler.py -x` | Wave 0 |
| TBOT-12 | /portfolio handler | unit | `pytest tests/test_bot/test_portfolio_handler.py -x` | Wave 0 |
| REPT-06 | Daily report risk snapshot section | unit | `pytest tests/test_data/test_report_risk.py -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/test_risk/ tests/test_bot/test_portfolio_handler.py tests/test_bot/test_backtest_handler.py -x`
- **Per wave merge:** `pytest`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_risk/` directory -- new module, all test files needed
- [ ] `tests/test_risk/conftest.py` -- fixtures for price DataFrames, mock assets
- [ ] `tests/test_bot/test_portfolio_handler.py` -- handler tests
- [ ] `tests/test_bot/test_backtest_handler.py` -- handler tests
- [ ] `tests/test_data/test_report_risk.py` -- risk snapshot in daily report

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Parametric VaR (normal distribution) | Historical simulation VaR | Well-established | Better for crypto fat tails per D-02 |
| Per-asset risk only | Portfolio-level risk (correlations, concentration) | This phase | Cross-asset view enables diversification insights |
| QoQ trends only | 5-year trend sparklines | This phase | Longer-term fundamental picture |

## Open Questions

1. **Position sizes for portfolio risk**
   - What we know: System tracks signals, not actual positions. No buy/sell execution.
   - What's unclear: Should we assume equal-weight? Price-weighted? User-defined allocations?
   - Recommendation: Equal-weight (1/N) is simplest and honest. Document assumption in output. User-defined allocations could be a v2 feature via /settings.

2. **Backtest LLM cost and rate limiting**
   - What we know: 90-day backtest needs ~90 LLM calls. gpt-4o-mini is cheap (~$0.005/call).
   - What's unclear: How fast can we make LLM calls? Rate limits? Should we batch?
   - Recommendation: Sequential calls with 0.5s delay. Cache results aggressively. 90-day backtest ~2-3 minutes.

3. **5-year historical fundamental data availability**
   - What we know: FinancialData table has parsed IDX PDF data (quarterly). yfinance has some historical annual data.
   - What's unclear: How many years of IDX PDF data are actually stored? yfinance coverage for .JK tickers?
   - Recommendation: Use whatever FinancialData periods exist. If <5 years, show available years. Supplement with yfinance annual fundamentals fetched in pipeline.

4. **Two-process boundary for backtest**
   - What we know: Bot cannot import src/pipeline or src/llm. Backtest needs LLM.
   - What's unclear: Cleanest architectural approach.
   - Recommendation: Subprocess approach. Bot spawns `python -m src.data.backtest`, reads results from DB. Avoids boundary violations entirely.

## Sources

### Primary (HIGH confidence)
- Codebase analysis: `src/data/analyze.py` -- existing correlation computation, engine pipeline
- Codebase analysis: `src/engines/network.py` -- correlation-based scoring patterns
- Codebase analysis: `src/engines/valuation.py` -- IDX_SECTOR_MAP (53 tickers, 12 sectors)
- Codebase analysis: `src/bot/handlers/` -- established handler pattern (auth, DB query, format, send)
- Codebase analysis: `src/pipeline/main.py` -- post-pipeline hook pattern (discovery scan, batch cross-cutting)
- Codebase analysis: `src/report/formatter.py` -- formatting, splitting, emoji patterns
- Codebase analysis: `src/db/models.py` -- all existing ORM models, 13 existing migrations

### Secondary (MEDIUM confidence)
- Historical drawdown numbers for stress scenarios (well-documented in financial literature)
- VaR computation methodology (standard financial risk management practice)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- all libraries already in project, no new deps needed
- Architecture: HIGH -- follows established codebase patterns (new module, bot handlers, pipeline hooks)
- Risk computations: HIGH -- standard financial math with numpy/pandas
- Backtest implementation: MEDIUM -- subprocess approach is pragmatic but needs careful implementation for progress feedback
- 5-year fundamentals: MEDIUM -- data availability in FinancialData table is uncertain
- Pitfalls: HIGH -- well-known issues in financial risk systems

**Research date:** 2026-03-27
**Valid until:** 2026-04-27 (stable domain, no fast-moving dependencies)
