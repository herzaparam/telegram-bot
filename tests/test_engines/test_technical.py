"""Unit tests for TechnicalEngine."""

import math

import pandas as pd
import pytest

from src.engines.technical import (
    TechnicalEngine,
    _bollinger_to_score,
    _ema_to_score,
    _macd_to_score,
    _rsi_to_score,
    _volume_to_score,
    compute_technical_indicators,
)


class TestTechnicalEngine:
    """Basic engine property tests."""

    def setup_method(self) -> None:
        self.engine = TechnicalEngine()

    def test_category_is_technical(self) -> None:
        assert self.engine.category == "technical"

    def test_supports_stocks(self) -> None:
        assert self.engine.supports_stocks is True

    def test_supports_crypto(self) -> None:
        assert self.engine.supports_crypto is True


class TestAnalyzeWith200Rows:
    """Tests with sufficient data (200 rows)."""

    def test_returns_valid_signal(self, sample_price_df_200: pd.DataFrame) -> None:
        engine = TechnicalEngine()
        signal = engine.analyze(1, "BBCA", sample_price_df_200)
        assert -1.0 <= signal.score <= 1.0
        assert 0.0 <= signal.confidence <= 1.0
        assert signal.category == "technical"
        assert len(signal.reasoning) > 0

    def test_indicators_dict_has_expected_keys(
        self, sample_price_df_200: pd.DataFrame
    ) -> None:
        engine = TechnicalEngine()
        signal = engine.analyze(1, "BBCA", sample_price_df_200)
        expected_keys = {
            "rsi_14",
            "rsi_7",
            "macd_line",
            "macd_histogram",
            "macd_signal",
            "bb_lower_2",
            "bb_mid",
            "bb_upper_2",
            "bb_lower_1",
            "bb_upper_1",
            "ema_9",
            "ema_21",
            "ema_50",
            "ema_100",
            "ema_200",
            "obv",
            "obv_trend",
            "volume_ratio",
        }
        assert expected_keys.issubset(set(signal.indicators.keys()))

    def test_data_quality_has_trading_days(
        self, sample_price_df_200: pd.DataFrame
    ) -> None:
        engine = TechnicalEngine()
        signal = engine.analyze(1, "BBCA", sample_price_df_200)
        assert "trading_days" in signal.data_quality
        assert signal.data_quality["trading_days"] == 200

    def test_reasoning_contains_indicator_info(
        self, sample_price_df_200: pd.DataFrame
    ) -> None:
        engine = TechnicalEngine()
        signal = engine.analyze(1, "BBCA", sample_price_df_200)
        assert "RSI" in signal.reasoning
        assert "MACD" in signal.reasoning


class TestInsufficientData:
    """Tests with limited or no data."""

    def test_10_rows_lower_confidence(
        self, sample_price_df_10: pd.DataFrame
    ) -> None:
        engine = TechnicalEngine()
        signal = engine.analyze(1, "BBCA", sample_price_df_10)
        assert signal.confidence < 0.8  # Should be penalized
        assert "indicators_skipped" in signal.data_quality
        assert len(signal.data_quality["indicators_skipped"]) > 0

    def test_empty_df_returns_zero(self, empty_price_df: pd.DataFrame) -> None:
        engine = TechnicalEngine()
        signal = engine.analyze(1, "BBCA", empty_price_df)
        assert signal.score == 0.0
        assert signal.confidence == 0.0
        assert "insufficient" in signal.reasoning.lower() or "no data" in signal.reasoning.lower()

    def test_very_small_df_returns_zero(self) -> None:
        df = pd.DataFrame(
            {
                "open": [100.0, 101.0],
                "high": [102.0, 103.0],
                "low": [99.0, 100.0],
                "close": [101.0, 102.0],
                "volume": [1000.0, 1100.0],
            }
        )
        engine = TechnicalEngine()
        signal = engine.analyze(1, "TEST", df)
        assert signal.score == 0.0
        assert signal.confidence == 0.0


class TestScoreRange:
    """Score clamping tests."""

    def test_score_always_clamped(self, sample_price_df_200: pd.DataFrame) -> None:
        engine = TechnicalEngine()
        signal = engine.analyze(1, "BBCA", sample_price_df_200)
        assert -1.0 <= signal.score <= 1.0

    def test_score_with_50_rows(self, sample_price_df_50: pd.DataFrame) -> None:
        engine = TechnicalEngine()
        signal = engine.analyze(1, "BBCA", sample_price_df_50)
        assert -1.0 <= signal.score <= 1.0
        assert 0.0 <= signal.confidence <= 1.0


