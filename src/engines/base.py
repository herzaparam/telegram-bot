"""Base engine contract and Signal dataclass for analysis engines."""

from abc import ABC, abstractmethod
from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class Signal:
    """Output from an analysis engine.

    Attributes:
        category: Engine category (e.g., "technical", "quantitative").
        score: Signal strength from -1.0 (strong sell) to +1.0 (strong buy).
        confidence: Confidence level from 0.0 to 1.0.
        reasoning: Human-readable explanation of the signal.
        indicators: Final computed indicator values (e.g., {"rsi_14": 28}).
        data_quality: Data quality metadata (sources, skipped indicators, trading days).
    """

    category: str
    score: float
    confidence: float
    reasoning: str
    indicators: dict  # type: ignore[type-arg]
    data_quality: dict  # type: ignore[type-arg]


class BaseEngine(ABC):
    """Abstract base class for all analysis engines.

    Subclasses must implement ``analyze()`` and ``category``.
    ``analyze()`` is synchronous (CPU-bound work) and must never raise.
    """

    @abstractmethod
    def analyze(self, asset_id: int, asset_symbol: str, df: pd.DataFrame) -> Signal:
        """Run analysis on price data.

        Args:
            asset_id: Database ID of the asset.
            asset_symbol: Human-readable symbol (e.g., "BBCA", "BTC").
            df: DataFrame with columns open, high, low, close, volume.

        Returns:
            A Signal with score, confidence, and reasoning.
        """
        ...

    @property
    @abstractmethod
    def category(self) -> str:
        """Return the engine category (e.g., 'technical', 'quantitative')."""
        ...

    @property
    def supports_stocks(self) -> bool:
        """Whether this engine supports stock assets. Default True."""
        return True

    @property
    def supports_crypto(self) -> bool:
        """Whether this engine supports crypto assets. Default True."""
        return True
