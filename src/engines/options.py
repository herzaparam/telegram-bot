"""OptionsEngine: Stub for options flow analysis (not yet available for IDX market)."""

from __future__ import annotations

import pandas as pd

from src.engines.base import BaseEngine, Signal


class OptionsEngine(BaseEngine):
    """Options flow analysis engine (stub).

    Options flow data is not yet available for the IDX market.
    Returns score=0/confidence=0 with documented reasoning until
    Deribit integration for crypto options or IDX options data becomes available.
    """

    @property
    def category(self) -> str:
        """Return the engine category."""
        return "options"

    @property
    def supports_crypto(self) -> bool:
        """Crypto options not yet supported (future Deribit integration)."""
        return False

    def analyze(self, asset_id: int, asset_symbol: str, df: pd.DataFrame) -> Signal:
        """Return stub signal — options data not available.

        Never raises.
        """
        return Signal(
            category="options",
            score=0.0,
            confidence=0.0,
            reasoning="Options flow data not available for IDX market",
            indicators={},
            data_quality={
                "stub": True,
                "todo": "Deribit for crypto options, IDX options when available",
            },
        )
