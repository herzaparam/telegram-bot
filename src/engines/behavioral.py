"""BehavioralEngine: Volume anomalies, price gaps, and price/volume divergence."""

from __future__ import annotations

import numpy as np
import pandas as pd
import structlog

from src.engines.base import BaseEngine, Signal

logger = structlog.get_logger(__name__)

MIN_DAYS = 20


class BehavioralEngine(BaseEngine):
    """Behavioral analysis engine detecting volume spikes, gaps, and divergence.

    Analyzes:
    - Volume anomaly detection (Z-score > 2 std dev)
    - Price gap detection (open vs prior close > 3%)
    - Price/volume divergence (rising price on falling volume or vice versa)
    """

    @property
    def category(self) -> str:
        """Return the engine category."""
        return "behavioral"

    def analyze(self, asset_id: int, asset_symbol: str, df: pd.DataFrame) -> Signal:
        """Run behavioral analysis on price data.

        Never raises -- returns score=0/confidence=0 on failure.
        """
        try:
            return self._analyze_impl(asset_id, asset_symbol, df)
        except Exception as exc:
            logger.warning(
                "behavioral_engine_error",
                asset_id=asset_id,
                asset_symbol=asset_symbol,
                error=str(exc),
            )
            return Signal(
                category="behavioral",
                score=0.0,
                confidence=0.0,
                reasoning=f"Behavioral analysis failed: {exc}",
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
                category="behavioral",
                score=0.0,
                confidence=0.0,
                reasoning=f"Insufficient data for behavioral analysis (need >= {MIN_DAYS} days, got {len(df)})",
                indicators={},
                data_quality={"trading_days": len(df), "sufficient": False},
            )

        volume = df["volume"].values.astype(float)
        close = df["close"].values.astype(float)
        open_ = df["open"].values.astype(float)

        # --- 1. Volume anomaly detection ---
        vol_mean_20 = float(np.mean(volume[-20:]))
        vol_std_20 = float(np.std(volume[-20:], ddof=1))
        if vol_std_20 > 0:
            volume_z_score = float((volume[-1] - vol_mean_20) / vol_std_20)
        else:
            volume_z_score = 0.0
        is_spike = abs(volume_z_score) > 2.0

        # --- 2. Price gap detection ---
        gap_pct = 0.0
        is_gap = False
        if len(df) >= 2 and close[-2] != 0:
            gap_pct = float((open_[-1] - close[-2]) / close[-2])
            is_gap = abs(gap_pct) > 0.03

        # --- 3. Price/volume divergence ---
        divergence = False
        price_change_5d = 0.0
        vol_change_5d = 0.0
        if len(df) >= 10:
            price_change_5d = float(close[-1] / close[-6] - 1)
            vol_recent = float(np.mean(volume[-5:]))
            vol_prior = float(np.mean(volume[-10:-5]))
            if vol_prior > 0:
                vol_change_5d = float(vol_recent / vol_prior - 1)
            # Rising price but falling volume, or falling price but rising volume
            if price_change_5d > 0.01 and vol_change_5d < -0.20:
                divergence = True
            elif price_change_5d < -0.01 and vol_change_5d > 0.20:
                divergence = True

        # --- 4. Scoring ---
        # Volume spike score: z_score direction with price context
        if is_spike:
            # Positive z-score + positive recent price = bullish; negative = bearish
            price_direction = 1.0 if close[-1] >= close[-2] else -1.0
            volume_spike_score = float(
                np.clip(volume_z_score * 0.3 * price_direction, -1.0, 1.0)
            )
        else:
            volume_spike_score = float(np.clip(volume_z_score * 0.1, -0.3, 0.3))

        # Gap score
        gap_score = float(np.clip(gap_pct * 5.0, -1.0, 1.0))

        # Divergence score (bearish signal when detected)
        divergence_score = -0.4 if divergence else 0.0

        # Final composite score
        final_score = float(
            np.clip(
                0.4 * volume_spike_score + 0.3 * gap_score + 0.3 * divergence_score,
                -1.0,
                1.0,
            )
        )

        # Confidence: base + bonuses
        confidence = 0.3
        if is_spike:
            confidence += 0.2
        if is_gap:
            confidence += 0.1
        if divergence:
            confidence += 0.1
        confidence = min(confidence, 0.7)

        # --- 5. Build reasoning ---
        parts = []
        if is_spike:
            parts.append(f"Volume spike detected (z={volume_z_score:.2f})")
        if is_gap:
            parts.append(f"Price gap {gap_pct:.1%}")
        if divergence:
            parts.append(
                f"Price/volume divergence (price {price_change_5d:+.1%}, vol {vol_change_5d:+.1%})"
            )
        if not parts:
            parts.append("No significant behavioral anomalies detected")

        reasoning = "; ".join(parts)

        # --- 6. Indicators ---
        indicators: dict[str, object] = {
            "volume_z_score": round(volume_z_score, 4),
            "is_spike": is_spike,
            "gap_pct": round(gap_pct, 6),
            "is_gap": is_gap,
            "divergence": divergence,
            "price_change_5d": round(price_change_5d, 6),
            "vol_change_5d": round(vol_change_5d, 6),
        }

        return Signal(
            category="behavioral",
            score=round(final_score, 6),
            confidence=round(confidence, 4),
            reasoning=reasoning,
            indicators=indicators,
            data_quality={
                "trading_days": len(df),
                "sufficient": True,
            },
        )
