"""EmergingMethodsEngine: Fractal dimension (Hurst exponent) and wavelet decomposition."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pywt  # type: ignore[import-untyped]
import structlog

from src.engines.base import BaseEngine, Signal

logger = structlog.get_logger(__name__)

MIN_DAYS = 60


def _hurst_exponent(prices: np.ndarray, max_lag: int = 20) -> float:
    """Compute Hurst exponent via R/S analysis.

    Args:
        prices: Array of closing prices.
        max_lag: Maximum lag size for subseries.

    Returns:
        Hurst exponent H in [0, 1].
        H > 0.55: trending, H < 0.45: mean-reverting, else random walk.
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
        return 0.5

    log_sizes = np.log(np.array(sizes, dtype=float))
    log_rs = np.log(np.array(rs_values, dtype=float))
    slope, _ = np.polyfit(log_sizes, log_rs, 1)

    return float(np.clip(slope, 0.0, 1.0))


class EmergingMethodsEngine(BaseEngine):
    """Emerging methods engine using fractal dimension and wavelet decomposition.

    Computes:
    - Hurst exponent via R/S analysis for regime detection
    - Wavelet decomposition (db4, level 3) for multi-scale trend analysis
    - Fractal dimension (2 - H) as a complexity measure
    """

    @property
    def category(self) -> str:
        """Return the engine category."""
        return "emerging_methods"

    def analyze(self, asset_id: int, asset_symbol: str, df: pd.DataFrame) -> Signal:
        """Run emerging methods analysis on price data.

        Never raises -- returns score=0/confidence=0 on failure.
        """
        try:
            return self._analyze_impl(asset_id, asset_symbol, df)
        except Exception as exc:
            logger.warning(
                "emerging_engine_error",
                asset_id=asset_id,
                asset_symbol=asset_symbol,
                error=str(exc),
            )
            return Signal(
                category="emerging_methods",
                score=0.0,
                confidence=0.0,
                reasoning=f"Emerging methods analysis failed: {exc}",
                indicators={},
                data_quality={"error": str(exc)},
            )

    def _analyze_impl(
        self, asset_id: int, asset_symbol: str, df: pd.DataFrame
    ) -> Signal:
        """Internal analysis implementation."""
        # Guard: insufficient data
        if df.empty or len(df) < MIN_DAYS:
            return Signal(
                category="emerging_methods",
                score=0.0,
                confidence=0.0,
                reasoning=(
                    f"Insufficient data for fractal/wavelet analysis "
                    f"(need {MIN_DAYS}+ days, got {len(df)})"
                ),
                indicators={},
                data_quality={"trading_days": len(df), "sufficient": False},
            )

        close_arr = df["close"].values.astype(float)

        # --- 1. Hurst exponent ---
        hurst = _hurst_exponent(close_arr)

        if hurst > 0.55:
            regime = "trending"
        elif hurst < 0.45:
            regime = "mean_reverting"
        else:
            regime = "random"

        # --- 2. Wavelet decomposition ---
        # Use db4 wavelet, level 3
        max_level = pywt.dwt_max_level(len(close_arr), "db4")
        level = min(3, max_level)

        coeffs = pywt.wavedec(close_arr, "db4", level=level)
        # coeffs[0] = cA (approximation), coeffs[1:] = cD (detail) at each level

        # Compute energy ratio: energy in approximation / total energy
        total_energy = sum(float(np.sum(c ** 2)) for c in coeffs)
        approx_energy = float(np.sum(coeffs[0] ** 2))
        energy_ratio = approx_energy / total_energy if total_energy > 0 else 0.0

        # Trend direction from approximation coefficients
        ca = coeffs[0]
        if len(ca) >= 2:
            # Slope of last few approximation coefficients
            n_pts = min(5, len(ca))
            x = np.arange(n_pts, dtype=float)
            y = ca[-n_pts:]
            slope, _ = np.polyfit(x, y, 1)
            wavelet_trend_slope = float(slope)
        else:
            wavelet_trend_slope = 0.0

        # --- 3. Scoring ---
        if regime == "trending":
            # Use wavelet trend direction as score basis
            # Normalize slope relative to price magnitude
            price_scale = float(np.mean(close_arr[-20:])) if len(close_arr) >= 20 else float(np.mean(close_arr))
            if price_scale > 0:
                normalized_slope = wavelet_trend_slope / price_scale * 100.0
            else:
                normalized_slope = 0.0
            hurst_score = float(np.clip(normalized_slope * 2.0, -1.0, 1.0))

        elif regime == "mean_reverting":
            # Use Z-score of close vs 20-day mean, inverted
            rolling_mean = float(np.mean(close_arr[-20:]))
            rolling_std = float(np.std(close_arr[-20:], ddof=1))
            if rolling_std > 0:
                z_score = (close_arr[-1] - rolling_mean) / rolling_std
                # Invert: high Z = bearish for mean-reverting asset
                hurst_score = float(np.clip(-z_score * 0.5, -1.0, 1.0))
            else:
                hurst_score = 0.0
        else:
            # Random walk: near zero
            hurst_score = 0.0

        # Wavelet energy adjustment
        if energy_ratio > 0.6:
            # Strong trend energy strengthens signal
            sign = 1.0 if hurst_score >= 0 else -1.0
            hurst_score = hurst_score + sign * 0.2
        elif energy_ratio < 0.3:
            # Weak trend energy weakens signal
            sign = 1.0 if hurst_score >= 0 else -1.0
            hurst_score = hurst_score - sign * 0.1

        final_score = float(np.clip(hurst_score, -1.0, 1.0))

        # --- 4. Confidence ---
        # Stronger regime = higher confidence
        confidence = 0.2 + 0.2 * min(abs(hurst - 0.5) * 4.0, 1.0) + 0.1 * energy_ratio
        confidence = float(np.clip(confidence, 0.0, 0.7))

        # --- 5. Reasoning ---
        parts = [f"Regime: {regime} (H={hurst:.3f})"]
        if regime == "trending":
            direction = "bullish" if final_score > 0 else "bearish"
            parts.append(f"Wavelet trend {direction} (slope={wavelet_trend_slope:.2f})")
        elif regime == "mean_reverting":
            parts.append("Z-score inversion applied for mean-reverting regime")
        parts.append(f"Wavelet energy ratio={energy_ratio:.3f}")

        reasoning = "; ".join(parts)

        # --- 6. Indicators ---
        fractal_dimension = 2.0 - hurst
        indicators: dict[str, object] = {
            "hurst_exponent": round(hurst, 4),
            "regime": regime,
            "wavelet_energy_ratio": round(energy_ratio, 4),
            "wavelet_trend_slope": round(wavelet_trend_slope, 4),
            "fractal_dimension": round(fractal_dimension, 4),
        }

        return Signal(
            category="emerging_methods",
            score=round(final_score, 6),
            confidence=round(confidence, 4),
            reasoning=reasoning,
            indicators=indicators,
            data_quality={
                "trading_days": len(df),
                "sufficient": True,
                "wavelet": "db4",
                "wavelet_level": level,
            },
        )
