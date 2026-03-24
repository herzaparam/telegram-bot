# Phase 3: Technical Engine + Pipeline Shell - Research

**Researched:** 2026-03-24
**Domain:** Technical analysis engines, quantitative analysis, pipeline orchestration
**Confidence:** HIGH

## Summary

Phase 3 implements the BaseEngine abstract class, TechnicalEngine, and QuantitativeEngine as the first two engines in the signal pipeline. The existing PipelineRunner already supports an "analyze" stage -- this phase wires it up with a StageFunc that loads price data from the DB, runs engines sequentially per asset, and stores results in a new `signals` table via SignalRepository.

The stack is well-constrained by CONTEXT.md decisions: pandas-ta-classic (v0.4.47) for technical indicators, pmdarima (v2.1.1) for auto-ARIMA, and numpy for Hurst exponent / Ornstein-Uhlenbeck calculations. Both libraries install cleanly with the existing pandas 3.0.1 + numpy 2.4.3 stack (verified via dry-run). The codebase already has strong patterns to follow: BaseFetcher for the abstract class design, PriceRepository for the signal repository, and ingest_stage for the StageFunc wiring.

**Primary recommendation:** Follow existing codebase patterns closely -- BaseEngine mirrors BaseFetcher, SignalRepository mirrors PriceRepository, analyze_stage mirrors ingest_stage. The main complexity is in correct indicator computation and zone-to-score mapping, not in architecture.

<user_constraints>

## User Constraints (from CONTEXT.md)

### Locked Decisions
- RSI: Dual period -- RSI(14) + RSI(7) for medium-term and short-term momentum
- MACD: Standard 12/26/9 configuration (fast EMA 12, slow EMA 26, signal line 9)
- Bollinger Bands: Dual bands -- outer (20-period, 2 sigma) + inner (20-period, 1 sigma) for extremes and early signals
- EMA: Full set -- 9, 21, 50, 100, 200 periods
- Volume: OBV (On-Balance Volume) trend direction + volume vs 20-day SMA
- Same parameters for both IDX stocks and crypto -- no asset-class-specific tuning
- Stick to required indicators only (RSI, MACD, Bollinger, EMA, volume) -- no extras like ATR/Stochastic in this phase
- Auto-ARIMA via pmdarima: auto_arima finds best (p,d,q) params, produces 1-day-ahead forecast with confidence interval
- Momentum: Rate of Change (ROC) at 5, 10, 20 day windows + Hurst exponent for regime detection
- Mean reversion: Ornstein-Uhlenbeck half-life estimation + Z-score of price relative to rolling mean (20/50 day)
- Regime detection: Hurst-driven weighting -- if H>0.5 (trending), weight momentum higher; if H<0.5 (mean-reverting), weight z-score higher
- Regime included in reasoning text
- Minimum data requirement: 200 trading days per asset
- Graceful degradation: skip ARIMA and Hurst if <200 days, run only ROC and basic z-score, lower confidence to reflect limited data
- Weighted average with zone mapping: each indicator maps to a sub-score (-1 to +1) via predefined zones
- Confidence: signal agreement + data quality penalty
- Indicator weights stored in pydantic-settings config, overridable via env vars
- Reasoning format: key indicators summary -- concise, factual
- Full signals table via Alembic migration: (asset_id, date, category, score, confidence, reasoning, indicators, data_quality)
- Add price_at_signal column: store asset's latest close price when signal is generated
- data_quality JSONB tracks: sources available, sources failed, trading days of data used, indicators skipped
- indicators JSONB stores final computed values only
- Signals are idempotent: UPSERT on (asset_id, date, category)
- Batch insert: all engine signals for one asset collected then bulk-inserted in one transaction
- SignalRepository class following price_repo pattern

### Claude's Discretion
- Exact zone thresholds for each indicator (e.g., RSI <30 -> +0.8 or +0.7)
- Exact indicator weight values (starting point, user can tune via config)
- BaseEngine abstract class implementation details
- Auto-ARIMA parameter bounds and fitting strategy
- Hurst exponent calculation method (R/S analysis vs DFA)
- SignalRepository method signatures and query patterns
- Analyze stage orchestration within PipelineRunner
- Error handling and logging for individual engine failures

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope

