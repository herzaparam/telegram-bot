"""Tests for src/engines/game_theory.py — GameTheoryEngine stub."""

import pandas as pd
import pytest

from src.engines.base import BaseEngine, Signal
from src.engines.game_theory import GameTheoryEngine


class TestGameTheoryEngine:
    """Tests for the GameTheoryEngine stub."""

    def test_inherits_base_engine(self) -> None:
        engine = GameTheoryEngine()
        assert isinstance(engine, BaseEngine)

    def test_category_is_game_theory(self) -> None:
        engine = GameTheoryEngine()
        assert engine.category == "game_theory"

    def test_supports_stocks_true(self) -> None:
        engine = GameTheoryEngine()
        assert engine.supports_stocks is True

    def test_supports_crypto_true(self) -> None:
        engine = GameTheoryEngine()
        assert engine.supports_crypto is True

    def test_analyze_returns_signal(self, sample_price_df_50: pd.DataFrame) -> None:
        engine = GameTheoryEngine()
        signal = engine.analyze(1, "BBCA", sample_price_df_50)
        assert isinstance(signal, Signal)

    def test_analyze_returns_zero_score(self, sample_price_df_50: pd.DataFrame) -> None:
        engine = GameTheoryEngine()
        signal = engine.analyze(1, "BBCA", sample_price_df_50)
        assert signal.score == 0.0

    def test_analyze_returns_zero_confidence(self, sample_price_df_50: pd.DataFrame) -> None:
        engine = GameTheoryEngine()
        signal = engine.analyze(1, "BBCA", sample_price_df_50)
        assert signal.confidence == 0.0

    def test_analyze_category_in_signal(self, sample_price_df_50: pd.DataFrame) -> None:
        engine = GameTheoryEngine()
        signal = engine.analyze(1, "BBCA", sample_price_df_50)
        assert signal.category == "game_theory"

    def test_analyze_reasoning_mentions_order_book(self, sample_price_df_50: pd.DataFrame) -> None:
        engine = GameTheoryEngine()
        signal = engine.analyze(1, "BBCA", sample_price_df_50)
        assert "order book" in signal.reasoning.lower() or "not available" in signal.reasoning.lower()

    def test_analyze_data_quality_stub(self, sample_price_df_50: pd.DataFrame) -> None:
        engine = GameTheoryEngine()
        signal = engine.analyze(1, "BBCA", sample_price_df_50)
        assert signal.data_quality.get("stub") is True

    def test_analyze_data_quality_todo(self, sample_price_df_50: pd.DataFrame) -> None:
        engine = GameTheoryEngine()
        signal = engine.analyze(1, "BBCA", sample_price_df_50)
        assert "todo" in signal.data_quality
        assert "Binance" in signal.data_quality["todo"]

    def test_analyze_with_empty_df(self, empty_price_df: pd.DataFrame) -> None:
        engine = GameTheoryEngine()
        signal = engine.analyze(1, "BBCA", empty_price_df)
        assert signal.score == 0.0
        assert signal.confidence == 0.0
