"""Tests for extended analyze_stage with 6 engines and store-backed data loading.

TDD tests for Phase 08-04 Task 1.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pandas as pd
import pytest

from src.db.models import Asset


@pytest.fixture()
def mock_stock_asset() -> Asset:
    """A mock stock Asset object."""
    asset = MagicMock(spec=Asset)
    asset.id = 1
    asset.symbol = "BBCA"
    asset.asset_type = "stock"
    return asset


@pytest.fixture()
def mock_crypto_asset() -> Asset:
    """A mock crypto Asset object."""
    asset = MagicMock(spec=Asset)
    asset.id = 2
    asset.symbol = "BTC"
    asset.asset_type = "crypto"
    return asset


@pytest.fixture()
def sample_df() -> pd.DataFrame:
    """A small but valid price DataFrame."""
    return pd.DataFrame(
        {
            "open": [100.0] * 60,
            "high": [105.0] * 60,
            "low": [95.0] * 60,
            "close": [102.0] * 60,
            "volume": [1000.0] * 60,
        },
        index=pd.date_range("2026-01-01", periods=60, freq="B", tz="UTC"),
    )


class TestGetEnginesForAssetExtended:
    """Test that _get_engines_for_asset returns 6 engines when context provided."""

    def test_stock_gets_six_engines_with_context(self, mock_stock_asset):
        """After Task 1: _get_engines_for_asset returns 6 engine instances for stock."""
        from src.data.analyze import _get_engines_for_asset

        engines = _get_engines_for_asset(
            mock_stock_asset,
            fundamentals={"trailing_pe": 10.0},
            macro_data={"fed_funds_rate": 5.25},
            sentiment_data=None,
            news_events=[],
        )
        categories = [e.category for e in engines]
        assert "technical" in categories
        assert "quantitative" in categories
        assert "fundamental" in categories
        assert "macro" in categories
        assert "sentiment" in categories
        assert "event" in categories

    def test_stock_passes_fundamentals_to_fundamental_engine(self, mock_stock_asset):
        """FundamentalEngine receives fundamentals data."""
        from src.data.analyze import _get_engines_for_asset
        from src.engines.fundamental import FundamentalEngine

        fundamentals = {"trailing_pe": 10.0, "price_to_book": 1.5}
        engines = _get_engines_for_asset(
            mock_stock_asset,
            fundamentals=fundamentals,
            macro_data=None,
            sentiment_data=None,
            news_events=None,
        )
        fund_engines = [e for e in engines if isinstance(e, FundamentalEngine)]
        assert len(fund_engines) == 1
        # FundamentalEngine should have the fundamentals data
        assert fund_engines[0]._fundamentals == fundamentals

    def test_stock_passes_macro_to_macro_engine(self, mock_stock_asset):
        """MacroEngine receives macro data."""
        from src.data.analyze import _get_engines_for_asset
        from src.engines.macro import MacroEngine

        macro_data = {"fed_funds_rate": 5.25, "cpi": 3.2}
        engines = _get_engines_for_asset(
            mock_stock_asset,
            fundamentals=None,
            macro_data=macro_data,
            sentiment_data=None,
            news_events=None,
        )
        macro_engines = [e for e in engines if isinstance(e, MacroEngine)]
        assert len(macro_engines) == 1
        assert macro_engines[0]._macro_data == macro_data

    def test_crypto_gets_all_applicable_engines(self, mock_crypto_asset):
        """Crypto asset gets all applicable engines."""
        from src.data.analyze import _get_engines_for_asset

        engines = _get_engines_for_asset(
            mock_crypto_asset,
            fundamentals=None,
            macro_data={"fed_funds_rate": 5.25},
            sentiment_data=None,
            news_events=[],
        )
        categories = [e.category for e in engines]
        # Crypto gets technical, quantitative, macro, sentiment, event
        # but NOT fundamental (stock-only)
        assert "technical" in categories
        assert "quantitative" in categories
        assert "macro" in categories


class TestAnalyzeStageStoreBacked:
    """Test analyze_stage loads store-backed data and passes to 6 engines."""

    @pytest.mark.asyncio
    async def test_analyze_stage_stores_signals_from_seven_engines(
        self, mock_stock_asset, sample_df
    ):
        """analyze_stage with mocked DB data creates 7 engine signals for stock."""
        from src.data.analyze import analyze_stage

        session = AsyncMock()

        with (
            patch("src.data.analyze._load_price_dataframe", return_value=sample_df),
            patch("src.data.analyze._load_fundamentals", new_callable=AsyncMock, return_value={"trailing_pe": 10.0}),
            patch("src.data.analyze._load_latest_macro", new_callable=AsyncMock, return_value={"fed_funds_rate": 5.25}),
            patch("src.data.analyze._load_recent_news", new_callable=AsyncMock, return_value=[]),
            patch("src.data.analyze._load_financial_data", new_callable=AsyncMock, return_value=None),
            patch("src.data.analyze._load_peer_data", new_callable=AsyncMock, return_value=None),
            patch("src.data.analyze.signal_repo") as mock_repo,
        ):
            mock_repo.upsert_signals = AsyncMock(return_value=7)
            await analyze_stage(session, mock_stock_asset)
            mock_repo.upsert_signals.assert_called_once()
            signals = mock_repo.upsert_signals.call_args[0][3]
            # Stock asset should have 7 engines (technical, quantitative, fundamental, macro, sentiment, event, valuation)
            assert len(signals) == 7

    @pytest.mark.asyncio
    async def test_load_fundamentals_returns_dict(self):
        """_load_fundamentals returns correct dict from StockFundamental row."""
        from src.data.analyze import _load_fundamentals
        from src.db.models import StockFundamental

        mock_row = MagicMock(spec=StockFundamental)
        mock_row.trailing_pe = 12.5
        mock_row.price_to_book = 1.8
        mock_row.return_on_equity = 0.15
        mock_row.revenue_growth = 0.08
        mock_row.dividend_yield = 0.03
        mock_row.debt_to_equity = 0.5

        session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_row
        session.execute = AsyncMock(return_value=mock_result)

        result = await _load_fundamentals(session, asset_id=1)
        assert result is not None
        assert result["trailing_pe"] == 12.5
        assert result["price_to_book"] == 1.8
        assert result["return_on_equity"] == 0.15
        assert result["revenue_growth"] == 0.08
        assert result["dividend_yield"] == 0.03
        assert result["debt_to_equity"] == 0.5

    @pytest.mark.asyncio
    async def test_load_fundamentals_returns_none_when_no_row(self):
        """_load_fundamentals returns None when no StockFundamental row exists."""
        from src.data.analyze import _load_fundamentals

        session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        session.execute = AsyncMock(return_value=mock_result)

        result = await _load_fundamentals(session, asset_id=99)
        assert result is None

    @pytest.mark.asyncio
    async def test_load_latest_macro_returns_dict(self):
        """_load_latest_macro returns correct dict from MacroData rows."""
        from src.data.analyze import _load_latest_macro
        from src.db.models import MacroData

        row1 = MagicMock(spec=MacroData)
        row1.series_id = "DFF"
        row1.value = 5.25

        row2 = MagicMock(spec=MacroData)
        row2.series_id = "CPIAUCSL"
        row2.value = 3.2

        session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [row1, row2]
        session.execute = AsyncMock(return_value=mock_result)

        result = await _load_latest_macro(session)
        assert result is not None
        assert result["fed_funds_rate"] == 5.25
        assert result["cpi"] == 3.2

    @pytest.mark.asyncio
    async def test_load_latest_macro_returns_none_when_empty(self):
        """_load_latest_macro returns None when no MacroData rows exist."""
        from src.data.analyze import _load_latest_macro

        session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        session.execute = AsyncMock(return_value=mock_result)

        result = await _load_latest_macro(session)
        assert result is None


class TestFetchGlobalData:
    """Test that fetch_global_data calls all three global fetchers."""

    @pytest.mark.asyncio
    async def test_fetch_global_data_calls_macro_news_sentiment(self):
        """fetch_global_data calls macro, news, and sentiment fetchers."""
        from src.pipeline.main import fetch_global_data

        session = AsyncMock()
        # Mock watchlist query
        mock_result = MagicMock()
        mock_result.all.return_value = [("BBCA",), ("BTC",)]
        session.execute = AsyncMock(return_value=mock_result)

        with (
            patch("src.pipeline.main.fetch_macro_data", new_callable=AsyncMock) as mock_macro,
            patch("src.pipeline.main.fetch_news", new_callable=AsyncMock) as mock_news,
            patch("src.pipeline.main.fetch_sentiment_data", new_callable=AsyncMock) as mock_sentiment,
            patch("src.pipeline.main.set_sentiment_cache") as mock_set_cache,
            patch("src.pipeline.main.score_news_impact", new_callable=AsyncMock) as mock_score,
        ):
            mock_sentiment.return_value = MagicMock()  # SentimentSnapshot
            await fetch_global_data(session)

            mock_macro.assert_called_once_with(session)
            mock_news.assert_called_once_with(session)
            mock_sentiment.assert_called_once_with(session)
            mock_set_cache.assert_called_once()

    @pytest.mark.asyncio
    async def test_fetch_global_data_continues_on_error(self):
        """fetch_global_data continues if one fetcher raises an exception."""
        from src.pipeline.main import fetch_global_data

        session = AsyncMock()
        mock_result = MagicMock()
        mock_result.all.return_value = []
        session.execute = AsyncMock(return_value=mock_result)

        with (
            patch("src.pipeline.main.fetch_macro_data", side_effect=RuntimeError("FRED down")),
            patch("src.pipeline.main.fetch_news", new_callable=AsyncMock) as mock_news,
            patch("src.pipeline.main.fetch_sentiment_data", new_callable=AsyncMock) as mock_sentiment,
            patch("src.pipeline.main.set_sentiment_cache"),
            patch("src.pipeline.main.score_news_impact", new_callable=AsyncMock),
        ):
            mock_sentiment.return_value = MagicMock()
            # Should not raise -- exceptions are caught internally
            await fetch_global_data(session)
            # news and sentiment should still be called even after macro failed
            mock_news.assert_called_once_with(session)
            mock_sentiment.assert_called_once_with(session)
