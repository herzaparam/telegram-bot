"""Quantitative analysis engine with momentum, mean reversion, and ARIMA forecasting."""

from __future__ import annotations

import math

import numpy as np
import pandas as pd
import structlog

from src.config import settings
from src.engines.base import BaseEngine, Signal

logger = structlog.get_logger(__name__)

MIN_DAYS_FULL = 200  # Minimum for ARIMA/Hurst
MIN_DAYS_BASIC = 25  # Minimum for ROC/z-score


# ---------------------------------------------------------------------------
# Helper functions (module-level, private)
# ---------------------------------------------------------------------------


def _hurst_exponent(prices: np.ndarray) -> float:
    """Calculate Hurst exponent using rescaled range (R/S) analysis.

    Args:
        prices: Array of closing prices.

    Returns:
        Hurst exponent H in [0, 1].
        H < 0.5: mean-reverting, H = 0.5: random walk, H > 0.5: trending.
        Returns 0.5 if insufficient data.
    """
    if len(prices) < 32:
        return 0.5

    returns = np.diff(np.log(prices))
    n = len(returns)

    sizes: list[int] = []
    rs_values: list[float] = []

    for size in [16, 32, 64, 128, 256]:
        if size > n:
            break
        num_subseries = n // size
        rs_list: list[float] = []

        for i in range(num_subseries):
            subseries = returns[i * size : (i + 1) * size]
            mean = np.mean(subseries)
            deviations = np.cumsum(subseries - mean)
            r = float(np.max(deviations) - np.min(deviations))
            s = float(np.std(subseries, ddof=1))
            if s > 0:
                rs_list.append(r / s)

        if rs_list:
            sizes.append(size)
            rs_values.append(float(np.mean(rs_list)))

    if len(sizes) < 2:
        return 0.5  # Insufficient data, assume random walk

    # Linear regression on log-log scale
    log_sizes = np.log(np.array(sizes, dtype=float))
    log_rs = np.log(np.array(rs_values, dtype=float))
    slope, _ = np.polyfit(log_sizes, log_rs, 1)

    return float(np.clip(slope, 0.0, 1.0))


def _ou_half_life(prices: np.ndarray) -> float:
    """Estimate half-life of mean reversion using Ornstein-Uhlenbeck model.

    Uses linear regression: delta_y(t) = lambda * y(t-1) + intercept.
    half_life = -ln(2) / lambda.

    Args:
        prices: Array of closing prices.

    Returns:
        Half-life in trading days. Returns float('inf') if not mean-reverting.
    """
    y = prices[1:]
    y_lag = prices[:-1]
    delta_y = y - y_lag

    # OLS: delta_y = lambda * y_lag + intercept
    x = np.column_stack([y_lag, np.ones(len(y_lag))])
    result = np.linalg.lstsq(x, delta_y, rcond=None)
    lambda_param = float(result[0][0])

    if lambda_param >= 0:
        return float("inf")  # Not mean-reverting

    half_life = -math.log(2) / lambda_param
    return float(half_life)


def _arima_forecast(prices: np.ndarray) -> tuple[float, float, float]:
    """Fit auto-ARIMA and produce 1-day-ahead forecast with confidence interval.

    Args:
        prices: Array of closing prices (at least 200 points recommended).

    Returns:
        Tuple of (forecast_price, lower_ci, upper_ci) at 95% confidence.

    Raises:
        ValueError: If model fitting fails.
    """
    import pmdarima as pm  # type: ignore[import-untyped]

    model = pm.auto_arima(
        prices,
        start_p=1,
        start_q=1,
        max_p=5,
        max_q=5,
        max_d=2,
        seasonal=False,
        stepwise=True,
        suppress_warnings=True,
        error_action="ignore",
        trace=False,
    )

    forecast, conf_int = model.predict(n_periods=1, return_conf_int=True, alpha=0.05)
    return float(forecast[0]), float(conf_int[0][0]), float(conf_int[0][1])


def _roc_to_score(roc_5: float, roc_10: float, roc_20: float) -> float:
    """Map Rate of Change values to a score in [-1, 1].

    Weighted average: roc_5 * 0.5, roc_10 * 0.3, roc_20 * 0.2.
    Each ROC mapped to sub-score based on magnitude.
    """

    def _single_roc_score(roc: float) -> float:
        if roc > 5.0:
            return 0.7
        if roc > 2.0:
            return 0.4
        if roc > 0.0:
            return 0.1
        if roc > -2.0:
            return -0.1
        if roc > -5.0:
            return -0.4
        return -0.7

    s5 = _single_roc_score(roc_5)
    s10 = _single_roc_score(roc_10)
    s20 = _single_roc_score(roc_20)

    return s5 * 0.5 + s10 * 0.3 + s20 * 0.2


