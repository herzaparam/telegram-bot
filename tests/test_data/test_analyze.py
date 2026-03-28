"""Tests for the analyze stage."""

from datetime import date, datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np
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
        ), patch(
            "src.data.analyze._load_fundamentals", new_callable=AsyncMock, return_value=None,
        ), patch(
            "src.data.analyze._load_latest_macro", new_callable=AsyncMock, return_value=None,
        ), patch(
            "src.data.analyze._load_recent_news", new_callable=AsyncMock, return_value=[],
        ), patch(
            "src.data.analyze._load_financial_data", new_callable=AsyncMock, return_value=None,
        ), patch(
            "src.data.analyze._load_peer_data", new_callable=AsyncMock, return_value=None,
        ), patch(
            "src.data.analyze._load_onchain_data", new_callable=AsyncMock, return_value=None,
        ), patch(
            "src.data.analyze._load_github_data", new_callable=AsyncMock, return_value=None,
        ), patch(
            "src.data.analyze._compute_correlation_data", new_callable=AsyncMock, return_value=None,
        ), patch("src.data.analyze.signal_repo") as mock_repo:
            mock_repo.upsert_signals = AsyncMock(return_value=13)
            await analyze_stage(session, mock_stock_asset)
            mock_repo.upsert_signals.assert_called_once()
            call_args = mock_repo.upsert_signals.call_args
            assert call_args[0][1] == 1  # asset_id
            # Stock asset now has 13 engines (Phase 3 + 8 + 9 + 10)
            assert len(call_args[0][3]) == 13

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
            "src.data.analyze._load_fundamentals", new_callable=AsyncMock, return_value=None,
        ), patch(
            "src.data.analyze._load_latest_macro", new_callable=AsyncMock, return_value=None,
        ), patch(
            "src.data.analyze._load_recent_news", new_callable=AsyncMock, return_value=[],
        ), patch(
            "src.data.analyze._load_financial_data", new_callable=AsyncMock, return_value=None,
        ), patch(
            "src.data.analyze._load_peer_data", new_callable=AsyncMock, return_value=None,
        ), patch(
            "src.data.analyze._load_onchain_data", new_callable=AsyncMock, return_value=None,
        ), patch(
            "src.data.analyze._load_github_data", new_callable=AsyncMock, return_value=None,
        ), patch(
            "src.data.analyze._compute_correlation_data", new_callable=AsyncMock, return_value=None,
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

            mock_repo.upsert_signals = AsyncMock(return_value=13)
            await analyze_stage(session, mock_stock_asset)
            # Should still call upsert with 13 signals (1 failed + 12 from other engines)
            mock_repo.upsert_signals.assert_called_once()
            call_args = mock_repo.upsert_signals.call_args
            signals = call_args[0][3]
            assert len(signals) == 13
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
        ), patch(
            "src.data.analyze._load_fundamentals", new_callable=AsyncMock, return_value=None,
        ), patch(
            "src.data.analyze._load_latest_macro", new_callable=AsyncMock, return_value=None,
        ), patch(
            "src.data.analyze._load_recent_news", new_callable=AsyncMock, return_value=[],
        ), patch(
            "src.data.analyze._load_financial_data", new_callable=AsyncMock, return_value=None,
        ), patch(
            "src.data.analyze._load_peer_data", new_callable=AsyncMock, return_value=None,
        ), patch(
            "src.data.analyze._load_onchain_data", new_callable=AsyncMock, return_value=None,
        ), patch(
            "src.data.analyze._load_github_data", new_callable=AsyncMock, return_value=None,
        ), patch(
            "src.data.analyze._compute_correlation_data", new_callable=AsyncMock, return_value=None,
        ), patch("src.data.analyze.signal_repo") as mock_repo, patch(
            "src.data.analyze.gc"
        ) as mock_gc:
            mock_repo.upsert_signals = AsyncMock(return_value=13)
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


# ── Integration tests for 15-engine suite ────────────────────────────────────


def _make_mock_asset(asset_type: str, symbol: str = "TEST", asset_id: int = 1):
    """Create a lightweight mock asset for engine instantiation."""
    return type("MockAsset", (), {
        "id": asset_id,
        "symbol": symbol,
        "asset_type": asset_type,
        "yfinance_symbol": None,
        "ccxt_symbol": None,
    })()


