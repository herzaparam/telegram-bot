"""Tests for IDX stock fetcher (yfinance wrapper)."""

from __future__ import annotations

import asyncio
from datetime import date, datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pandas as pd
import pytest

from tenacity import wait_none

from src.data.base import OHLCVRow
from src.data.idx_stocks import IDXStockFetcher


class TestIDXStockFetcher:
    """IDXStockFetcher unit tests with mocked yfinance."""

    def setup_method(self) -> None:
        self.fetcher = IDXStockFetcher()

    def test_source_name(self) -> None:
        assert self.fetcher.source_name == "yfinance"

    @pytest.mark.asyncio
    async def test_fetch_returns_ohlcv_rows(self, mock_yfinance_df: pd.DataFrame) -> None:
        """fetch() returns list of OHLCVRow with source='yfinance'."""
        with patch("src.data.idx_stocks.yf.download", return_value=mock_yfinance_df):
            rows = await self.fetcher.fetch(
                asset_id=1,
                symbol="BBCA.JK",
                start=date(2026, 3, 16),
                end=date(2026, 3, 20),
            )

        assert len(rows) == 5
        assert all(isinstance(r, OHLCVRow) for r in rows)
        assert all(r.source == "yfinance" for r in rows)
        assert all(r.asset_id == 1 for r in rows)

    @pytest.mark.asyncio
    async def test_fetch_empty_dataframe_returns_empty_list(self) -> None:
        """fetch() with empty DataFrame returns []."""
        empty_df = pd.DataFrame()
        with patch("src.data.idx_stocks.yf.download", return_value=empty_df):
            rows = await self.fetcher.fetch(
                asset_id=1,
                symbol="BBCA.JK",
                start=date(2026, 3, 16),
                end=date(2026, 3, 20),
            )

        assert rows == []

    @pytest.mark.asyncio
    async def test_fetch_adds_one_day_to_end_date(self, mock_yfinance_df: pd.DataFrame) -> None:
        """fetch() adds timedelta(days=1) to end date for yfinance exclusion."""
        with patch("src.data.idx_stocks.yf.download", return_value=mock_yfinance_df) as mock_dl:
            await self.fetcher.fetch(
                asset_id=1,
                symbol="BBCA.JK",
                start=date(2026, 3, 16),
                end=date(2026, 3, 20),
            )

        # yfinance end date should be 2026-03-21 (exclusive)
        call_kwargs = mock_dl.call_args
        assert call_kwargs is not None
        end_arg = call_kwargs[1].get("end") or call_kwargs[0][2] if len(call_kwargs[0]) > 2 else call_kwargs[1]["end"]
        assert end_arg == "2026-03-21"

    @pytest.mark.asyncio
    async def test_fetch_runs_in_executor(self, mock_yfinance_df: pd.DataFrame) -> None:
        """fetch() uses run_in_executor (source code contains it)."""
        import inspect

        from src.data import idx_stocks

        source = inspect.getsource(idx_stocks.IDXStockFetcher.fetch)
        assert "run_in_executor" in source

    @pytest.mark.asyncio
    async def test_fetch_retries_on_failure(self, mock_yfinance_df: pd.DataFrame) -> None:
        """fetch() retries 3x on failure with tenacity."""
        from src.data.idx_stocks import _download_inner

        call_count = 0

        def flaky_download(*args: object, **kwargs: object) -> pd.DataFrame:
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError("Network error")
            return mock_yfinance_df

        with patch("src.data.idx_stocks.yf.download", side_effect=flaky_download):
            # Patch tenacity wait to avoid real delays in tests
            original_wait = _download_inner.retry.wait
            _download_inner.retry.wait = wait_none()
            try:
                rows = await self.fetcher.fetch(
                    asset_id=1,
                    symbol="BBCA.JK",
                    start=date(2026, 3, 16),
                    end=date(2026, 3, 20),
                )
            finally:
                _download_inner.retry.wait = original_wait

        assert call_count == 3
        assert len(rows) == 5
