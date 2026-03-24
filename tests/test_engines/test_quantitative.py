"""Tests for the QuantitativeEngine."""

import numpy as np
import pandas as pd
import pytest
from unittest.mock import patch

from src.engines.quantitative import (
    QuantitativeEngine,
    _hurst_exponent,
    _ou_half_life,
    _roc_to_score,
    _zscore_to_score,
)


class TestQuantitativeEngine:
    """Basic engine contract tests."""

    def setup_method(self) -> None:
        self.engine = QuantitativeEngine()

    def test_category(self) -> None:
        assert self.engine.category == "quantitative"

    def test_supports_stocks(self) -> None:
        assert self.engine.supports_stocks is True

    def test_supports_crypto(self) -> None:
        assert self.engine.supports_crypto is True


class TestAnalyzeFullData:
    """Tests with 200-row (sufficient) data."""

    def test_returns_valid_signal(self, sample_price_df_200: pd.DataFrame) -> None:
        engine = QuantitativeEngine()
        signal = engine.analyze(1, "BBCA", sample_price_df_200)
        assert -1.0 <= signal.score <= 1.0
        assert 0.0 <= signal.confidence <= 1.0
        assert signal.category == "quantitative"

    def test_indicators_contain_roc(self, sample_price_df_200: pd.DataFrame) -> None:
        engine = QuantitativeEngine()
        signal = engine.analyze(1, "BBCA", sample_price_df_200)
        assert "roc_5" in signal.indicators
        assert "roc_10" in signal.indicators
        assert "roc_20" in signal.indicators

    def test_indicators_contain_hurst(self, sample_price_df_200: pd.DataFrame) -> None:
        engine = QuantitativeEngine()
        signal = engine.analyze(1, "BBCA", sample_price_df_200)
        assert "hurst" in signal.indicators
        assert 0.0 <= signal.indicators["hurst"] <= 1.0

    def test_regime_in_indicators(self, sample_price_df_200: pd.DataFrame) -> None:
        engine = QuantitativeEngine()
        signal = engine.analyze(1, "BBCA", sample_price_df_200)
        assert "regime" in signal.indicators
        assert signal.indicators["regime"] in ("trending", "mean_reverting", "indeterminate")

    def test_reasoning_contains_regime(self, sample_price_df_200: pd.DataFrame) -> None:
        engine = QuantitativeEngine()
        signal = engine.analyze(1, "BBCA", sample_price_df_200)
        assert "Regime" in signal.reasoning or "regime" in signal.reasoning.lower()

    def test_indicators_contain_zscore(self, sample_price_df_200: pd.DataFrame) -> None:
        engine = QuantitativeEngine()
        signal = engine.analyze(1, "BBCA", sample_price_df_200)
        assert "z_score_20" in signal.indicators

    def test_indicators_contain_arima(self, sample_price_df_200: pd.DataFrame) -> None:
        engine = QuantitativeEngine()
        signal = engine.analyze(1, "BBCA", sample_price_df_200)
        assert "arima_forecast" in signal.indicators


class TestGracefulDegradation:
    """Tests for insufficient data handling."""

    def test_50_rows_skips_arima_hurst(self, sample_price_df_50: pd.DataFrame) -> None:
        engine = QuantitativeEngine()
        signal = engine.analyze(1, "BBCA", sample_price_df_50)
        assert "arima" in signal.data_quality.get("indicators_skipped", [])
        assert "hurst" in signal.data_quality.get("indicators_skipped", [])
        assert signal.confidence < 0.9  # Penalized for missing components

    def test_10_rows_returns_zero(self, sample_price_df_10: pd.DataFrame) -> None:
        engine = QuantitativeEngine()
        signal = engine.analyze(1, "BBCA", sample_price_df_10)
        assert signal.score == 0.0
        assert signal.confidence == 0.0

    def test_empty_returns_zero(self, empty_price_df: pd.DataFrame) -> None:
        engine = QuantitativeEngine()
        signal = engine.analyze(1, "BBCA", empty_price_df)
        assert signal.score == 0.0
        assert signal.confidence == 0.0


class TestRegimeWeighting:
    """Tests for Hurst-driven regime weighting."""

    def test_trending_regime_weights_momentum(self, sample_price_df_200: pd.DataFrame) -> None:
        with patch("src.engines.quantitative._hurst_exponent", return_value=0.7):
            engine = QuantitativeEngine()
            signal = engine.analyze(1, "BBCA", sample_price_df_200)
            assert signal.indicators.get("regime") == "trending"

    def test_mean_reverting_regime(self, sample_price_df_200: pd.DataFrame) -> None:
        with patch("src.engines.quantitative._hurst_exponent", return_value=0.3):
            engine = QuantitativeEngine()
            signal = engine.analyze(1, "BBCA", sample_price_df_200)
            assert signal.indicators.get("regime") == "mean_reverting"


class TestHelperFunctions:
    """Tests for module-level helper functions."""

    def test_hurst_returns_valid_range(self) -> None:
        np.random.seed(42)
        prices = np.cumsum(np.random.randn(500)) + 100
        prices = np.abs(prices) + 1  # Ensure positive
        h = _hurst_exponent(prices)
        assert 0.0 <= h <= 1.0

    def test_hurst_short_data_returns_half(self) -> None:
        h = _hurst_exponent(np.array([1.0, 2.0, 3.0]))
        assert h == 0.5

    def test_ou_half_life_positive(self) -> None:
        np.random.seed(42)
        prices = 100 + np.sin(np.linspace(0, 10, 200)) * 5
        hl = _ou_half_life(prices)
        assert hl > 0

    def test_roc_positive_bullish(self) -> None:
        score = _roc_to_score(3.0, 5.0, 8.0)
        assert score > 0

    def test_roc_negative_bearish(self) -> None:
        score = _roc_to_score(-3.0, -5.0, -8.0)
        assert score < 0

    def test_zscore_oversold(self) -> None:
        score = _zscore_to_score(-2.5, -2.0)
        assert score > 0  # Oversold = bullish


class TestExceptionHandling:
    """Tests for error resilience."""

    def test_arima_failure_still_produces_signal(self, sample_price_df_200: pd.DataFrame) -> None:
        with patch("src.engines.quantitative._arima_forecast", side_effect=ValueError("fit failed")):
            engine = QuantitativeEngine()
            signal = engine.analyze(1, "BBCA", sample_price_df_200)
            assert isinstance(signal.score, float)
            assert "arima" in signal.data_quality.get("indicators_skipped", [])