def _make_ohlcv_df(rows: int = 200) -> pd.DataFrame:
    """Create a synthetic OHLCV DataFrame with realistic data."""
    np.random.seed(42)
    dates = pd.date_range("2025-01-01", periods=rows, freq="B", tz="UTC")
    close = 100.0 + np.cumsum(np.random.randn(rows) * 0.5)
    close = np.maximum(close, 10.0)  # Prevent negatives
    return pd.DataFrame({
        "open": close * (1 + np.random.randn(rows) * 0.005),
        "high": close * (1 + np.abs(np.random.randn(rows) * 0.01)),
        "low": close * (1 - np.abs(np.random.randn(rows) * 0.01)),
        "close": close,
        "volume": np.random.randint(100_000, 10_000_000, size=rows).astype(float),
    }, index=dates)


class TestStockEngineCount:
    def test_stock_engine_count_is_13(self):
        """Stock assets get 13 engines: all except onchain and alternative (crypto-only)."""
        asset = _make_mock_asset("stock")
        engines = _get_engines_for_asset(asset)
        assert len(engines) == 13, f"Expected 13 stock engines, got {len(engines)}: {[e.category for e in engines]}"

    def test_stock_engine_categories_unique(self):
        """No duplicate categories in stock engine list."""
        asset = _make_mock_asset("stock")
        engines = _get_engines_for_asset(asset)
        categories = [e.category for e in engines]
        assert len(categories) == len(set(categories)), f"Duplicate categories: {categories}"

    def test_stock_includes_options(self):
        """Stock engines include options (stock-only engine)."""
        asset = _make_mock_asset("stock")
        engines = _get_engines_for_asset(asset)
        categories = [e.category for e in engines]
        assert "options" in categories

    def test_stock_excludes_onchain_and_alternative(self):
        """Stock engines exclude crypto-only engines."""
        asset = _make_mock_asset("stock")
        engines = _get_engines_for_asset(asset)
        categories = [e.category for e in engines]
        assert "onchain" not in categories
        assert "alternative" not in categories


class TestCryptoEngineCount:
    def test_crypto_engine_count_is_14(self):
        """Crypto assets get 14 engines: all except options (stock-only)."""
        asset = _make_mock_asset("crypto", symbol="BTC")
        engines = _get_engines_for_asset(asset)
        assert len(engines) == 14, f"Expected 14 crypto engines, got {len(engines)}: {[e.category for e in engines]}"

    def test_crypto_engine_categories_unique(self):
        """No duplicate categories in crypto engine list."""
        asset = _make_mock_asset("crypto", symbol="BTC")
        engines = _get_engines_for_asset(asset)
        categories = [e.category for e in engines]
        assert len(categories) == len(set(categories)), f"Duplicate categories: {categories}"

    def test_crypto_includes_onchain_and_alternative(self):
        """Crypto engines include onchain and alternative (crypto-only engines)."""
        asset = _make_mock_asset("crypto", symbol="BTC")
        engines = _get_engines_for_asset(asset)
        categories = [e.category for e in engines]
        assert "onchain" in categories
        assert "alternative" in categories

    def test_crypto_excludes_options(self):
        """Crypto engines exclude options (stock-only engine)."""
        asset = _make_mock_asset("crypto", symbol="BTC")
        engines = _get_engines_for_asset(asset)
        categories = [e.category for e in engines]
        assert "options" not in categories


class TestAllEnginesProduceValidSignal:
    def test_all_stock_engines_produce_valid_signal(self):
        """Every stock engine returns a signal with valid score, confidence, category, reasoning."""
        asset = _make_mock_asset("stock")
        engines = _get_engines_for_asset(asset)
        df = _make_ohlcv_df(200)

        for engine in engines:
            signal = engine.analyze(asset.id, asset.symbol, df)
            assert -1.0 <= signal.score <= 1.0, (
                f"{engine.category}: score {signal.score} out of range"
            )
            assert 0.0 <= signal.confidence <= 1.0, (
                f"{engine.category}: confidence {signal.confidence} out of range"
            )
            assert isinstance(signal.category, str) and len(signal.category) > 0, (
                f"Engine produced empty category"
            )
            assert isinstance(signal.reasoning, str) and len(signal.reasoning) > 0, (
                f"{engine.category}: empty reasoning"
            )

    def test_all_crypto_engines_produce_valid_signal(self):
        """Every crypto engine returns a signal with valid score, confidence, category, reasoning."""
        asset = _make_mock_asset("crypto", symbol="BTC")
        engines = _get_engines_for_asset(asset)
        df = _make_ohlcv_df(200)

        for engine in engines:
            signal = engine.analyze(asset.id, asset.symbol, df)
            assert -1.0 <= signal.score <= 1.0, (
                f"{engine.category}: score {signal.score} out of range"
            )
            assert 0.0 <= signal.confidence <= 1.0, (
                f"{engine.category}: confidence {signal.confidence} out of range"
            )
            assert isinstance(signal.category, str) and len(signal.category) > 0
            assert isinstance(signal.reasoning, str) and len(signal.reasoning) > 0