</user_constraints>

<phase_requirements>

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| ENGN-01 | Technical analysis engine (RSI, MACD, Bollinger, MA, volume) outputs score/confidence/reasoning | pandas-ta-classic provides all indicators; zone mapping converts to score; signal agreement drives confidence; reasoning is formatted indicator summary |
| ENGN-03 | Quantitative/statistical engine (momentum, mean reversion, ARIMA) | pmdarima for auto-ARIMA; numpy R/S analysis for Hurst; OLS regression for OU half-life; ROC via pandas-ta or manual calculation |

</phase_requirements>

## Project Constraints (from CLAUDE.md)

- Python 3.13 with strict mypy
- SQLAlchemy async ORM with asyncpg driver for all DB operations
- pydantic-settings for configuration
- structlog for JSON logging
- Alembic for database migrations
- ruff for linting/formatting
- pytest with asyncio_mode = "auto"
- pandas-ta-classic (v0.4.47) for technical indicators (PROJECT.md constraint)
- 1GB peak RAM budget (PROJECT.md constraint)
- Sequential engine execution per asset (PROJECT.md constraint)
- Engine execution is CPU-bound, must run synchronously (ARCHITECTURE.md constraint)

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pandas-ta-classic | 0.4.47 | RSI, MACD, Bollinger, EMA, OBV calculation | Project decision; community fork of pandas-ta, drop-in pandas extension with 150+ indicators |
| pmdarima | 2.1.1 | Auto-ARIMA model fitting and forecasting | Standard Python ARIMA library; wraps statsmodels with scikit-learn interface; auto parameter selection |
| numpy | 2.4.3 (already installed) | Hurst exponent R/S analysis, OU half-life regression, array operations | Already in stack via pandas |
| scipy | 1.17.1 (via pmdarima) | Statistical functions if needed for OU regression | Comes as pmdarima dependency |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| statsmodels | 0.14.6 (via pmdarima) | OLS regression for OU half-life estimation | OU half-life calculation uses statsmodels OLS or numpy lstsq |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| pandas-ta-classic | TA-Lib (C extension) | TA-Lib requires C library install, harder to deploy; pandas-ta is pure Python |
| pmdarima | statsforecast (Nixtla) | statsforecast is faster but pmdarima is more mature and well-documented for auto_arima |
| Manual Hurst | hurst PyPI package | hurst package adds a dependency for ~30 lines of numpy code; hand-roll is fine here |

**Installation:**
```bash
uv add pandas-ta-classic pmdarima
```

**Version verification:** Verified via `uv pip install --dry-run` on 2026-03-24. Both packages resolve cleanly against pandas 3.0.1 + numpy 2.4.3 + Python 3.13. pmdarima pulls in scipy 1.17.1, statsmodels 0.14.6, scikit-learn 1.8.0, joblib 1.5.3, cython 3.2.4, patsy 1.0.2, threadpoolctl 3.6.0.

## Architecture Patterns

### Recommended Project Structure
```
src/
├── engines/                    # Signal engines (one per category)
│   ├── __init__.py
│   ├── base.py                 # BaseEngine ABC, Signal dataclass
│   ├── technical.py            # TechnicalEngine (RSI, MACD, BB, EMA, volume)
│   └── quantitative.py         # QuantitativeEngine (momentum, mean reversion, ARIMA)
├── db/
│   ├── models.py               # Add Signal ORM model
│   ├── signal_repo.py          # SignalRepository (upsert_signals, get_signals_for_asset, get_latest_signals)
│   └── migrations/versions/
│       └── 003_signals_table.py # Alembic migration for signals table
├── data/
│   └── analyze.py              # analyze_stage() StageFunc
└── config.py                   # Extended with indicator weight settings
tests/
├── test_engines/
│   ├── __init__.py
│   ├── conftest.py             # Shared engine test fixtures (sample DataFrames)
│   ├── test_base_engine.py
│   ├── test_technical.py
│   └── test_quantitative.py
├── test_data/
│   └── test_analyze.py         # Analyze stage tests
└── test_db/
    └── test_signal_repo.py     # SignalRepository tests
```

