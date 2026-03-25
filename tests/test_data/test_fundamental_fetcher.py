"""Tests for fundamental data fetcher (yfinance .info wrapper)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


def _make_stock_asset(asset_id: int = 1) -> MagicMock:
    """Create a mock stock Asset."""
    asset = MagicMock()
    asset.id = asset_id
    asset.symbol = "BBCA"
    asset.asset_type = "stock"
    asset.yfinance_symbol = "BBCA.JK"
    return asset


def _make_crypto_asset(asset_id: int = 2) -> MagicMock:
    """Create a mock crypto Asset."""
    asset = MagicMock()
    asset.id = asset_id
    asset.symbol = "BTC"
    asset.asset_type = "crypto"
    asset.yfinance_symbol = None
    return asset


def _make_fundamental_row(asset_id: int = 1, days_old: int = 10) -> MagicMock:
    """Create a mock StockFundamental row."""
    row = MagicMock()
    row.asset_id = asset_id
    row.fetched_at = datetime.now(UTC) - timedelta(days=days_old)
    return row


class TestFetchFundamentals:
    """Tests for fetch_fundamentals() function."""

    @pytest.mark.asyncio
    async def test_fetch_fundamentals_stock_upserts_row(self) -> None:
        """fetch_fundamentals() for stock asset calls yfinance and upserts StockFundamental row."""
        asset = _make_stock_asset()
        mock_session = AsyncMock()

        # No existing row (first fetch)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        yfinance_info = {
            "trailingPE": 15.5,
            "forwardPE": 12.0,
            "priceToBook": 2.3,
            "returnOnEquity": 0.18,
            "revenueGrowth": 0.10,
            "dividendYield": 0.04,
            "debtToEquity": 45.0,
        }

        with patch(
            "src.data.fundamental_fetcher._fetch_yfinance_info",
            return_value={
                "trailing_pe": 15.5,
                "forward_pe": 12.0,
                "price_to_book": 2.3,
                "return_on_equity": 0.18,
                "revenue_growth": 0.10,
                "dividend_yield": 0.04,
                "debt_to_equity": 45.0,
            },
        ):
            from src.data.fundamental_fetcher import fetch_fundamentals

            await fetch_fundamentals(mock_session, asset)

        # Session should have had execute called for upsert
        assert mock_session.execute.called
        assert mock_session.commit.called

    @pytest.mark.asyncio
    async def test_fetch_fundamentals_crypto_returns_immediately(self) -> None:
        """fetch_fundamentals() for crypto asset returns immediately without any DB calls."""
        asset = _make_crypto_asset()
        mock_session = AsyncMock()

        from src.data.fundamental_fetcher import fetch_fundamentals

        await fetch_fundamentals(mock_session, asset)

        # No DB operations for crypto
        mock_session.execute.assert_not_called()

    @pytest.mark.asyncio
    async def test_fetch_fundamentals_skips_when_cache_fresh(self) -> None:
        """fetch_fundamentals() skips yfinance when existing data is less than 7 days old."""
        asset = _make_stock_asset()
        mock_session = AsyncMock()

        # Existing row fetched 3 days ago (fresh)
        fresh_row = _make_fundamental_row(days_old=3)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = fresh_row
        mock_session.execute.return_value = mock_result

        with patch(
            "src.data.fundamental_fetcher._fetch_yfinance_info",
        ) as mock_fetch:
            from src.data.fundamental_fetcher import fetch_fundamentals

            await fetch_fundamentals(mock_session, asset)

            # yfinance should NOT be called
            mock_fetch.assert_not_called()

    @pytest.mark.asyncio
    async def test_fetch_fundamentals_handles_none_fields(self) -> None:
        """fetch_fundamentals() handles yfinance returning None for some fields gracefully."""
        asset = _make_stock_asset()
        mock_session = AsyncMock()

        # No existing row
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        # yfinance returns partial info (some fields None)
        with patch(
            "src.data.fundamental_fetcher._fetch_yfinance_info",
            return_value={
                "trailing_pe": None,
                "forward_pe": None,
                "price_to_book": 2.3,
                "return_on_equity": None,
                "revenue_growth": 0.10,
                "dividend_yield": None,
                "debt_to_equity": None,
            },
        ):
            from src.data.fundamental_fetcher import fetch_fundamentals

            # Should not raise
            await fetch_fundamentals(mock_session, asset)

        assert mock_session.execute.called

    @pytest.mark.asyncio
    async def test_fetch_fundamentals_handles_yfinance_exception(self) -> None:
        """fetch_fundamentals() catches yfinance exceptions and logs warning."""
        asset = _make_stock_asset()
        mock_session = AsyncMock()

        # No existing row
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        # yfinance returns empty dict (signals an exception was caught internally)
        with patch(
            "src.data.fundamental_fetcher._fetch_yfinance_info",
            return_value={},
        ):
            from src.data.fundamental_fetcher import fetch_fundamentals

            # Should not raise - degrades gracefully
            await fetch_fundamentals(mock_session, asset)

        # No commit when info is empty
        mock_session.commit.assert_not_called()
