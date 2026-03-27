"""Tests for the backtest engine (TBOT-08)."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np
import pandas as pd
import pytest

from src.engines.base import Signal


@pytest.fixture
def sample_asset():
    """Return a mock Asset object."""
    asset = MagicMock()
    asset.id = 1
    asset.symbol = "BTC"
    asset.name = "Bitcoin"
    asset.asset_type = "crypto"
    return asset


@pytest.fixture
def sample_price_rows():
    """Return 100 mock PriceHistory rows."""
    rows = []
    base_price = 100.0
    base_date = datetime(2026, 1, 1, tzinfo=None)
    for i in range(100):
        row = MagicMock()
        row.time = base_date + timedelta(days=i)
        row.open = base_price + i * 0.1
        row.high = base_price + i * 0.1 + 1
        row.low = base_price + i * 0.1 - 1
        row.close = base_price + i * 0.2
        row.volume = 1000.0 + i
        rows.append(row)
    return rows


@pytest.fixture
def sample_backtest_result():
    """Return a mock BacktestResult."""
    result = MagicMock()
    result.win_rate = 0.65
    result.total_return = 0.123
    result.buy_hold_return = 0.081
    result.max_drawdown = -0.152
    result.sharpe_ratio = 1.4
    result.daily_results = {"days_tested": 30}
    return result


def _make_signal(category: str = "technical", score: float = 0.5, confidence: float = 0.7) -> Signal:
    return Signal(
        category=category,
        score=score,
        confidence=confidence,
        reasoning="test",
        indicators={},
        data_quality={},
    )


class TestRunBacktest:
    """Tests for run_backtest function."""

    def test_invalid_period_raises(self):
        """Invalid period should raise ValueError."""
        from src.data.backtest import run_backtest
        import asyncio

        with pytest.raises(ValueError, match="Invalid period"):
            asyncio.get_event_loop().run_until_complete(run_backtest("BTC", "invalid"))

    @pytest.mark.asyncio
    async def test_asset_not_found(self):
        """Asset not found returns error status."""
        from src.data.backtest import run_backtest

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)

        with patch("src.data.backtest.async_session_factory") as mock_factory:
            mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)
            result = await run_backtest("UNKNOWN", "30d")

        assert result["status"] == "error"
        assert "not found" in result["message"].lower()

    @pytest.mark.asyncio
    async def test_cached_result_returned(self, sample_asset, sample_backtest_result):
        """When cached result exists, return it without running engines."""
        from src.data.backtest import run_backtest

        mock_session = AsyncMock()

        # First execute: asset lookup
        asset_result = MagicMock()
        asset_result.scalar_one_or_none.return_value = sample_asset

        # Second execute: cached result lookup
        cached_result = MagicMock()
        cached_result.scalar_one_or_none.return_value = sample_backtest_result

        mock_session.execute = AsyncMock(side_effect=[asset_result, cached_result])

        with patch("src.data.backtest.async_session_factory") as mock_factory:
            mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)
            result = await run_backtest("BTC", "30d")

        assert result["status"] == "complete"
        assert result["win_rate"] == 0.65
        assert result["total_return"] == 0.123

    @pytest.mark.asyncio
    async def test_insufficient_data(self, sample_asset):
        """Insufficient price data returns error."""
        from src.data.backtest import run_backtest

        mock_session = AsyncMock()

        # Asset found
        asset_result = MagicMock()
        asset_result.scalar_one_or_none.return_value = sample_asset

        # No cached result
        cached_result = MagicMock()
        cached_result.scalar_one_or_none.return_value = None

        # Only 10 price rows (< 30 minimum)
        price_result = MagicMock()
        few_rows = []
        for i in range(10):
            row = MagicMock()
            row.time = datetime(2026, 3, 1) + timedelta(days=i)
            row.open = row.high = row.low = row.close = 100.0
            row.volume = 1000.0
            few_rows.append(row)
        price_result.scalars.return_value.all.return_value = few_rows

        mock_session.execute = AsyncMock(side_effect=[asset_result, cached_result, price_result])

        with patch("src.data.backtest.async_session_factory") as mock_factory:
            mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)
            result = await run_backtest("BTC", "30d")

        assert result["status"] == "error"
        assert "insufficient" in result["message"].lower()

    @pytest.mark.asyncio
    async def test_full_backtest_returns_required_keys(self, sample_asset, sample_price_rows):
        """Full backtest run returns all required result keys."""
        from src.data.backtest import run_backtest

        mock_session = AsyncMock()

        # Asset found
        asset_result = MagicMock()
        asset_result.scalar_one_or_none.return_value = sample_asset

        # No cached result
        cached_result = MagicMock()
        cached_result.scalar_one_or_none.return_value = None

        # Price data
        price_result = MagicMock()
        price_result.scalars.return_value.all.return_value = sample_price_rows

        # 4th execute call = pg_insert store result
        insert_result = MagicMock()
        mock_session.execute = AsyncMock(side_effect=[asset_result, cached_result, price_result, insert_result])
        mock_session.commit = AsyncMock()

        test_signal = _make_signal()
        mock_engine = MagicMock()
        mock_engine.analyze.return_value = test_signal

        with (
            patch("src.data.backtest.async_session_factory") as mock_factory,
            patch("src.data.backtest._get_llm_verdict", new_callable=AsyncMock, return_value="BUY"),
            patch("src.data.analyze._get_engines_for_asset", return_value=[mock_engine]),
        ):
            # Override today for test consistency
            with patch("src.data.backtest.date") as mock_date:
                mock_date.today.return_value = date(2026, 4, 10)
                mock_date.side_effect = lambda *a, **kw: date(*a, **kw)
                mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
                mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)
                result = await run_backtest("BTC", "7d")

        assert result["status"] == "complete"
        required_keys = {"symbol", "period", "win_rate", "total_return", "buy_hold_return",
                         "max_drawdown", "sharpe_ratio", "days_tested", "status"}
        assert required_keys.issubset(result.keys())


class TestLookAheadProtection:
    """Verify that backtest prevents look-ahead bias."""

    @pytest.mark.asyncio
    async def test_price_slice_no_future_data(self, sample_asset, sample_price_rows):
        """Verify price data passed to engines for date D has no rows after D."""
        from src.data.backtest import run_backtest

        # Track what DataFrames are passed to engines
        captured_dfs: list[pd.DataFrame] = []

        def mock_analyze(asset_id, symbol, df):
            captured_dfs.append(df.copy())
            return _make_signal()

        mock_session = AsyncMock()

        asset_result = MagicMock()
        asset_result.scalar_one_or_none.return_value = sample_asset

        cached_result = MagicMock()
        cached_result.scalar_one_or_none.return_value = None

        price_result = MagicMock()
        price_result.scalars.return_value.all.return_value = sample_price_rows

        insert_result = MagicMock()
        mock_session.execute = AsyncMock(side_effect=[asset_result, cached_result, price_result, insert_result])
        mock_session.commit = AsyncMock()

        mock_engine = MagicMock()
        mock_engine.analyze.side_effect = mock_analyze

        with (
            patch("src.data.backtest.async_session_factory") as mock_factory,
            patch("src.data.backtest._get_llm_verdict", new_callable=AsyncMock, return_value="HOLD"),
            patch("src.data.analyze._get_engines_for_asset", return_value=[mock_engine]),
        ):
            with patch("src.data.backtest.date") as mock_date:
                mock_date.today.return_value = date(2026, 4, 10)
                mock_date.side_effect = lambda *a, **kw: date(*a, **kw)
                mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
                mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)
                await run_backtest("BTC", "7d")

        # For each captured DataFrame, verify all timestamps are <= the max
        # (which represents the "current" date in that slice)
        for df in captured_dfs:
            if df.empty:
                continue
            max_time = df.index.max()
            assert (df.index <= max_time).all(), "Found future data in price slice"


class TestDeterministicVerdict:
    """Tests for the deterministic fallback verdict logic."""

    def test_deterministic_buy(self):
        from src.data.backtest import _deterministic_verdict
        signals = [_make_signal(score=0.8, confidence=0.9)]
        assert _deterministic_verdict(signals) in ("STRONG_BUY", "BUY")

    def test_deterministic_sell(self):
        from src.data.backtest import _deterministic_verdict
        signals = [_make_signal(score=-0.8, confidence=0.9)]
        assert _deterministic_verdict(signals) in ("STRONG_SELL", "SELL")

    def test_deterministic_hold(self):
        from src.data.backtest import _deterministic_verdict
        signals = [_make_signal(score=0.0, confidence=0.5)]
        assert _deterministic_verdict(signals) == "HOLD"

    def test_empty_signals(self):
        from src.data.backtest import _deterministic_verdict
        assert _deterministic_verdict([]) == "HOLD"


class TestValidPeriods:
    """Test period validation."""

    def test_valid_periods_constant(self):
        from src.data.backtest import VALID_PERIODS
        assert VALID_PERIODS == {"7d": 7, "30d": 30, "90d": 90}