### Pattern 1: BaseEngine Abstract Class
**What:** Abstract class mirroring BaseFetcher pattern from `src/data/base.py`, but synchronous (CPU-bound).
**When to use:** All engine implementations must subclass this.
**Example:**
```python
# Source: plan/ARCHITECTURE.md Core Interfaces section
from abc import ABC, abstractmethod
from dataclasses import dataclass

@dataclass(frozen=True)
class Signal:
    """Output of a single engine analysis for one asset."""
    category: str          # e.g., "technical", "quantitative"
    score: float           # -1.0 (strong sell) to +1.0 (strong buy)
    confidence: float      # 0.0 to 1.0
    reasoning: str         # human-readable explanation
    indicators: dict       # final computed values, e.g., {"rsi_14": 28}
    data_quality: dict     # {"sources_available": [...], "indicators_skipped": [...]}

class BaseEngine(ABC):
    @abstractmethod
    def analyze(self, asset_id: int, asset_symbol: str, df: pd.DataFrame) -> Signal:
        """Run analysis on price DataFrame. Synchronous (CPU-bound).

        Must never raise -- returns score=0/confidence=0 on failure.
        """
        ...

    @property
    @abstractmethod
    def category(self) -> str:
        """Engine category name (e.g., 'technical')."""
        ...

    @property
    def supports_stocks(self) -> bool:
        return True

    @property
    def supports_crypto(self) -> bool:
        return True
```

### Pattern 2: Analyze Stage as StageFunc
**What:** An async function matching `StageFunc = Callable[[AsyncSession, Asset], Awaitable[None]]` that loads price data, runs engines, and stores signals.
**When to use:** Wired into PipelineRunner via `stage_funcs["analyze"]`.
**Example:**
```python
# Following pattern from src/data/ingest.py
import gc
import pandas as pd
from sqlalchemy.ext.asyncio import AsyncSession
from src.db.models import Asset

async def analyze_stage(session: AsyncSession, asset: Asset) -> None:
    """Analyze stage: load prices -> run engines -> store signals."""
    log = logger.bind(asset=asset.symbol, asset_type=asset.asset_type)

    # 1. Load price data from DB into DataFrame
    df = await _load_price_dataframe(session, asset)
    if df.empty:
        log.warning("no_price_data_for_analysis")
        return

    # 2. Run engines sequentially (CPU-bound, synchronous)
    engines = _get_engines_for_asset(asset)
    signals = []
    for engine in engines:
        try:
            signal = engine.analyze(asset.id, asset.symbol, df)
            signals.append(signal)
        except Exception as exc:
            log.warning("engine_failed", engine=engine.category, error=str(exc))
            signals.append(_failed_signal(engine.category))

    # 3. Store all signals in one transaction
    await signal_repo.upsert_signals(session, asset.id, date.today(), signals, price_at_signal=df["close"].iloc[-1])

    # 4. Release DataFrame memory
    del df
    gc.collect()
```

### Pattern 3: Zone Mapping for Score Composition
**What:** Each indicator is mapped to a sub-score (-1 to +1) using predefined threshold zones, then combined via weighted average.
**When to use:** Inside TechnicalEngine.analyze() to convert raw indicator values to a composite score.
**Example:**
```python
def _rsi_to_score(rsi: float) -> float:
    """Map RSI value to sub-score using zone thresholds."""
    if rsi < 20:
        return 0.9   # Strongly oversold -> bullish
    elif rsi < 30:
        return 0.6   # Oversold -> moderately bullish
    elif rsi < 45:
        return 0.2   # Slightly below neutral
    elif rsi <= 55:
        return 0.0   # Neutral
    elif rsi <= 70:
        return -0.2  # Slightly overbought
    elif rsi <= 80:
        return -0.6  # Overbought -> moderately bearish
    else:
        return -0.9  # Strongly overbought -> bearish
```