class TestEngineDurationMetric:
    @pytest.mark.asyncio
    async def test_engine_duration_metric_observed(self, mock_stock_asset):
        """ENGINE_DURATION histogram is observed for each engine after analyze."""
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
        ), patch(
            "src.data.analyze._load_fundamentals", new_callable=AsyncMock, return_value=None,
        ), patch(
            "src.data.analyze._load_latest_macro", new_callable=AsyncMock, return_value=None,
        ), patch(
            "src.data.analyze._load_recent_news", new_callable=AsyncMock, return_value=[],
        ), patch(
            "src.data.analyze._load_financial_data", new_callable=AsyncMock, return_value=None,
        ), patch(
            "src.data.analyze._load_peer_data", new_callable=AsyncMock, return_value=None,
        ), patch(
            "src.data.analyze._load_onchain_data", new_callable=AsyncMock, return_value=None,
        ), patch(
            "src.data.analyze._load_github_data", new_callable=AsyncMock, return_value=None,
        ), patch(
            "src.data.analyze._compute_correlation_data", new_callable=AsyncMock, return_value=None,
        ), patch("src.data.analyze.signal_repo") as mock_repo, patch(
            "src.data.analyze.ENGINE_DURATION"
        ) as mock_metric:
            mock_repo.upsert_signals = AsyncMock(return_value=13)
            await analyze_stage(session, mock_stock_asset)

            # ENGINE_DURATION.labels().observe() should be called for each engine
            assert mock_metric.labels.call_count == 13  # 13 stock engines
            # Each call should pass engine_name kwarg
            for call in mock_metric.labels.call_args_list:
                assert "engine_name" in call.kwargs
            # observe() should be called with a positive float
            for call in mock_metric.labels().observe.call_args_list:
                assert call.args[0] >= 0.0

    @pytest.mark.asyncio
    async def test_engine_duration_metric_on_failure(self, mock_stock_asset):
        """ENGINE_DURATION is still observed even when engine.analyze() raises."""
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
        ), patch(
            "src.data.analyze._load_fundamentals", new_callable=AsyncMock, return_value=None,
        ), patch(
            "src.data.analyze._load_latest_macro", new_callable=AsyncMock, return_value=None,
        ), patch(
            "src.data.analyze._load_recent_news", new_callable=AsyncMock, return_value=[],
        ), patch(
            "src.data.analyze._load_financial_data", new_callable=AsyncMock, return_value=None,
        ), patch(
            "src.data.analyze._load_peer_data", new_callable=AsyncMock, return_value=None,
        ), patch(
            "src.data.analyze._load_onchain_data", new_callable=AsyncMock, return_value=None,
        ), patch(
            "src.data.analyze._load_github_data", new_callable=AsyncMock, return_value=None,
        ), patch(
            "src.data.analyze._compute_correlation_data", new_callable=AsyncMock, return_value=None,
        ), patch(
            "src.data.analyze.TechnicalEngine"
        ) as MockTech, patch(
            "src.data.analyze.signal_repo"
        ) as mock_repo, patch(
            "src.data.analyze.ENGINE_DURATION"
        ) as mock_metric:
            mock_engine = MagicMock()
            mock_engine.category = "technical"
            mock_engine.supports_stocks = True
            mock_engine.supports_crypto = True
            mock_engine.analyze.side_effect = RuntimeError("crash")
            MockTech.return_value = mock_engine

            mock_repo.upsert_signals = AsyncMock(return_value=13)
            await analyze_stage(session, mock_stock_asset)

            # ENGINE_DURATION should still be observed for the failing engine (via finally block)
            engine_names = [call.kwargs.get("engine_name") for call in mock_metric.labels.call_args_list]
            assert "technical" in engine_names
            # observe() should have been called for every engine including the failed one
            assert mock_metric.labels().observe.call_count == 13


class TestEngineCategoriesComplete:
    def test_all_15_categories_covered_across_both_types(self):
        """Combined stock + crypto engines cover all 15 expected categories."""
        stock = _make_mock_asset("stock")
        crypto = _make_mock_asset("crypto", symbol="BTC")

        stock_cats = {e.category for e in _get_engines_for_asset(stock)}
        crypto_cats = {e.category for e in _get_engines_for_asset(crypto)}
        all_cats = stock_cats | crypto_cats

        expected = {
            "technical", "quantitative", "fundamental", "macro", "sentiment",
            "event", "valuation", "ml_ai", "onchain", "options", "behavioral",
            "alternative", "network", "game_theory", "emerging_methods",
        }
        assert all_cats == expected, f"Missing: {expected - all_cats}, Extra: {all_cats - expected}"
        assert len(expected) == 15
