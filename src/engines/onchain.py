"""OnChainEngine: TVL trends and exchange flow analysis for crypto assets."""

from __future__ import annotations

import pandas as pd
import structlog

from src.engines.base import BaseEngine, Signal

logger = structlog.get_logger(__name__)


class OnChainEngine(BaseEngine):
    """On-chain analysis engine using DeFiLlama TVL data.

    Scores crypto assets based on TVL trends and optional exchange flow data.
    Returns score=0/confidence=0 for stock assets or when no data available.
    """

    def __init__(self, onchain_data: dict | None = None) -> None:
        """Initialize with optional pre-fetched on-chain data.

        Args:
            onchain_data: Dict with keys tvl_current, tvl_7d_change, tvl_30d_change.
                Optionally: exchange_inflow, exchange_outflow.
                Pass None when data is unavailable.
        """
        self._data = onchain_data

    @property
    def category(self) -> str:
        """Return engine category."""
        return "onchain"

    @property
    def supports_stocks(self) -> bool:
        return False

    @property
    def supports_crypto(self) -> bool:
        return True

    def analyze(self, asset_id: int, asset_symbol: str, df: pd.DataFrame) -> Signal:
        """Run on-chain analysis. Never raises."""
        try:
            return self._analyze_impl(asset_id, asset_symbol, df)
        except Exception as exc:
            logger.warning(
                "onchain_engine_error",
                asset_id=asset_id,
                asset_symbol=asset_symbol,
                error=str(exc),
            )
            return Signal(
                category="onchain",
                score=0.0,
                confidence=0.0,
                reasoning=f"On-chain analysis failed: {exc}",
                indicators={},
                data_quality={"error": str(exc)},
            )

    def _analyze_impl(self, asset_id: int, asset_symbol: str, df: pd.DataFrame) -> Signal:
        """Internal analysis implementation."""
        if not self._data:
            return Signal(
                category="onchain",
                score=0.0,
                confidence=0.0,
                reasoning="No on-chain data available",
                indicators={},
                data_quality={"available_metrics": 0},
            )

        data = self._data

        # --- TVL scoring ---
        tvl_7d = data.get("tvl_7d_change", 0.0)
        tvl_30d = data.get("tvl_30d_change", 0.0)

        # Ensure numeric
        tvl_7d = float(tvl_7d) if tvl_7d is not None else 0.0
        tvl_30d = float(tvl_30d) if tvl_30d is not None else 0.0

        tvl_score = 0.0
        if tvl_7d > 0.10:
            tvl_score = 0.7
        elif tvl_7d > 0.05:
            tvl_score = 0.4
        elif tvl_7d < -0.10:
            tvl_score = -0.7
        elif tvl_7d < -0.05:
            tvl_score = -0.4

        # 30d confirming signal
        if tvl_30d != 0.0:
            same_direction = (tvl_7d > 0 and tvl_30d > 0) or (tvl_7d < 0 and tvl_30d < 0)
            if same_direction:
                tvl_score += 0.2 if tvl_7d > 0 else -0.2
            else:
                tvl_score -= 0.1 if tvl_7d > 0 else 0.1

        # --- Exchange flow scoring ---
        exchange_outflow = data.get("exchange_outflow")
        exchange_inflow = data.get("exchange_inflow")
        has_flow_data = exchange_outflow is not None and exchange_inflow is not None

        flow_score = 0.0
        if has_flow_data:
            outflow = float(exchange_outflow)  # type: ignore[arg-type]
            inflow = float(exchange_inflow)  # type: ignore[arg-type]
            if outflow > inflow:
                flow_score = 0.3  # Net outflow = accumulation = bullish
            else:
                flow_score = -0.3  # Net inflow = sell pressure = bearish

        # --- Final score ---
        if has_flow_data:
            score = tvl_score * 0.6 + flow_score * 0.4
        else:
            score = tvl_score

        score = max(-1.0, min(1.0, score))

        # --- Confidence ---
        confidence = 0.3
        if has_flow_data:
            confidence += 0.2
        same_7d_30d = (tvl_7d > 0 and tvl_30d > 0) or (tvl_7d < 0 and tvl_30d < 0)
        if same_7d_30d:
            confidence += 0.1
        confidence = max(0.0, min(1.0, confidence))

        # --- Reasoning ---
        parts = []
        if tvl_7d != 0:
            direction = "rising" if tvl_7d > 0 else "falling"
            parts.append(f"TVL {direction} {abs(tvl_7d)*100:.1f}% over 7d")
        if tvl_30d != 0:
            direction = "rising" if tvl_30d > 0 else "falling"
            parts.append(f"{abs(tvl_30d)*100:.1f}% over 30d")
        if has_flow_data:
            net = "outflow" if flow_score > 0 else "inflow"
            parts.append(f"net exchange {net}")
        reasoning = ". ".join(parts) if parts else "TVL data available but neutral"

        indicators: dict[str, object] = {
            "tvl_current": data.get("tvl_current"),
            "tvl_7d_change": tvl_7d,
            "tvl_30d_change": tvl_30d,
            "exchange_net_flow": (float(exchange_outflow or 0) - float(exchange_inflow or 0)) if has_flow_data else None,  # type: ignore[arg-type]
            "source": data.get("source", "defillama"),
        }

        data_quality: dict[str, object] = {
            "has_tvl": tvl_7d != 0.0 or tvl_30d != 0.0,
            "has_exchange_flow": has_flow_data,
        }

        return Signal(
            category="onchain",
            score=round(score, 6),
            confidence=round(confidence, 4),
            reasoning=reasoning,
            indicators=indicators,
            data_quality=data_quality,
        )
