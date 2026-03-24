"""TechnicalEngine: RSI, MACD, Bollinger Bands, EMA, OBV, and volume analysis."""

from __future__ import annotations

import math

import pandas as pd
import pandas_ta_classic as _ta  # type: ignore[import-untyped]  # noqa: F401 -- registers .ta accessor
import structlog

from src.config import settings
from src.engines.base import BaseEngine, Signal

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Zone-mapping functions (module-level, private)
# ---------------------------------------------------------------------------


def _rsi_to_score(rsi: float) -> float:
    """Map RSI value to sub-score using zone thresholds.

    RSI < 20: strongly oversold -> bullish (+0.9)
    RSI < 30: oversold -> moderately bullish (+0.6)
    RSI < 45: slightly bullish (+0.2)
    RSI 45-55: neutral (0.0)
    RSI > 55: slightly bearish (-0.2)
    RSI > 70: overbought -> moderately bearish (-0.6)
    RSI > 80: strongly overbought -> bearish (-0.9)
    """
    if rsi < 20:
        return 0.9
    elif rsi < 30:
        return 0.6
    elif rsi < 45:
        return 0.2
    elif rsi <= 55:
        return 0.0
    elif rsi <= 70:
        return -0.2
    elif rsi <= 80:
        return -0.6
    else:
        return -0.9


def _macd_to_score(
    histogram: float, macd_line: float, signal_line: float
) -> float:
    """Map MACD values to sub-score.

    Positive histogram + MACD above signal -> bullish.
    Negative histogram + MACD below signal -> bearish.
    Crossover detection via sign comparison.
    """
    score = 0.0

    # Histogram direction
    if histogram > 0:
        score += 0.4
    elif histogram < 0:
        score -= 0.4

    # MACD vs signal line
    if macd_line > signal_line:
        score += 0.3
    elif macd_line < signal_line:
        score -= 0.3

    # Histogram magnitude amplifier (larger histogram = stronger signal)
    abs_hist = abs(histogram)
    if abs_hist > 0:
        magnitude_bonus = min(abs_hist / max(abs(macd_line), 1e-10), 1.0) * 0.1
        score += magnitude_bonus if histogram > 0 else -magnitude_bonus

    return max(-0.9, min(0.9, score))


def _bollinger_to_score(
    close: float,
    lower_2: float,
    lower_1: float,
    upper_1: float,
    upper_2: float,
    mid: float,
) -> float:
    """Map price position relative to Bollinger Bands to sub-score.

    Below lower_2: strongly oversold -> +0.9
    Below lower_1: oversold -> +0.5
    Between bands: neutral, scaled by distance from mid
    Above upper_1: overbought -> -0.5
    Above upper_2: strongly overbought -> -0.9
    """
    if close <= lower_2:
        return 0.9
    elif close <= lower_1:
        return 0.5
    elif close >= upper_2:
        return -0.9
    elif close >= upper_1:
        return -0.5
    else:
        # Between inner bands: scale proportionally from mid
        if upper_1 == lower_1:
            return 0.0
        half_range = (upper_1 - lower_1) / 2.0
        if half_range == 0:
            return 0.0
        deviation = (close - mid) / half_range
        return max(-0.3, min(0.3, -deviation * 0.3))


def _ema_to_score(close: float, emas: dict[int, float | None]) -> float:
    """Map price position relative to EMAs to sub-score.

    Count how many EMAs price is above/below.
    Weight shorter EMAs more heavily.
    All above -> +0.8, all below -> -0.8, mixed -> proportional.
    """
    weights = {9: 0.30, 21: 0.25, 50: 0.20, 100: 0.15, 200: 0.10}
    total_weight = 0.0
    weighted_score = 0.0

    for period, ema_val in emas.items():
        if ema_val is None or math.isnan(ema_val):
            continue
        w = weights.get(period, 0.1)
        total_weight += w
        if close > ema_val:
            weighted_score += w
        elif close < ema_val:
            weighted_score -= w

    if total_weight == 0:
        return 0.0

    # Normalize to [-0.8, +0.8]
    return (weighted_score / total_weight) * 0.8


