"""NetworkEngine: Cross-asset correlation analysis and regime change detection."""

from __future__ import annotations

import numpy as np
import pandas as pd
import structlog

from src.engines.base import BaseEngine, Signal

logger = structlog.get_logger(__name__)


class NetworkEngine(BaseEngine):
    """Network analysis engine using pre-computed cross-asset correlations.

    Scores based on average correlation levels:
    - High correlation (>0.7): bearish (herd behavior, contagion risk)
    - Low correlation (<0.3): bullish (diversified, independent signals)
    - Regime changes (large correlation shifts) strengthen signals.

    Constructor accepts correlation_data dict pre-computed in analyze_stage.
    """

    def __init__(
        self,
        correlation_data: dict[str, float] | None = None,
    ) -> None:
        """Initialize with optional pre-computed correlation data.

        Args:
            correlation_data: Dict with keys: avg_correlation, max_correlation,
                correlation_change_30d, num_assets. Pass None when unavailable.
        """
        self._correlations = correlation_data

    @property
    def category(self) -> str:
        """Return the engine category."""
        return "network"

    def analyze(self, asset_id: int, asset_symbol: str, df: pd.DataFrame) -> Signal:
        """Run network correlation analysis.

        Never raises -- returns score=0/confidence=0 on failure.
        """
        try:
            return self._analyze_impl(asset_id, asset_symbol, df)
        except Exception as exc:
            logger.warning(
                "network_engine_error",
                asset_id=asset_id,
                asset_symbol=asset_symbol,
                error=str(exc),
            )
            return Signal(
                category="network",
                score=0.0,
                confidence=0.0,
                reasoning=f"Network analysis failed: {exc}",
                indicators={},
                data_quality={"error": str(exc)},
            )

    def _analyze_impl(
        self, asset_id: int, asset_symbol: str, df: pd.DataFrame
    ) -> Signal:
        """Internal analysis implementation."""
        # Guard: no correlation data
        if not self._correlations:
            return Signal(
                category="network",
                score=0.0,
                confidence=0.0,
                reasoning="No correlation data available",
                indicators={},
                data_quality={"correlation_data": False},
            )

        avg_corr = float(self._correlations.get("avg_correlation", 0.5))
        max_corr = float(self._correlations.get("max_correlation", 0.5))
        corr_change = float(self._correlations.get("correlation_change_30d", 0.0))
        num_assets = int(self._correlations.get("num_assets", 0))

        # --- Scoring ---
        if avg_corr > 0.7:
            # High correlation = bearish (herd, contagion risk)
            score = -(avg_corr - 0.5) * 2.0
        elif avg_corr < 0.3:
            # Low correlation = bullish (diversified)
            score = (0.5 - avg_corr) * 1.5
        else:
            # Neutral zone: linear interpolation toward 0
            score = (0.5 - avg_corr) * 0.5

        # Regime change amplifier
        if abs(corr_change) > 0.15:
            score_sign = -1.0 if score < 0 else 1.0
            score = score + score_sign * 0.2

        # Clamp score
        score = float(np.clip(score, -1.0, 1.0))

        # --- Confidence ---
        confidence = 0.3 + 0.1 * min(num_assets / 10.0, 1.0)
        confidence = min(confidence, 0.6)

        # --- Reasoning ---
        parts = []
        if avg_corr > 0.7:
            parts.append(f"High avg correlation ({avg_corr:.2f}) suggests contagion risk")
        elif avg_corr < 0.3:
            parts.append(f"Low avg correlation ({avg_corr:.2f}) indicates diversification")
        else:
            parts.append(f"Moderate avg correlation ({avg_corr:.2f})")

        if abs(corr_change) > 0.15:
            direction = "increasing" if corr_change > 0 else "decreasing"
            parts.append(f"Regime change detected ({direction} by {abs(corr_change):.2f})")

        reasoning = "; ".join(parts)

        # --- Indicators ---
        indicators: dict[str, object] = {
            "avg_correlation": round(avg_corr, 4),
            "max_correlation": round(max_corr, 4),
            "correlation_change_30d": round(corr_change, 4),
            "num_assets": num_assets,
        }

        return Signal(
            category="network",
            score=round(score, 6),
            confidence=round(confidence, 4),
            reasoning=reasoning,
            indicators=indicators,
            data_quality={
                "correlation_data": True,
                "num_assets": num_assets,
            },
        )
