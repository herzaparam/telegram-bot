"""Tests for src/engines/network.py — NetworkEngine."""

import numpy as np
import pandas as pd
import pytest

from src.engines.base import BaseEngine, Signal
from src.engines.network import NetworkEngine


def _make_df(n: int = 50, seed: int = 42) -> pd.DataFrame:
    """Create a DataFrame with n rows of synthetic OHLCV data."""
    rng = np.random.default_rng(seed)
    dates = pd.bdate_range("2025-06-01", periods=n, freq="B")
    returns = rng.normal(0.0005, 0.015, size=n)
    close = 10000.0 * np.cumprod(1 + returns)
    high = close * (1 + rng.uniform(0.001, 0.02, size=n))
    low = close * (1 - rng.uniform(0.001, 0.02, size=n))
    open_ = low + rng.uniform(0.3, 0.7, size=n) * (high - low)
    volume = rng.uniform(1_000_000, 2_000_000, size=n)
    return pd.DataFrame(
        {"open": open_, "high": high, "low": low, "close": close, "volume": volume},
        index=dates,
    )


class TestNetworkEngine:
    """Tests for the NetworkEngine."""

    def test_inherits_base_engine(self) -> None:
        engine = NetworkEngine()
        assert isinstance(engine, BaseEngine)

    def test_category_is_network(self) -> None:
        engine = NetworkEngine()
        assert engine.category == "network"

    def test_supports_stocks_true(self) -> None:
        engine = NetworkEngine()
        assert engine.supports_stocks is True

    def test_supports_crypto_true(self) -> None:
        engine = NetworkEngine()
        assert engine.supports_crypto is True

    def test_no_correlation_data_returns_zero(self) -> None:
        """No correlation data should return score=0, confidence=0."""
        engine = NetworkEngine(correlation_data=None)
        df = _make_df()
        signal = engine.analyze(1, "BBCA", df)
        assert signal.score == 0.0
        assert signal.confidence == 0.0
        assert "No correlation data" in signal.reasoning

    def test_empty_correlation_data_returns_zero(self) -> None:
        """Empty dict should return score=0, confidence=0."""
        engine = NetworkEngine(correlation_data={})
        df = _make_df()
        signal = engine.analyze(1, "BBCA", df)
        assert signal.score == 0.0
        assert signal.confidence == 0.0

    def test_high_correlation_bearish(self) -> None:
        """High avg correlation (>0.7) should produce negative score."""
        data = {
            "avg_correlation": 0.85,
            "max_correlation": 0.95,
            "correlation_change_30d": 0.05,
            "num_assets": 5,
        }
        engine = NetworkEngine(correlation_data=data)
        df = _make_df()
        signal = engine.analyze(1, "BBCA", df)
        assert signal.score < 0  # bearish

    def test_low_correlation_bullish(self) -> None:
        """Low avg correlation (<0.3) should produce positive score."""
        data = {
            "avg_correlation": 0.2,
            "max_correlation": 0.4,
            "correlation_change_30d": 0.0,
            "num_assets": 5,
        }
        engine = NetworkEngine(correlation_data=data)
        df = _make_df()
        signal = engine.analyze(1, "BBCA", df)
        assert signal.score > 0  # bullish

    def test_neutral_correlation(self) -> None:
        """Mid-range correlation should produce small score."""
        data = {
            "avg_correlation": 0.5,
            "max_correlation": 0.6,
            "correlation_change_30d": 0.0,
            "num_assets": 5,
        }
        engine = NetworkEngine(correlation_data=data)
        df = _make_df()
        signal = engine.analyze(1, "BBCA", df)
        assert abs(signal.score) < 0.3

    def test_regime_change_increases_signal(self) -> None:
        """Large correlation change (>0.15) should increase signal strength."""
        data_stable = {
            "avg_correlation": 0.85,
            "max_correlation": 0.95,
            "correlation_change_30d": 0.05,
            "num_assets": 5,
        }
        data_change = {
            "avg_correlation": 0.85,
            "max_correlation": 0.95,
            "correlation_change_30d": 0.25,
            "num_assets": 5,
        }
        engine_stable = NetworkEngine(correlation_data=data_stable)
        engine_change = NetworkEngine(correlation_data=data_change)
        df = _make_df()
        signal_stable = engine_stable.analyze(1, "BBCA", df)
        signal_change = engine_change.analyze(1, "BBCA", df)
        assert abs(signal_change.score) >= abs(signal_stable.score)

    def test_more_assets_higher_confidence(self) -> None:
        """More assets should increase confidence."""
        data_few = {
            "avg_correlation": 0.5,
            "max_correlation": 0.6,
            "correlation_change_30d": 0.0,
            "num_assets": 2,
        }
        data_many = {
            "avg_correlation": 0.5,
            "max_correlation": 0.6,
            "correlation_change_30d": 0.0,
            "num_assets": 10,
        }
        engine_few = NetworkEngine(correlation_data=data_few)
        engine_many = NetworkEngine(correlation_data=data_many)
        df = _make_df()
        signal_few = engine_few.analyze(1, "BBCA", df)
        signal_many = engine_many.analyze(1, "BBCA", df)
        assert signal_many.confidence >= signal_few.confidence

    def test_score_capped(self) -> None:
        """Score should always be in [-1, 1]."""
        data = {
            "avg_correlation": 0.99,
            "max_correlation": 1.0,
            "correlation_change_30d": 0.5,
            "num_assets": 20,
        }
        engine = NetworkEngine(correlation_data=data)
        df = _make_df()
        signal = engine.analyze(1, "BBCA", df)
        assert -1.0 <= signal.score <= 1.0

    def test_confidence_range(self) -> None:
        """Confidence should be in [0, 1]."""
        data = {
            "avg_correlation": 0.5,
            "max_correlation": 0.6,
            "correlation_change_30d": 0.0,
            "num_assets": 5,
        }
        engine = NetworkEngine(correlation_data=data)
        df = _make_df()
        signal = engine.analyze(1, "BBCA", df)
        assert 0.0 <= signal.confidence <= 1.0

    def test_indicators_has_expected_keys(self) -> None:
        data = {
            "avg_correlation": 0.5,
            "max_correlation": 0.6,
            "correlation_change_30d": 0.1,
            "num_assets": 5,
        }
        engine = NetworkEngine(correlation_data=data)
        df = _make_df()
        signal = engine.analyze(1, "BBCA", df)
        expected = {"avg_correlation", "max_correlation", "correlation_change_30d", "num_assets"}
        assert expected.issubset(set(signal.indicators.keys()))

    def test_signal_category(self) -> None:
        data = {"avg_correlation": 0.5, "max_correlation": 0.6, "correlation_change_30d": 0.0, "num_assets": 5}
        engine = NetworkEngine(correlation_data=data)
        df = _make_df()
        signal = engine.analyze(1, "BBCA", df)
        assert signal.category == "network"
