"""Tests for src/engines/behavioral.py — BehavioralEngine."""

import numpy as np
import pandas as pd
import pytest

from src.engines.base import BaseEngine, Signal
from src.engines.behavioral import BehavioralEngine


def _make_df(n: int, seed: int = 42) -> pd.DataFrame:
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


class TestBehavioralEngine:
    """Tests for the BehavioralEngine."""

    def test_inherits_base_engine(self) -> None:
        engine = BehavioralEngine()
        assert isinstance(engine, BaseEngine)

    def test_category_is_behavioral(self) -> None:
        engine = BehavioralEngine()
        assert engine.category == "behavioral"

    def test_supports_stocks_true(self) -> None:
        engine = BehavioralEngine()
        assert engine.supports_stocks is True

    def test_supports_crypto_true(self) -> None:
        engine = BehavioralEngine()
        assert engine.supports_crypto is True

    def test_insufficient_data_returns_zero(self) -> None:
        """Less than 20 rows should return score=0, confidence=0."""
        df = _make_df(15)
        engine = BehavioralEngine()
        signal = engine.analyze(1, "BBCA", df)
        assert signal.score == 0.0
        assert signal.confidence == 0.0
        assert "Insufficient" in signal.reasoning

    def test_empty_df_returns_zero(self, empty_price_df: pd.DataFrame) -> None:
        engine = BehavioralEngine()
        signal = engine.analyze(1, "BBCA", empty_price_df)
        assert signal.score == 0.0
        assert signal.confidence == 0.0

    def test_normal_data_low_confidence(self) -> None:
        """Normal data (no spikes, no gaps, no divergence) should give low confidence."""
        df = _make_df(50, seed=42)
        engine = BehavioralEngine()
        signal = engine.analyze(1, "BBCA", df)
        assert signal.confidence <= 0.5

    def test_volume_spike_detected(self) -> None:
        """A volume spike (>2 std dev) should produce non-zero score."""
        df = _make_df(50, seed=42)
        # Override last row volume to be 3x the mean
        mean_vol = df["volume"].iloc[:-1].mean()
        std_vol = df["volume"].iloc[:-1].std()
        df.iloc[-1, df.columns.get_loc("volume")] = mean_vol + 3.0 * std_vol
        engine = BehavioralEngine()
        signal = engine.analyze(1, "BBCA", df)
        assert signal.score != 0.0
        assert signal.indicators.get("is_spike") is True

    def test_volume_z_score_in_indicators(self) -> None:
        df = _make_df(50, seed=42)
        engine = BehavioralEngine()
        signal = engine.analyze(1, "BBCA", df)
        assert "volume_z_score" in signal.indicators

    def test_divergence_detected(self) -> None:
        """Rising prices with falling volume should detect divergence."""
        df = _make_df(50, seed=42)
        # Make last 5 days: rising close
        for i in range(-5, 0):
            df.iloc[i, df.columns.get_loc("close")] = df["close"].iloc[i - 1] * 1.02
        # Make last 5 days: falling volume (much lower than prior 5 days)
        for i in range(-5, 0):
            df.iloc[i, df.columns.get_loc("volume")] = 100_000  # very low
        for i in range(-10, -5):
            df.iloc[i, df.columns.get_loc("volume")] = 3_000_000  # high
        engine = BehavioralEngine()
        signal = engine.analyze(1, "BBCA", df)
        assert signal.indicators.get("divergence") is True

    def test_gap_detection(self) -> None:
        """A price gap > 3% should be detected."""
        df = _make_df(50, seed=42)
        # Create a gap: open of last row much higher than close of second to last
        prev_close = df["close"].iloc[-2]
        df.iloc[-1, df.columns.get_loc("open")] = prev_close * 1.05  # 5% gap
        engine = BehavioralEngine()
        signal = engine.analyze(1, "BBCA", df)
        assert signal.indicators.get("is_gap") is True

    def test_signal_score_capped(self) -> None:
        """Score should always be in [-1, 1]."""
        df = _make_df(50, seed=42)
        engine = BehavioralEngine()
        signal = engine.analyze(1, "BBCA", df)
        assert -1.0 <= signal.score <= 1.0

    def test_signal_confidence_range(self) -> None:
        """Confidence should be in [0, 1]."""
        df = _make_df(50, seed=42)
        engine = BehavioralEngine()
        signal = engine.analyze(1, "BBCA", df)
        assert 0.0 <= signal.confidence <= 1.0

    def test_signal_category_in_output(self) -> None:
        df = _make_df(50, seed=42)
        engine = BehavioralEngine()
        signal = engine.analyze(1, "BBCA", df)
        assert signal.category == "behavioral"

    def test_indicators_has_expected_keys(self) -> None:
        df = _make_df(50, seed=42)
        engine = BehavioralEngine()
        signal = engine.analyze(1, "BBCA", df)
        expected_keys = {"volume_z_score", "is_spike", "gap_pct", "is_gap", "divergence"}
        assert expected_keys.issubset(set(signal.indicators.keys()))
