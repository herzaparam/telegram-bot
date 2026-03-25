"""GameTheoryEngine: Stub for game theory / order book analysis."""

from __future__ import annotations

import pandas as pd

from src.engines.base import BaseEngine, Signal


class GameTheoryEngine(BaseEngine):
    """Game theory analysis engine (stub).

    Real-time order book data is not available in the daily cadence pipeline.
    Returns score=0/confidence=0 with documented reasoning until
    Binance WebSocket integration for real-time order book data is added.
    """

    @property
    def category(self) -> str:
        """Return the engine category."""
        return "game_theory"

    def analyze(self, asset_id: int, asset_symbol: str, df: pd.DataFrame) -> Signal:
        """Return stub signal — order book data not available.

        Never raises.
        """
        return Signal(
            category="game_theory",
            score=0.0,
            confidence=0.0,
            reasoning="Real-time order book data not available in daily cadence pipeline",
            indicators={},
            data_quality={
                "stub": True,
                "todo": "Binance WebSocket for real-time order book",
            },
        )