### Pattern 4: SignalRepository Following PriceRepository
**What:** Async repository class using SQLAlchemy ORM (not raw asyncpg) for signal CRUD.
**When to use:** All signal read/write operations.
**Example:**
```python
# Following pattern from src/db/price_repo.py but using SQLAlchemy ORM
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

async def upsert_signals(
    session: AsyncSession,
    asset_id: int,
    signal_date: date,
    signals: list[Signal],
    price_at_signal: float,
) -> int:
    """Bulk upsert signals for one asset. UPSERT on (asset_id, date, category)."""
    for signal in signals:
        stmt = pg_insert(SignalModel).values(
            asset_id=asset_id,
            date=signal_date,
            category=signal.category,
            score=signal.score,
            confidence=signal.confidence,
            reasoning=signal.reasoning,
            indicators=signal.indicators,
            data_quality=signal.data_quality,
            price_at_signal=price_at_signal,
        ).on_conflict_do_update(
            index_elements=["asset_id", "date", "category"],
            set_={
                "score": signal.score,
                "confidence": signal.confidence,
                "reasoning": signal.reasoning,
                "indicators": signal.indicators,
                "data_quality": signal.data_quality,
                "price_at_signal": price_at_signal,
            },
        )
        await session.execute(stmt)
    await session.commit()
    return len(signals)
```

### Anti-Patterns to Avoid
- **Running engines with asyncio.gather:** Engine execution is CPU-bound. asyncio.gather would starve the event loop. Run sequentially in main thread.
- **Letting engine exceptions propagate:** An engine failure must never halt the pipeline. Catch all exceptions in the analyze stage, return score=0/confidence=0.
- **Storing intermediate indicator series in DB:** Only store final computed values in the `indicators` JSONB column (e.g., `{"rsi_14": 28}`), not the full time series.
- **Loading all price history into memory at once:** Load only the rows needed (200 days max for quantitative, ~200 for technical). Use SQL LIMIT/ORDER BY.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| RSI calculation | Custom RSI with pandas rolling | `df.ta.rsi(length=14)` from pandas-ta-classic | Handles edge cases (initial NaN window, Wilder smoothing) |
| MACD calculation | Custom EMA subtraction | `df.ta.macd(fast=12, slow=26, signal=9)` | Returns MACD line, signal line, and histogram in one call |
| Bollinger Bands | Custom rolling mean + std | `df.ta.bbands(length=20, std=2)` | Correct SMA-based bands with proper NaN handling |
| EMA calculation | Custom exponential smoothing | `df.ta.ema(length=N)` | Correct decay factor and initialization |
| OBV calculation | Custom cumulative volume sum | `df.ta.obv()` | Handles sign-based accumulation correctly |
| ARIMA model selection | Grid search over (p,d,q) | `pmdarima.auto_arima()` | AIC/BIC-based selection, differencing tests, convergence handling |
| Rate of Change | Manual pct_change | `df.ta.roc(length=N)` | pandas-ta-classic has ROC built in |

**Key insight:** pandas-ta-classic handles all the edge cases in indicator computation (initial NaN windows, smoothing method selection, lookback period handling). Manual implementations commonly get Wilder smoothing wrong for RSI or use wrong EMA initialization.

## Common Pitfalls

### Pitfall 1: Insufficient Data for Indicators
**What goes wrong:** RSI(14) needs 14+ rows, EMA(200) needs 200+ rows, ARIMA needs 200+ rows. Running on new assets with <200 rows produces NaN or garbage values.
**Why it happens:** Not checking DataFrame length before computing indicators.
**How to avoid:** Check `len(df)` against minimum requirements before each indicator. Skip indicators that need more data than available. Reduce confidence proportionally.
**Warning signs:** NaN values in indicator outputs, unusually volatile scores on new assets.

### Pitfall 2: pandas-ta Returns NaN Columns
**What goes wrong:** pandas-ta functions return Series/DataFrame with NaN values for the initial lookback period (e.g., first 14 rows for RSI). Using `.iloc[-1]` to get the latest value works, but using the full column for averaging will include NaNs.
**Why it happens:** This is expected behavior -- indicators need warmup periods.
**How to avoid:** Always use `.iloc[-1]` or `.dropna()` before aggregation. Check for NaN explicitly before zone mapping.
**Warning signs:** Score returns NaN or 0 unexpectedly.