def _zscore_to_score(z_20: float, z_50: float) -> float:
    """Map Z-scores to a score in [-1, 1].

    Z-score below -2 -> +0.8 (oversold = bullish).
    Z-score below -1 -> +0.4.
    Between -1 and 1 -> 0.0.
    Above 1 -> -0.4.
    Above 2 -> -0.8 (overbought = bearish).
    Average z_20 and z_50 scores.
    """

    def _single_zscore_score(z: float) -> float:
        if z < -2.0:
            return 0.8
        if z < -1.0:
            return 0.4
        if z <= 1.0:
            return 0.0
        if z <= 2.0:
            return -0.4
        return -0.8

    return (_single_zscore_score(z_20) + _single_zscore_score(z_50)) / 2.0


def _arima_to_score(
    current_price: float,
    forecast: float,
    lower_ci: float,
    upper_ci: float,
) -> float:
    """Map ARIMA forecast to a score in [-1, 1].

    If forecast > current + (upper - current)*0.3 -> bullish.
    If forecast < current - (current - lower)*0.3 -> bearish.
    Scale by confidence interval width.
    """
    if current_price <= 0:
        return 0.0

    ci_width = upper_ci - lower_ci
    if ci_width <= 0:
        return 0.0

    pct_change = (forecast - current_price) / current_price

    # Scale by how far forecast is relative to CI width
    if ci_width > 0:
        normalized = (forecast - current_price) / (ci_width / 2)
    else:
        normalized = 0.0

    # Clamp to [-1, 1]
    score = float(np.clip(normalized * 0.5, -1.0, 1.0))
    return score


# ---------------------------------------------------------------------------
# QuantitativeEngine
# ---------------------------------------------------------------------------


