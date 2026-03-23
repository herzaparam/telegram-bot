"""Base fetcher contract and OHLCV row dataclass."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date, datetime


@dataclass
class OHLCVRow:
    """A single OHLCV candle row ready for database insertion."""

    time: datetime
    asset_id: int
    open: float
    high: float
    low: float
    close: float
    volume: float
    source: str


class BaseFetcher(ABC):
    """Abstract base class for all market data fetchers."""

    @property
    @abstractmethod
    def source_name(self) -> str:
        """Return the canonical name of this data source (e.g. 'yfinance', 'ccxt')."""
        ...

    @abstractmethod
    async def fetch(
        self, asset_id: int, symbol: str, start: date, end: date
    ) -> list[OHLCVRow]:
        """Fetch OHLCV data for a single asset over a date range.

        Args:
            asset_id: Database ID of the asset.
            symbol: Exchange-specific symbol (e.g. 'BBCA.JK', 'BTC/USDT').
            start: Start date (inclusive).
            end: End date (inclusive).

        Returns:
            List of validated OHLCVRow instances.
        """
        ...