### Pitfall 3: ARIMA Fitting Failures
**What goes wrong:** `auto_arima()` can raise `ValueError` or fail to converge on certain data patterns (highly volatile crypto, flat price series).
**Why it happens:** ARIMA assumes stationarity after differencing; some series don't fit this model well.
**How to avoid:** Wrap `auto_arima()` in try/except. Use `suppress_warnings=True`, `error_action='ignore'`, and `stepwise=True` for faster fitting. Set reasonable bounds: `max_p=5, max_q=5, max_d=2`. On failure, return score=0/confidence=0 with reasoning explaining the failure.
**Warning signs:** Fitting takes >10 seconds per asset (usually <2s), convergence warnings in logs.

### Pitfall 4: Hurst Exponent Instability
**What goes wrong:** Hurst exponent yields unexpected values (very close to 0.5) or varies significantly based on implementation details and data length.
**Why it happens:** R/S analysis is sensitive to short-range dependence and data length. Real financial data rarely gives clean H values.
**How to avoid:** Use at least 200 data points. Don't over-interpret small deviations from 0.5. Consider using a band around 0.5 (e.g., 0.45-0.55) as "indeterminate regime" rather than a hard threshold.
**Warning signs:** H values flipping between trending and mean-reverting on consecutive runs.

### Pitfall 5: Memory Leak from DataFrame Accumulation
**What goes wrong:** Processing 6 assets sequentially without releasing DataFrames causes memory to grow.
**Why it happens:** Python's garbage collector doesn't immediately free large DataFrames.
**How to avoid:** Explicitly `del df` and call `gc.collect()` after each asset, as specified in ARCHITECTURE.md daily execution flow.
**Warning signs:** Pipeline memory exceeding 500MB during analyze stage.

### Pitfall 6: Signals Table Migration Conflict with TimescaleDB
**What goes wrong:** The signals table should NOT be a hypertable (unlike price_history). Using `date` type (not `timestamp`) avoids accidental hypertable conversion.
**Why it happens:** Copying price_history migration pattern blindly.
**How to avoid:** Use a regular PostgreSQL table with a standard composite unique constraint on (asset_id, date, category). Use `sa.Date` column type, not `sa.DateTime(timezone=True)`.
**Warning signs:** Migration errors related to TimescaleDB on the signals table.

## Code Examples

### pandas-ta-classic Technical Indicator Computation
```python
# Source: pandas-ta-classic PyPI docs + GitHub README
import pandas as pd
import pandas_ta_classic as ta  # type: ignore[import-untyped]

def compute_technical_indicators(df: pd.DataFrame) -> dict:
    """Compute all required technical indicators on a price DataFrame.

    DataFrame must have columns: open, high, low, close, volume.
    Returns dict of indicator name -> latest value.
    """
    results = {}

    # RSI dual period
    rsi_14 = df.ta.rsi(length=14)
    rsi_7 = df.ta.rsi(length=7)
    results["rsi_14"] = float(rsi_14.iloc[-1]) if rsi_14 is not None else None
    results["rsi_7"] = float(rsi_7.iloc[-1]) if rsi_7 is not None else None

    # MACD 12/26/9
    macd = df.ta.macd(fast=12, slow=26, signal=9)
    if macd is not None:
        results["macd_line"] = float(macd.iloc[-1, 0])       # MACD line
        results["macd_histogram"] = float(macd.iloc[-1, 1])   # Histogram
        results["macd_signal"] = float(macd.iloc[-1, 2])      # Signal line

    # Bollinger Bands (outer 2 sigma, inner 1 sigma)
    bb_outer = df.ta.bbands(length=20, std=2)
    bb_inner = df.ta.bbands(length=20, std=1)
    if bb_outer is not None:
        results["bb_lower_2"] = float(bb_outer.iloc[-1, 0])
        results["bb_mid"] = float(bb_outer.iloc[-1, 1])
        results["bb_upper_2"] = float(bb_outer.iloc[-1, 2])
    if bb_inner is not None:
        results["bb_lower_1"] = float(bb_inner.iloc[-1, 0])
        results["bb_upper_1"] = float(bb_inner.iloc[-1, 2])

    # EMA set
    for period in [9, 21, 50, 100, 200]:
        ema = df.ta.ema(length=period)
        results[f"ema_{period}"] = float(ema.iloc[-1]) if ema is not None else None

    # OBV
    obv = df.ta.obv()
    if obv is not None:
        results["obv"] = float(obv.iloc[-1])
        # OBV trend: compare current vs 20-day SMA of OBV
        obv_sma = obv.rolling(20).mean()
        results["obv_trend"] = "bullish" if obv.iloc[-1] > obv_sma.iloc[-1] else "bearish"

    # Volume vs 20-day SMA
    vol_sma = df["volume"].rolling(20).mean()
    results["volume_ratio"] = float(df["volume"].iloc[-1] / vol_sma.iloc[-1]) if vol_sma.iloc[-1] > 0 else 1.0

    return results
```

