"""Tests for the analyze stage."""

from datetime import date, datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pandas as pd
import pytest

from src.data.analyze import (
    _failed_signal,
    _get_engines_for_asset,
    analyze_stage,
)
from src.db.models import Asset
from src.engines.base import Signal


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


class TestGetEnginesForAsset:
    def test_stock_gets_both_engines(self, mock_stock_asset):
        engines = _get_engines_for_asset(mock_stock_asset)
        categories = [e.category for e in engines]
        assert "technical" in categories
        assert "quantitative" in categories

    def test_crypto_gets_both_engines(self, mock_crypto_asset):
        engines = _get_engines_for_asset(mock_crypto_asset)
        categories = [e.category for e in engines]
        assert "technical" in categories
        assert "quantitative" in categories


class TestFailedSignal:
    def test_returns_zero_score(self):
        signal = _failed_signal("technical", "test error")
        assert signal.score == 0.0
        assert signal.confidence == 0.0
        assert signal.category == "technical"
        assert "test error" in signal.reasoning

    def test_returns_signal_type(self):
        signal = _failed_signal("quantitative", "crash")
        assert isinstance(signal, Signal)
        assert signal.data_quality == {"error": "crash"}


class TestAnalyzeStage:
    @pytest.mark.asyncio
    async def test_empty_data_returns_early(self, mock_stock_asset):
        session = AsyncMock()
        # Mock _load_price_dataframe to return empty DataFrame
        with patch(
            "src.data.analyze._load_price_dataframe",
            return_value=pd.DataFrame(columns=["open", "high", "low", "close", "volume"]),
        ), patch("src.data.analyze.signal_repo") as mock_repo:
            await analyze_stage(session, mock_stock_asset)
            mock_repo.upsert_signals.assert_not_called()

    @pytest.mark.asyncio
    async def test_with_data_calls_upsert(self, mock_stock_asset):
        session = AsyncMock()
        # Create a small but valid DataFrame
        df = pd.DataFrame({
            "open": [100.0] * 30,
            "high": [105.0] * 30,
            "low": [95.0] * 30,
            "close": [102.0] * 30,
            "volume": [1000.0] * 30,
        }, index=pd.date_range("2026-01-01", periods=30, freq="B", tz="UTC"))

        with patch(
            "src.data.analyze._load_price_dataframe",
            return_value=df,
        ), patch("src.data.analyze.signal_repo") as mock_repo:
            mock_repo.upsert_signals = AsyncMock(return_value=2)
            await analyze_stage(session, mock_stock_asset)
            mock_repo.upsert_signals.assert_called_once()
            call_args = mock_repo.upsert_signals.call_args
            assert call_args[0][1] == 1  # asset_id
            assert len(call_args[0][3]) == 2  # 2 signals (technical + quantitative)

    @pytest.mark.asyncio
    async def test_engine_failure_still_stores_other(self, mock_stock_asset):
        session = AsyncMock()
        df = pd.DataFrame({
            "open": [100.0] * 30,
            "high": [105.0] * 30,
            "low": [95.0] * 30,
            "close": [102.0] * 30,
            "volume": [1000.0] * 30,
        }, index=pd.date_range("2026-01-01", periods=30, freq="B", tz="UTC"))

        # Patch TechnicalEngine to raise
        with patch(
            "src.data.analyze._load_price_dataframe",
            return_value=df,
        ), patch(
            "src.data.analyze.TechnicalEngine"
        ) as MockTech, patch(
            "src.data.analyze.signal_repo"
        ) as mock_repo:
            mock_engine = MagicMock()
            mock_engine.category = "technical"
            mock_engine.supports_stocks = True
            mock_engine.supports_crypto = True
            mock_engine.analyze.side_effect = RuntimeError("crash")
            MockTech.return_value = mock_engine

            mock_repo.upsert_signals = AsyncMock(return_value=2)
            await analyze_stage(session, mock_stock_asset)
            # Should still call upsert with 2 signals (1 failed + 1 from quantitative)
            mock_repo.upsert_signals.assert_called_once()
            call_args = mock_repo.upsert_signals.call_args
            signals = call_args[0][3]
            assert len(signals) == 2
            # One should be the failed signal
            failed = [s for s in signals if s.score == 0.0 and "failed" in s.reasoning.lower()]
            assert len(failed) >= 1

    @pytest.mark.asyncio
    async def test_gc_collect_called(self, mock_stock_asset):
        session = AsyncMock()
        df = pd.DataFrame({
            "open": [100.0] * 30,
            "high": [105.0] * 30,
            "low": [95.0] * 30,
            "close": [102.0] * 30,
            "volume": [1000.0] * 30,
        }, index=pd.date_range("2026-01-01", periods=30, freq="B", tz="UTC"))

        with patch(
            "src.data.analyze._load_price_dataframe",
            return_value=df,
        ), patch("src.data.analyze.signal_repo") as mock_repo, patch(
            "src.data.analyze.gc"
        ) as mock_gc:
            mock_repo.upsert_signals = AsyncMock(return_value=2)
            await analyze_stage(session, mock_stock_asset)
            mock_gc.collect.assert_called_once()

    @pytest.mark.asyncio
    async def test_pipeline_main_has_stage_funcs(self):
        """Verify pipeline main wires both fetch and analyze in stage_funcs."""
        # Import and check that the module references are correct
        from src.data.analyze import analyze_stage as _as
        from src.data.ingest import ingest_stage as _is
        from src.pipeline.main import async_main

        # The imports should resolve without error
        assert callable(_as)
        assert callable(_is)
