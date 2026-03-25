"""Tests for src/engines/options.py — OptionsEngine stub."""

import pandas as pd
import pytest

from src.engines.base import BaseEngine, Signal
from src.engines.options import OptionsEngine


class TestOptionsEngine:
    """Tests for the OptionsEngine stub."""

    def test_inherits_base_engine(self) -> None:
        engine = OptionsEngine()
        assert isinstance(engine, BaseEngine)

    def test_category_is_options(self) -> None:
        engine = OptionsEngine()
        assert engine.category == "options"

    def test_supports_stocks_true(self) -> None:
        engine = OptionsEngine()
        assert engine.supports_stocks is True

    def test_supports_crypto_false(self) -> None:
        engine = OptionsEngine()
        assert engine.supports_crypto is False

    def test_analyze_returns_signal(self, sample_price_df_50: pd.DataFrame) -> None:
        engine = OptionsEngine()
        signal = engine.analyze(1, "BBCA", sample_price_df_50)
        assert isinstance(signal, Signal)

    def test_analyze_returns_zero_score(self, sample_price_df_50: pd.DataFrame) -> None:
        engine = OptionsEngine()
        signal = engine.analyze(1, "BBCA", sample_price_df_50)
        assert signal.score == 0.0

    def test_analyze_returns_zero_confidence(self, sample_price_df_50: pd.DataFrame) -> None:
        engine = OptionsEngine()
        signal = engine.analyze(1, "BBCA", sample_price_df_50)
        assert signal.confidence == 0.0

    def test_analyze_category_in_signal(self, sample_price_df_50: pd.DataFrame) -> None:
        engine = OptionsEngine()
        signal = engine.analyze(1, "BBCA", sample_price_df_50)
        assert signal.category == "options"

    def test_analyze_reasoning_mentions_idx(self, sample_price_df_50: pd.DataFrame) -> None:
        engine = OptionsEngine()
        signal = engine.analyze(1, "BBCA", sample_price_df_50)
        assert "IDX" in signal.reasoning or "not available" in signal.reasoning.lower()

    def test_analyze_data_quality_stub(self, sample_price_df_50: pd.DataFrame) -> None:
        engine = OptionsEngine()
        signal = engine.analyze(1, "BBCA", sample_price_df_50)
        assert signal.data_quality.get("stub") is True

    def test_analyze_data_quality_todo(self, sample_price_df_50: pd.DataFrame) -> None:
        engine = OptionsEngine()
        signal = engine.analyze(1, "BBCA", sample_price_df_50)
        assert "todo" in signal.data_quality
        assert "Deribit" in signal.data_quality["todo"]

    def test_analyze_with_empty_df(self, empty_price_df: pd.DataFrame) -> None:
        engine = OptionsEngine()
        signal = engine.analyze(1, "BBCA", empty_price_df)
        assert signal.score == 0.0
        assert signal.confidence == 0.0