class TestZoneFunctions:
    """Zone mapping function unit tests."""

    def test_rsi_oversold(self) -> None:
        assert _rsi_to_score(25) > 0  # Oversold = bullish

    def test_rsi_strongly_oversold(self) -> None:
        assert _rsi_to_score(15) > _rsi_to_score(25)

    def test_rsi_overbought(self) -> None:
        assert _rsi_to_score(75) < 0  # Overbought = bearish

    def test_rsi_strongly_overbought(self) -> None:
        assert _rsi_to_score(85) < _rsi_to_score(75)

    def test_rsi_neutral(self) -> None:
        assert _rsi_to_score(50) == 0.0

    def test_bollinger_below_lower_2(self) -> None:
        # Price below lower 2-sigma band = oversold = bullish
        score = _bollinger_to_score(
            close=90.0, lower_2=95.0, lower_1=97.0, upper_1=103.0, upper_2=105.0, mid=100.0
        )
        assert score > 0.5

    def test_bollinger_above_upper_2(self) -> None:
        # Price above upper 2-sigma band = overbought = bearish
        score = _bollinger_to_score(
            close=110.0, lower_2=95.0, lower_1=97.0, upper_1=103.0, upper_2=105.0, mid=100.0
        )
        assert score < -0.5

    def test_bollinger_middle(self) -> None:
        score = _bollinger_to_score(
            close=100.0, lower_2=95.0, lower_1=97.0, upper_1=103.0, upper_2=105.0, mid=100.0
        )
        assert -0.3 <= score <= 0.3

    def test_ema_all_above(self) -> None:
        # Price above all EMAs = bullish
        emas = {9: 99.0, 21: 98.0, 50: 97.0, 100: 96.0, 200: 95.0}
        score = _ema_to_score(close=100.0, emas=emas)
        assert score > 0.5

    def test_ema_all_below(self) -> None:
        # Price below all EMAs = bearish
        emas = {9: 101.0, 21: 102.0, 50: 103.0, 100: 104.0, 200: 105.0}
        score = _ema_to_score(close=100.0, emas=emas)
        assert score < -0.5

    def test_ema_handles_none_values(self) -> None:
        emas = {9: 99.0, 21: 98.0, 50: None, 100: None, 200: None}
        score = _ema_to_score(close=100.0, emas=emas)
        assert isinstance(score, float)

    def test_volume_bullish(self) -> None:
        score = _volume_to_score(obv_trend="bullish", volume_ratio=2.0)
        assert score > 0.3

    def test_volume_bearish(self) -> None:
        score = _volume_to_score(obv_trend="bearish", volume_ratio=0.5)
        assert score < -0.3


class TestExceptionHandling:
    """Engine never raises exceptions."""

    def test_nan_values_dont_crash(self) -> None:
        df = pd.DataFrame(
            {
                "open": [float("nan")] * 20,
                "high": [float("nan")] * 20,
                "low": [float("nan")] * 20,
                "close": [float("nan")] * 20,
                "volume": [float("nan")] * 20,
            }
        )
        engine = TechnicalEngine()
        signal = engine.analyze(1, "TEST", df)
        assert isinstance(signal.score, float)
        assert isinstance(signal.confidence, float)

    def test_zero_volume_doesnt_crash(self) -> None:
        df = pd.DataFrame(
            {
                "open": [100.0] * 30,
                "high": [101.0] * 30,
                "low": [99.0] * 30,
                "close": [100.5] * 30,
                "volume": [0.0] * 30,
            }
        )
        engine = TechnicalEngine()
        signal = engine.analyze(1, "TEST", df)
        assert isinstance(signal.score, float)


class TestComputeIndicators:
    """Tests for the compute_technical_indicators function."""

    def test_returns_dict(self, sample_price_df_200: pd.DataFrame) -> None:
        result = compute_technical_indicators(sample_price_df_200)
        assert isinstance(result, dict)
        assert "rsi_14" in result
        assert "skipped" in result

    def test_skipped_list_empty_with_200_rows(
        self, sample_price_df_200: pd.DataFrame
    ) -> None:
        result = compute_technical_indicators(sample_price_df_200)
        assert result["skipped"] == []

    def test_skipped_list_nonempty_with_10_rows(
        self, sample_price_df_10: pd.DataFrame
    ) -> None:
        result = compute_technical_indicators(sample_price_df_10)
        assert len(result["skipped"]) > 0