class QuantitativeEngine(BaseEngine):
    """Quantitative analysis engine with momentum, mean reversion, and ARIMA.

    Computes:
    - Momentum: ROC at 5/10/20 days + Hurst exponent
    - Mean reversion: OU half-life + Z-score at 20/50 day windows
    - ARIMA: 1-day forecast with confidence interval

    Regime detection via Hurst exponent adjusts component weighting:
    - H > 0.55 (trending): momentum weighted higher
    - H < 0.45 (mean-reverting): mean reversion weighted higher
    - Otherwise: uses default config weights
    """

    @property
    def category(self) -> str:
        """Return the engine category."""
        return "quantitative"

    def analyze(self, asset_id: int, asset_symbol: str, df: pd.DataFrame) -> Signal:
        """Run quantitative analysis on price data.

        Never raises -- returns score=0/confidence=0 on total failure.
        """
        try:
            return self._analyze_impl(asset_id, asset_symbol, df)
        except Exception as exc:
            logger.warning(
                "quantitative_engine_failure",
                asset_id=asset_id,
                asset_symbol=asset_symbol,
                error=str(exc),
            )
            return Signal(
                category="quantitative",
                score=0.0,
                confidence=0.0,
                reasoning=f"Quantitative analysis failed: {exc}",
                indicators={},
                data_quality={"error": str(exc)},
            )

    def _analyze_impl(
        self, asset_id: int, asset_symbol: str, df: pd.DataFrame
    ) -> Signal:
        """Internal analysis implementation."""
        log = logger.bind(asset_id=asset_id, asset_symbol=asset_symbol)

        # Check minimum data requirements
        if df.empty or len(df) < MIN_DAYS_BASIC:
            return Signal(
                category="quantitative",
                score=0.0,
                confidence=0.0,
                reasoning=(
                    f"Insufficient data for quantitative analysis "
                    f"(need >= {MIN_DAYS_BASIC} trading days, got {len(df)})"
                ),
                indicators={},
                data_quality={"trading_days": len(df), "sufficient": False},
            )

        close = df["close"].values.astype(float)
        skipped: list[str] = []

        # --- ROC at 5, 10, 20 days ---
        roc_5 = float((close[-1] / close[-6] - 1) * 100) if len(close) > 5 else 0.0
        roc_10 = float((close[-1] / close[-11] - 1) * 100) if len(close) > 10 else 0.0
        roc_20 = float((close[-1] / close[-21] - 1) * 100) if len(close) > 20 else 0.0

        # --- Z-scores ---
        close_series = df["close"]
        rolling_mean_20 = close_series.rolling(20).mean()
        rolling_std_20 = close_series.rolling(20).std()
        rolling_mean_50 = close_series.rolling(50).mean()
        rolling_std_50 = close_series.rolling(50).std()

        z_20 = 0.0
        if (
            rolling_std_20.iloc[-1] is not None
            and not np.isnan(rolling_std_20.iloc[-1])
            and rolling_std_20.iloc[-1] > 0
        ):
            z_20 = float(
                (close_series.iloc[-1] - rolling_mean_20.iloc[-1])
                / rolling_std_20.iloc[-1]
            )

        z_50 = 0.0
        if (
            len(df) >= 50
            and rolling_std_50.iloc[-1] is not None
            and not np.isnan(rolling_std_50.iloc[-1])
            and rolling_std_50.iloc[-1] > 0
        ):
            z_50 = float(
                (close_series.iloc[-1] - rolling_mean_50.iloc[-1])
                / rolling_std_50.iloc[-1]
            )
        else:
            if len(df) < 50:
                skipped.append("z_score_50")

        # --- Full analysis (>= MIN_DAYS_FULL) ---
        hurst = 0.5
        ou_hl = float("inf")
        arima_forecast_val = None
        arima_lower = None
        arima_upper = None
        regime = "insufficient_data"

        if len(df) >= MIN_DAYS_FULL:
            # Hurst exponent
            hurst = _hurst_exponent(close)

            # OU half-life
            ou_hl = _ou_half_life(close)

            # ARIMA forecast
            try:
                arima_forecast_val, arima_lower, arima_upper = _arima_forecast(close)
            except Exception as exc:
                log.warning("arima_failed", error=str(exc))
                skipped.append("arima")

            # Regime detection
            if hurst > 0.55:
                regime = "trending"
            elif hurst < 0.45:
                regime = "mean_reverting"
            else:
                regime = "indeterminate"
        else:
            skipped.extend(["arima", "hurst", "ou_half_life"])
            regime = "insufficient_data"

        # --- Component scores ---
        momentum_score = _roc_to_score(roc_5, roc_10, roc_20)
        reversion_score = _zscore_to_score(z_20, z_50)

        arima_score = 0.0
        if arima_forecast_val is not None and arima_lower is not None and arima_upper is not None:
            arima_score = _arima_to_score(
                float(close[-1]), arima_forecast_val, arima_lower, arima_upper
            )

        # --- Regime-based weighting ---
        if regime == "trending":
            w_mom, w_rev, w_arima = 0.50, 0.20, 0.30
        elif regime == "mean_reverting":
            w_mom, w_rev, w_arima = 0.20, 0.50, 0.30
        else:
            # Use config weights (default or indeterminate/insufficient_data)
            w_mom = settings.weight_momentum
            w_rev = settings.weight_mean_reversion
            w_arima = settings.weight_arima

        # If ARIMA was skipped, redistribute its weight
        if "arima" in skipped:
            total_remaining = w_mom + w_rev
            if total_remaining > 0:
                w_mom = w_mom / total_remaining
                w_rev = w_rev / total_remaining
            w_arima = 0.0

        final_score = (
            momentum_score * w_mom + reversion_score * w_rev + arima_score * w_arima
        )
        final_score = float(np.clip(final_score, -1.0, 1.0))

        # --- Confidence ---
        # base_agreement: how many components agree with final direction
        components = [momentum_score, reversion_score]
        if arima_forecast_val is not None:
            components.append(arima_score)

        if final_score == 0.0:
            base_agreement = 0.5
        else:
            direction = 1.0 if final_score > 0 else -1.0
            agreeing = sum(
                1 for c in components if (c * direction) > 0 or c == 0.0
            )
            base_agreement = agreeing / len(components) if components else 0.5

        # Penalty for skipped components
        penalty = min(0.15 * len(skipped), 0.4)
        confidence = max(0.0, min(1.0, base_agreement * (1 - penalty)))

        # --- Build indicators dict ---
        indicators: dict[str, object] = {
            "roc_5": round(roc_5, 4),
            "roc_10": round(roc_10, 4),
            "roc_20": round(roc_20, 4),
            "z_score_20": round(z_20, 4),
            "z_score_50": round(z_50, 4),
            "hurst": round(hurst, 4),
            "ou_half_life": round(ou_hl, 2) if ou_hl != float("inf") else "inf",
            "regime": regime,
            "momentum_score": round(momentum_score, 4),
            "reversion_score": round(reversion_score, 4),
            "arima_score": round(arima_score, 4),
        }

        if arima_forecast_val is not None:
            indicators["arima_forecast"] = round(arima_forecast_val, 2)
            indicators["arima_lower_ci"] = round(arima_lower, 2)  # type: ignore[arg-type]
            indicators["arima_upper_ci"] = round(arima_upper, 2)  # type: ignore[arg-type]

        # --- Reasoning ---
        arima_part = ""
        if arima_forecast_val is not None:
            arima_part = f" ARIMA forecast={arima_forecast_val:.2f}."
        elif "arima" in skipped and len(df) >= MIN_DAYS_FULL:
            arima_part = " ARIMA skipped (fitting failure)."
        elif "arima" in skipped:
            arima_part = " ARIMA skipped (insufficient data)."

        reasoning = (
            f"Regime: {regime} (H={hurst:.2f}). "
            f"ROC(5d)={roc_5:.1f}%, Z-score(20d)={z_20:.2f}."
            f"{arima_part} "
            f"Momentum weighted {w_mom:.0%}."
        )

        # --- Data quality ---
        data_quality: dict[str, object] = {
            "trading_days": len(df),
            "sufficient": len(df) >= MIN_DAYS_FULL,
            "indicators_skipped": skipped,
        }

        return Signal(
            category="quantitative",
            score=round(final_score, 4),
            confidence=round(confidence, 4),
            reasoning=reasoning.strip(),
            indicators=indicators,
            data_quality=data_quality,
        )
