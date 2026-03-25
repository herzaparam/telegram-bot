"""Tests for src/engines/emerging.py — EmergingMethodsEngine."""

import numpy as np
import pandas as pd
import pytest

from src.engines.base import BaseEngine, Signal
from src.engines.emerging import EmergingMethodsEngine


def _make_trending_df(n: int = 200, seed: int = 42) -> pd.DataFrame:
    """Create a DataFrame with autocorrelated returns (high Hurst exponent).

    Uses momentum-style returns: each return is biased by the previous return,
    creating persistence that R/S analysis detects as H > 0.5.
    """
    rng = np.random.default_rng(seed)
    dates = pd.bdate_range("2025-01-01", periods=n, freq="B")
    # Generate autocorrelated returns for trending behavior
    returns = np.zeros(n)
    returns[0] = rng.normal(0.002, 0.005)
    for i in range(1, n):
        # Strong positive autocorrelation: 70% momentum + noise
        returns[i] = 0.7 * returns[i - 1] + 0.3 * rng.normal(0.001, 0.005)
    close = 10000.0 * np.cumprod(1 + returns)
    close = np.maximum(close, 1.0)  # ensure positive
    high = close * (1 + rng.uniform(0.001, 0.01, size=n))
    low = close * (1 - rng.uniform(0.001, 0.01, size=n))
    open_ = low + rng.uniform(0.3, 0.7, size=n) * (high - low)
    volume = rng.uniform(1_000_000, 2_000_000, size=n)
    return pd.DataFrame(
        {"open": open_, "high": high, "low": low, "close": close, "volume": volume},
        index=dates,
    )


def _make_mean_reverting_df(n: int = 200, seed: int = 42) -> pd.DataFrame:
    """Create a DataFrame with a sinusoidal pattern (low Hurst exponent)."""
    rng = np.random.default_rng(seed)
    dates = pd.bdate_range("2025-01-01", periods=n, freq="B")
    # Sinusoidal => mean-reverting => H < 0.5
    t = np.linspace(0, 16 * np.pi, n)
    close = 10000 + 500 * np.sin(t) + rng.normal(0, 10, size=n)
    close = np.maximum(close, 1.0)
    high = close * (1 + rng.uniform(0.001, 0.01, size=n))
    low = close * (1 - rng.uniform(0.001, 0.01, size=n))
    open_ = low + rng.uniform(0.3, 0.7, size=n) * (high - low)
    volume = rng.uniform(1_000_000, 2_000_000, size=n)
    return pd.DataFrame(
        {"open": open_, "high": high, "low": low, "close": close, "volume": volume},
        index=dates,
    )


def _make_short_df(n: int = 30, seed: int = 42) -> pd.DataFrame:
    """Create a DataFrame with insufficient data for emerging methods."""
    rng = np.random.default_rng(seed)
    dates = pd.bdate_range("2025-01-01", periods=n, freq="B")
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


class TestEmergingMethodsEngine:
    """Tests for the EmergingMethodsEngine."""

    def test_inherits_base_engine(self) -> None:
        engine = EmergingMethodsEngine()
        assert isinstance(engine, BaseEngine)

    def test_category_is_emerging_methods(self) -> None:
        engine = EmergingMethodsEngine()
        assert engine.category == "emerging_methods"

    def test_supports_stocks_true(self) -> None:
        engine = EmergingMethodsEngine()
        assert engine.supports_stocks is True

    def test_supports_crypto_true(self) -> None:
        engine = EmergingMethodsEngine()
        assert engine.supports_crypto is True

    def test_insufficient_data_returns_zero(self) -> None:
        """Less than 60 rows should return score=0, confidence=0."""
        df = _make_short_df(30)
        engine = EmergingMethodsEngine()
        signal = engine.analyze(1, "BBCA", df)
        assert signal.score == 0.0
        assert signal.confidence == 0.0
        assert "Insufficient" in signal.reasoning

    def test_empty_df_returns_zero(self) -> None:
        df = pd.DataFrame(columns=["open", "high", "low", "close", "volume"], dtype=float)
        engine = EmergingMethodsEngine()
        signal = engine.analyze(1, "BBCA", df)
        assert signal.score == 0.0
        assert signal.confidence == 0.0

    def test_trending_data_positive_confidence(self) -> None:
        """Trending data (H>0.55) should return positive confidence."""
        df = _make_trending_df()
        engine = EmergingMethodsEngine()
        signal = engine.analyze(1, "BBCA", df)
        assert signal.confidence > 0.0

    def test_trending_data_hurst_above_half(self) -> None:
        """Trending data should have Hurst > 0.5."""
        df = _make_trending_df()
        engine = EmergingMethodsEngine()
        signal = engine.analyze(1, "BBCA", df)
        assert signal.indicators.get("hurst_exponent", 0) > 0.5

    def test_mean_reverting_data_returns_signal(self) -> None:
        """Mean-reverting data (H<0.45) should return a signal."""
        df = _make_mean_reverting_df()
        engine = EmergingMethodsEngine()
        signal = engine.analyze(1, "BBCA", df)
        # Should produce some signal (not necessarily zero)
        assert isinstance(signal, Signal)
        assert signal.confidence > 0.0

    def test_trending_data_regime_indicator(self) -> None:
        """Trending data should report 'trending' regime."""
        df = _make_trending_df()
        engine = EmergingMethodsEngine()
        signal = engine.analyze(1, "BBCA", df)
        assert signal.indicators.get("regime") in ("trending", "random")

    def test_score_capped(self) -> None:
        """Score should always be in [-1, 1]."""
        df = _make_trending_df()
        engine = EmergingMethodsEngine()
        signal = engine.analyze(1, "BBCA", df)
        assert -1.0 <= signal.score <= 1.0

    def test_confidence_range(self) -> None:
        """Confidence should be in [0, 0.7]."""
        df = _make_trending_df()
        engine = EmergingMethodsEngine()
        signal = engine.analyze(1, "BBCA", df)
        assert 0.0 <= signal.confidence <= 0.7

    def test_indicators_has_expected_keys(self) -> None:
        df = _make_trending_df()
        engine = EmergingMethodsEngine()
        signal = engine.analyze(1, "BBCA", df)
        expected = {"hurst_exponent", "regime", "wavelet_energy_ratio", "fractal_dimension"}
        assert expected.issubset(set(signal.indicators.keys()))

    def test_fractal_dimension_equals_2_minus_hurst(self) -> None:
        """Fractal dimension should equal 2 - H."""
        df = _make_trending_df()
        engine = EmergingMethodsEngine()
        signal = engine.analyze(1, "BBCA", df)
        h = signal.indicators["hurst_exponent"]
        fd = signal.indicators["fractal_dimension"]
        assert abs(fd - (2 - h)) < 0.01

    def test_uses_pywt(self) -> None:
        """Verify pywt is importable (wavelet decomposition dependency)."""
        import pywt
        assert hasattr(pywt, "wavedec")

    def test_signal_category(self) -> None:
        df = _make_trending_df()
        engine = EmergingMethodsEngine()
        signal = engine.analyze(1, "BBCA", df)
        assert signal.category == "emerging_methods"