def _volume_to_score(obv_trend: str, volume_ratio: float) -> float:
    """Map OBV trend and volume ratio to sub-score.

    Bullish OBV + high volume ratio (>1.5) -> +0.6
    Bearish OBV + low volume -> -0.6
    Neutral otherwise.
    """
    score = 0.0

    # OBV trend component
    if obv_trend == "bullish":
        score += 0.3
    elif obv_trend == "bearish":
        score -= 0.3

    # Volume ratio component (high volume = stronger conviction in OBV direction)
    if volume_ratio > 2.0:
        vol_magnitude = 0.3
    elif volume_ratio > 1.5:
        vol_magnitude = 0.2
    elif volume_ratio > 1.0:
        vol_magnitude = 0.1
    else:
        vol_magnitude = 0.05  # Low volume still provides some directional info

    # Volume amplifies the OBV direction
    if obv_trend == "bullish":
        score += vol_magnitude
    elif obv_trend == "bearish":
        score -= vol_magnitude

    return max(-0.8, min(0.8, score))


# ---------------------------------------------------------------------------
# Indicator computation
# ---------------------------------------------------------------------------


def compute_technical_indicators(df: pd.DataFrame) -> dict[str, object]:
    """Compute all required technical indicators on a price DataFrame.

    DataFrame must have columns: open, high, low, close, volume.
    Returns dict of indicator name -> latest value, plus 'skipped' list.
    """
    results: dict[str, object] = {}
    skipped: list[str] = []
    n = len(df)

    # RSI dual period
    if n >= 15:
        rsi_14 = df.ta.rsi(length=14)  # type: ignore[attr-defined]
        val = rsi_14.iloc[-1] if rsi_14 is not None and not rsi_14.empty else None
        results["rsi_14"] = float(val) if val is not None and not math.isnan(float(val)) else None
    else:
        results["rsi_14"] = None
        skipped.append("rsi_14")

    if n >= 8:
        rsi_7 = df.ta.rsi(length=7)  # type: ignore[attr-defined]
        val = rsi_7.iloc[-1] if rsi_7 is not None and not rsi_7.empty else None
        results["rsi_7"] = float(val) if val is not None and not math.isnan(float(val)) else None
    else:
        results["rsi_7"] = None
        skipped.append("rsi_7")

    # MACD 12/26/9
    if n >= 27:
        macd = df.ta.macd(fast=12, slow=26, signal=9)  # type: ignore[attr-defined]
        if macd is not None and not macd.empty:
            results["macd_line"] = float(macd.iloc[-1, 0])
            results["macd_histogram"] = float(macd.iloc[-1, 1])
            results["macd_signal"] = float(macd.iloc[-1, 2])
        else:
            results["macd_line"] = None
            results["macd_histogram"] = None
            results["macd_signal"] = None
            skipped.append("macd")
    else:
        results["macd_line"] = None
        results["macd_histogram"] = None
        results["macd_signal"] = None
        skipped.append("macd")

    # Bollinger Bands (outer 2 sigma, inner 1 sigma)
    if n >= 21:
        bb_outer = df.ta.bbands(length=20, std=2)  # type: ignore[attr-defined]
        if bb_outer is not None and not bb_outer.empty:
            results["bb_lower_2"] = float(bb_outer.iloc[-1, 0])
            results["bb_mid"] = float(bb_outer.iloc[-1, 1])
            results["bb_upper_2"] = float(bb_outer.iloc[-1, 2])
        else:
            results["bb_lower_2"] = None
            results["bb_mid"] = None
            results["bb_upper_2"] = None
            skipped.append("bb_outer")

        bb_inner = df.ta.bbands(length=20, std=1)  # type: ignore[attr-defined]
        if bb_inner is not None and not bb_inner.empty:
            results["bb_lower_1"] = float(bb_inner.iloc[-1, 0])
            results["bb_upper_1"] = float(bb_inner.iloc[-1, 2])
        else:
            results["bb_lower_1"] = None
            results["bb_upper_1"] = None
            skipped.append("bb_inner")
    else:
        results["bb_lower_2"] = None
        results["bb_mid"] = None
        results["bb_upper_2"] = None
        results["bb_lower_1"] = None
        results["bb_upper_1"] = None
        skipped.append("bollinger")

    # EMA set
    for period in [9, 21, 50, 100, 200]:
        if n >= period:
            ema = df.ta.ema(length=period)  # type: ignore[attr-defined]
            val = ema.iloc[-1] if ema is not None and not ema.empty else None
            results[f"ema_{period}"] = (
                float(val) if val is not None and not math.isnan(float(val)) else None
            )
        else:
            results[f"ema_{period}"] = None
            skipped.append(f"ema_{period}")

    # OBV
    if n >= 2:
        obv = df.ta.obv()  # type: ignore[attr-defined]
        if obv is not None and not obv.empty:
            results["obv"] = float(obv.iloc[-1])
            # OBV trend: compare current vs 20-day SMA of OBV
            if n >= 20:
                obv_sma = obv.rolling(20).mean()
                if not math.isnan(float(obv_sma.iloc[-1])):
                    results["obv_trend"] = (
                        "bullish" if obv.iloc[-1] > obv_sma.iloc[-1] else "bearish"
                    )
                else:
                    results["obv_trend"] = "neutral"
            else:
                results["obv_trend"] = "neutral"
        else:
            results["obv"] = None
            results["obv_trend"] = "neutral"
            skipped.append("obv")
    else:
        results["obv"] = None
        results["obv_trend"] = "neutral"
        skipped.append("obv")

    # Volume vs 20-day SMA
    if n >= 20:
        vol_sma = df["volume"].rolling(20).mean()
        vol_sma_last = float(vol_sma.iloc[-1])
        if vol_sma_last > 0 and not math.isnan(vol_sma_last):
            results["volume_ratio"] = float(df["volume"].iloc[-1] / vol_sma_last)
        else:
            results["volume_ratio"] = 1.0
    else:
        results["volume_ratio"] = 1.0
        skipped.append("volume_ratio")

    results["skipped"] = skipped
    return results