### Hurst Exponent via R/S Analysis
```python
# Source: R/S analysis method, standard implementation
import numpy as np

def hurst_exponent(prices: np.ndarray) -> float:
    """Calculate Hurst exponent using rescaled range (R/S) analysis.

    Args:
        prices: Array of closing prices (at least 100 points).

    Returns:
        Hurst exponent H in [0, 1].
        H < 0.5: mean-reverting, H = 0.5: random walk, H > 0.5: trending
    """
    returns = np.diff(np.log(prices))
    n = len(returns)

    # Use multiple sub-series sizes
    sizes = []
    rs_values = []

    for size in [16, 32, 64, 128, 256]:
        if size > n:
            break
        num_subseries = n // size
        rs_list = []

        for i in range(num_subseries):
            subseries = returns[i * size : (i + 1) * size]
            mean = np.mean(subseries)
            deviations = np.cumsum(subseries - mean)
            r = np.max(deviations) - np.min(deviations)
            s = np.std(subseries, ddof=1)
            if s > 0:
                rs_list.append(r / s)

        if rs_list:
            sizes.append(size)
            rs_values.append(np.mean(rs_list))

    if len(sizes) < 2:
        return 0.5  # Insufficient data, assume random walk

    # Linear regression on log-log scale
    log_sizes = np.log(sizes)
    log_rs = np.log(rs_values)
    slope, _ = np.polyfit(log_sizes, log_rs, 1)

    return float(np.clip(slope, 0.0, 1.0))
```

### Ornstein-Uhlenbeck Half-Life Estimation
```python
# Source: Standard OU half-life via OLS regression
import numpy as np

def ou_half_life(prices: np.ndarray) -> float:
    """Estimate half-life of mean reversion using OU model.

    Uses linear regression of price changes on lagged prices:
    delta_y(t) = lambda * y(t-1) + epsilon
    half_life = -ln(2) / lambda

    Args:
        prices: Array of closing prices.

    Returns:
        Half-life in trading days. Returns float('inf') if not mean-reverting.
    """
    y = prices[1:]
    y_lag = prices[:-1]
    delta_y = y - y_lag

    # OLS: delta_y = lambda * y_lag + intercept
    # Using numpy lstsq
    x = np.column_stack([y_lag, np.ones(len(y_lag))])
    result = np.linalg.lstsq(x, delta_y, rcond=None)
    lambda_param = result[0][0]

    if lambda_param >= 0:
        return float("inf")  # Not mean-reverting

    half_life = -np.log(2) / lambda_param
    return float(half_life)
```

