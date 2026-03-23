"""IDX stock fetcher using yfinance.

Wraps synchronous yfinance.download in an executor to avoid blocking
the event loop. Includes tenacity retry for transient network failures.
"""

from __future__ import annotations

import asyncio
import functools
from datetime import UTC, date, timedelta
from typing import Any

import structlog
import yfinance as yf
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from src.data.base import BaseFetcher, OHLCVRow
from src.data.validation import validate_rows

logger = structlog.get_logger(__name__)


def _download_with_retry(symbol: str, start_str: str, end_str: str) -> Any:
    """Synchronous yfinance download wrapped with tenacity retry.

    Retries up to 3 times with exponential backoff on transient errors.
    """
    return _download_inner(symbol, start_str, end_str)


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    retry=retry_if_exception_type((ConnectionError, TimeoutError, Exception)),
    reraise=True,
)
def _download_inner(symbol: str, start_str: str, end_str: str) -> Any:
    """The actual yfinance download call, decorated with retry."""
    return yf.download(
        tickers=symbol,
        start=start_str,
        end=end_str,
        interval="1d",
        progress=False,
        auto_adjust=True,
    )


class IDXStockFetcher(BaseFetcher):
    """Fetches IDX stock OHLCV data via yfinance."""

    def __init__(self) -> None:
        self._log = logger.bind(component="idx_fetcher")

    @property
    def source_name(self) -> str:
        return "yfinance"

    async def fetch(
        self, asset_id: int, symbol: str, start: date, end: date
    ) -> list[OHLCVRow]:
        """Fetch daily OHLCV data from yfinance for a .JK ticker.

        Args:
            asset_id: Database ID of the asset.
            symbol: yfinance-compatible symbol (e.g. 'BBCA.JK').
            start: Start date (inclusive).
            end: End date (inclusive). +1 day added internally for yfinance exclusion.

        Returns:
            List of validated OHLCVRow instances with source='yfinance'.
        """
        # yfinance end date is EXCLUSIVE, so add 1 day
        end_exclusive = end + timedelta(days=1)
        start_str = start.isoformat()
        end_str = end_exclusive.isoformat()

        self._log.info(
            "fetching_idx_stock",
            symbol=symbol,
            start=start_str,
            end=end_str,
        )

        loop = asyncio.get_event_loop()
        df = await loop.run_in_executor(
            None,
            functools.partial(_download_with_retry, symbol, start_str, end_str),
        )

        if df is None or df.empty:
            self._log.warning("empty_dataframe", symbol=symbol)
            return []

        rows: list[OHLCVRow] = []
        for idx, row_data in df.iterrows():
            # Handle both regular and MultiIndex columns
            try:
                dt = idx.to_pydatetime()
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=UTC)
            except Exception:
                continue

            try:
                ohlcv = OHLCVRow(
                    time=dt,
                    asset_id=asset_id,
                    open=float(row_data["Open"]),
                    high=float(row_data["High"]),
                    low=float(row_data["Low"]),
                    close=float(row_data["Close"]),
                    volume=float(row_data["Volume"]),
                    source="yfinance",
                )
                rows.append(ohlcv)
            except (KeyError, ValueError, TypeError) as exc:
                self._log.warning("row_conversion_error", symbol=symbol, error=str(exc))
                continue

        # Validate and return only valid rows
        result = validate_rows(rows, asset_symbol=symbol)

        self._log.info(
            "fetch_complete",
            symbol=symbol,
            total_rows=len(rows),
            valid_rows=len(result.valid),
            rejected_rows=len(result.rejected),
        )

        return result.valid