# ---------------------------------------------------------------------------
# TechnicalEngine
# ---------------------------------------------------------------------------


class TechnicalEngine(BaseEngine):
    """Technical analysis engine using RSI, MACD, Bollinger Bands, EMA, OBV."""

    @property
    def category(self) -> str:
        return "technical"

    def analyze(
        self, asset_id: int, asset_symbol: str, df: pd.DataFrame
    ) -> Signal:
        """Run technical analysis on price data.

        Never raises -- returns score=0/confidence=0 on failure.
        """
        try:
            return self._analyze_impl(asset_id, asset_symbol, df)
        except Exception as exc:
            logger.warning(
                "technical_engine_error",
                asset_id=asset_id,
                asset_symbol=asset_symbol,
                error=str(exc),
            )
            return Signal(
                category="technical",
                score=0.0,
                confidence=0.0,
                reasoning=f"Technical analysis failed: {exc}",
                indicators={},
                data_quality={"trading_days": 0, "indicators_skipped": ["all"]},
            )

    def _analyze_impl(
        self, asset_id: int, asset_symbol: str, df: pd.DataFrame
    ) -> Signal:
        """Internal analysis implementation."""
        # Insufficient data guard
        if df.empty or len(df) < 5:
            return Signal(
                category="technical",
                score=0.0,
                confidence=0.0,
                reasoning="Insufficient data for technical analysis",
                indicators={},
                data_quality={
                    "trading_days": len(df) if not df.empty else 0,
                    "indicators_skipped": ["all"],
                },
            )

        # Compute all indicators
        ind = compute_technical_indicators(df)
        skipped: list[str] = ind.pop("skipped", [])  # type: ignore[assignment]

        # --- Map each indicator group to sub-score ---
        sub_scores: dict[str, float] = {}

        # RSI sub-score (average of RSI-14 and RSI-7)
        rsi_scores = []
        if ind.get("rsi_14") is not None:
            rsi_scores.append(_rsi_to_score(float(ind["rsi_14"])))
        if ind.get("rsi_7") is not None:
            rsi_scores.append(_rsi_to_score(float(ind["rsi_7"])))
        sub_scores["rsi"] = sum(rsi_scores) / len(rsi_scores) if rsi_scores else 0.0

        # MACD sub-score
        if (
            ind.get("macd_line") is not None
            and ind.get("macd_histogram") is not None
            and ind.get("macd_signal") is not None
        ):
            sub_scores["macd"] = _macd_to_score(
                float(ind["macd_histogram"]),
                float(ind["macd_line"]),
                float(ind["macd_signal"]),
            )
        else:
            sub_scores["macd"] = 0.0

        # Bollinger sub-score
        if (
            ind.get("bb_lower_2") is not None
            and ind.get("bb_upper_2") is not None
            and ind.get("bb_mid") is not None
        ):
            bb_lower_1 = ind.get("bb_lower_1") or ind["bb_lower_2"]
            bb_upper_1 = ind.get("bb_upper_1") or ind["bb_upper_2"]
            sub_scores["bollinger"] = _bollinger_to_score(
                close=float(df["close"].iloc[-1]),
                lower_2=float(ind["bb_lower_2"]),
                lower_1=float(bb_lower_1),
                upper_1=float(bb_upper_1),
                upper_2=float(ind["bb_upper_2"]),
                mid=float(ind["bb_mid"]),
            )
        else:
            sub_scores["bollinger"] = 0.0

        # EMA sub-score
        emas: dict[int, float | None] = {}
        for period in [9, 21, 50, 100, 200]:
            val = ind.get(f"ema_{period}")
            emas[period] = float(val) if val is not None else None
        sub_scores["ema"] = _ema_to_score(float(df["close"].iloc[-1]), emas)

        # Volume sub-score
        obv_trend = str(ind.get("obv_trend", "neutral"))
        vol_ratio = float(ind.get("volume_ratio", 1.0))
        sub_scores["volume"] = _volume_to_score(obv_trend, vol_ratio)

        # Overall trend: combine RSI direction + EMA alignment + MACD direction
        sub_scores["overall_trend"] = (
            sub_scores["rsi"] * 0.3
            + sub_scores["ema"] * 0.4
            + sub_scores["macd"] * 0.3
        )

        # --- Weighted average composite score ---
        weights = {
            "rsi": settings.weight_rsi,
            "macd": settings.weight_macd,
            "bollinger": settings.weight_bollinger,
            "ema": settings.weight_ema,
            "volume": settings.weight_volume,
            "overall_trend": settings.weight_overall_trend,
        }

        composite = sum(
            sub_scores[k] * weights[k] for k in weights
        )
        # Clamp to [-1.0, +1.0]
        composite = max(-1.0, min(1.0, composite))

        # --- Confidence calculation ---
        # Count indicators agreeing with composite sign
        sign = 1 if composite >= 0 else -1
        agreeing = sum(
            1
            for k, v in sub_scores.items()
            if k != "overall_trend" and ((v >= 0 and sign >= 0) or (v < 0 and sign < 0))
        )
        total_indicators = 5  # rsi, macd, bollinger, ema, volume

        agreement_ratio = agreeing / total_indicators if total_indicators > 0 else 0.5

        # Data quality penalty: 0.1 per skipped indicator (max 0.5)
        data_quality_penalty = min(len(skipped) * 0.1, 0.5)

        confidence = agreement_ratio * (1.0 - data_quality_penalty)
        confidence = max(0.0, min(1.0, confidence))

        # --- Build reasoning string ---
        reasoning_parts = []

        if ind.get("rsi_14") is not None:
            rsi_val = float(ind["rsi_14"])
            rsi_label = (
                "oversold" if rsi_val < 30 else "overbought" if rsi_val > 70 else "neutral"
            )
            reasoning_parts.append(f"RSI(14)={rsi_val:.1f} {rsi_label}")

        if ind.get("macd_histogram") is not None:
            hist_val = float(ind["macd_histogram"])
            macd_label = "bullish" if hist_val > 0 else "bearish"
            reasoning_parts.append(f"MACD histogram={hist_val:.4f} {macd_label}")

        if ind.get("bb_mid") is not None:
            close_val = float(df["close"].iloc[-1])
            mid_val = float(ind["bb_mid"])
            if close_val < mid_val:
                bb_pos = "below mid"
            else:
                bb_pos = "above mid"
            reasoning_parts.append(f"price at {bb_pos} BB")

        reasoning_parts.append(f"{agreeing}/{total_indicators} indicators agree")

        if composite > 0.1:
            bias = "Bullish"
        elif composite < -0.1:
            bias = "Bearish"
        else:
            bias = "Neutral"
        reasoning_parts.append(f"{bias} bias.")

        reasoning = ", ".join(reasoning_parts[:-1]) + ". " + reasoning_parts[-1] if len(reasoning_parts) > 1 else reasoning_parts[0] if reasoning_parts else "No indicators computed."

        # --- Data quality dict ---
        data_quality = {
            "trading_days": len(df),
            "indicators_skipped": skipped,
        }

        return Signal(
            category="technical",
            score=round(composite, 6),
            confidence=round(confidence, 4),
            reasoning=reasoning,
            indicators=ind,
            data_quality=data_quality,
        )