### Auto-ARIMA Forecast
```python
# Source: pmdarima official docs
import pmdarima as pm  # type: ignore[import-untyped]
import numpy as np

def arima_forecast(prices: np.ndarray) -> tuple[float, float, float]:
    """Fit auto-ARIMA and produce 1-day-ahead forecast with confidence interval.

    Args:
        prices: Array of closing prices (at least 200 points recommended).

    Returns:
        Tuple of (forecast_price, lower_ci, upper_ci) at 95% confidence.

    Raises:
        ValueError: If model fitting fails (caller should catch).
    """
    model = pm.auto_arima(
        prices,
        start_p=1, start_q=1,
        max_p=5, max_q=5,
        max_d=2,
        seasonal=False,
        stepwise=True,
        suppress_warnings=True,
        error_action="ignore",
        trace=False,
    )

    forecast, conf_int = model.predict(n_periods=1, return_conf_int=True, alpha=0.05)
    return float(forecast[0]), float(conf_int[0][0]), float(conf_int[0][1])
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| pandas-ta (original) | pandas-ta-classic (community fork) | Mid-2025 | Original maintainer warned of archival; classic fork is drop-in compatible |
| Manual ARIMA order selection | pmdarima auto_arima | Stable since 2019 | Auto parameter selection eliminates manual (p,d,q) grid search |
| ta-lib (C library) | pandas-ta-classic (pure Python) | N/A | pandas-ta avoids C compilation dependencies; adequate performance for daily analysis |

**Deprecated/outdated:**
- Original `pandas-ta` package: maintainer warned of archival by July 2026; use `pandas-ta-classic` instead

## Open Questions

1. **pandas-ta-classic MACD column ordering**
   - What we know: MACD returns a DataFrame with 3 columns (MACD, histogram, signal)
   - What's unclear: Exact column names may be `MACD_12_26_9`, `MACDh_12_26_9`, `MACDs_12_26_9` -- need to verify at implementation time
   - Recommendation: Use `.iloc[-1, 0/1/2]` or check column names at runtime; add a unit test verifying column structure

2. **pandas-ta-classic bbands column ordering**
   - What we know: Returns DataFrame with 3+ columns (lower, mid, upper, bandwidth, percent)
   - What's unclear: Exact column count and order may vary by version
   - Recommendation: Same approach -- verify column structure in unit test

3. **mypy compatibility with pandas-ta-classic and pmdarima**
   - What we know: Both are untyped packages; mypy strict mode will flag imports
   - What's unclear: Whether stubs exist
   - Recommendation: Add both to mypy overrides with `ignore_missing_imports = true`, consistent with existing yfinance/ccxt/asyncpg overrides

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.13 | Runtime | Yes | 3.13 | -- |
| pandas | DataFrame ops | Yes | 3.0.1 | -- |
| numpy | Numerical computation | Yes | 2.4.3 | -- |
| pandas-ta-classic | Technical indicators | No (not yet installed) | 0.4.47 (resolved) | -- |
| pmdarima | Auto-ARIMA | No (not yet installed) | 2.1.1 (resolved) | -- |
| TimescaleDB | Signals table | Yes | 2.18.0-pg16 (Docker) | -- |
| Alembic | Migration | Yes | 1.18.4+ | -- |

**Missing dependencies with no fallback:**
- pandas-ta-classic and pmdarima must be added to pyproject.toml dependencies (Wave 0 task)

**Missing dependencies with fallback:**
- None

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2+ with pytest-asyncio |
| Config file | `pyproject.toml` [tool.pytest.ini_options] |
| Quick run command | `pytest tests/test_engines/ tests/test_data/test_analyze.py -x` |
| Full suite command | `pytest` |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| ENGN-01 | TechnicalEngine.analyze() returns valid Signal with RSI/MACD/BB/EMA/volume | unit | `pytest tests/test_engines/test_technical.py -x` | No -- Wave 0 |
| ENGN-01 | Technical score within [-1, 1], confidence within [0, 1] | unit | `pytest tests/test_engines/test_technical.py::TestScoreRange -x` | No -- Wave 0 |
| ENGN-01 | Technical engine handles <14 rows gracefully (degraded output) | unit | `pytest tests/test_engines/test_technical.py::TestInsufficientData -x` | No -- Wave 0 |
| ENGN-03 | QuantitativeEngine.analyze() returns valid Signal with momentum/reversion/ARIMA | unit | `pytest tests/test_engines/test_quantitative.py -x` | No -- Wave 0 |
| ENGN-03 | Regime detection weights momentum vs z-score based on Hurst | unit | `pytest tests/test_engines/test_quantitative.py::TestRegimeWeighting -x` | No -- Wave 0 |
| ENGN-03 | Graceful degradation with <200 days: skip ARIMA/Hurst, lower confidence | unit | `pytest tests/test_engines/test_quantitative.py::TestGracefulDegradation -x` | No -- Wave 0 |
| SC-1 | Pipeline produces signal records in DB for each asset | integration | `pytest tests/test_data/test_analyze.py -x` | No -- Wave 0 |
| SC-4 | Engine that fails returns score=0/confidence=0, no exception | unit | `pytest tests/test_engines/test_base_engine.py::TestFailureHandling -x` | No -- Wave 0 |
| SCHEMA | Signals table migration creates correct columns | unit | `pytest tests/test_data/test_migration.py::TestSignalsMigration -x` | No -- Wave 0 |
| REPO | SignalRepository upsert_signals works with UPSERT semantics | unit | `pytest tests/test_db/test_signal_repo.py -x` | No -- Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/test_engines/ tests/test_data/test_analyze.py tests/test_db/test_signal_repo.py -x`
- **Per wave merge:** `pytest`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_engines/__init__.py` -- package init
- [ ] `tests/test_engines/conftest.py` -- shared fixtures: sample price DataFrames (200+ rows, <200 rows, empty)
- [ ] `tests/test_engines/test_base_engine.py` -- BaseEngine contract tests
- [ ] `tests/test_engines/test_technical.py` -- TechnicalEngine unit tests
- [ ] `tests/test_engines/test_quantitative.py` -- QuantitativeEngine unit tests
- [ ] `tests/test_data/test_analyze.py` -- analyze_stage integration tests
- [ ] `tests/test_db/test_signal_repo.py` -- SignalRepository tests
- [ ] Framework install: `uv add pandas-ta-classic pmdarima` -- required before engine tests

## Sources

### Primary (HIGH confidence)
- Existing codebase: `src/pipeline/runner.py`, `src/data/base.py`, `src/db/price_repo.py`, `src/data/ingest.py` -- patterns to follow
- `plan/ARCHITECTURE.md` -- BaseEngine interface, Signal dataclass, signals table schema, sequential engine execution
- `src/db/models.py` -- ORM model patterns and naming conventions
- `.planning/phases/03-technical-engine-pipeline-shell/03-CONTEXT.md` -- all locked decisions

### Secondary (MEDIUM confidence)
- [pandas-ta-classic PyPI](https://pypi.org/project/pandas-ta-classic/) -- v0.4.47, indicator API
- [pandas-ta-classic GitHub](https://github.com/xgboosted/pandas-ta-classic) -- Strategy usage, column naming
- [pmdarima documentation](https://alkaline-ml.com/pmdarima/) -- auto_arima API, v2.1.1
- [pmdarima auto_arima reference](https://alkaline-ml.com/pmdarima/modules/generated/pmdarima.arima.auto_arima.html) -- parameter docs
- `uv pip install --dry-run` output -- dependency resolution verified 2026-03-24

### Tertiary (LOW confidence)
- Hurst exponent R/S analysis implementations -- multiple GitHub repos agree on the algorithm, but real-world accuracy on financial data varies
- OU half-life estimation via OLS -- standard textbook approach, reliable

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - packages verified via dry-run, project decisions locked
- Architecture: HIGH - closely follows existing codebase patterns (BaseFetcher, PriceRepository, ingest_stage)
- Pitfalls: HIGH - well-documented issues with indicator warmup periods, ARIMA convergence, and Hurst instability
- pandas-ta-classic column naming: MEDIUM - API verified via docs but exact column names need runtime verification
- Hurst/OU numerical stability: MEDIUM - algorithm is standard but financial data edge cases are unpredictable

**Research date:** 2026-03-24
**Valid until:** 2026-04-24 (stable libraries, locked decisions)
