"""Tests for SentimentEngine."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd
import pytest

from src.engines.sentiment import SentimentEngine


@pytest.fixture()
def empty_df() -> pd.DataFrame:
    return pd.DataFrame(columns=["open", "high", "low", "close", "volume"], dtype=float)


@dataclass
class FakeSentimentSnapshot:
    """Duck-typed SentimentSnapshot for testing."""

    fear_greed_value: float
    fear_greed_classification: str
    reddit_posts: list[Any] | None = None


class TestSentimentEngineContract:
    """Test that SentimentEngine follows the BaseEngine contract."""

    def test_category_property(self) -> None:
        engine = SentimentEngine()
        assert engine.category == "sentiment"

    def test_supports_stocks(self) -> None:
        assert SentimentEngine().supports_stocks is True

    def test_supports_crypto(self) -> None:
        assert SentimentEngine().supports_crypto is True


class TestSentimentEngineAnalyze:
    """Test analyze() output."""

    def test_analyze_with_fear_greed_and_reddit_returns_valid_score(
        self, empty_df: pd.DataFrame
    ) -> None:
        """Test 10: analyze() with Fear & Greed + Reddit data returns valid score."""
        snapshot = FakeSentimentSnapshot(
            fear_greed_value=45.0,
            fear_greed_classification="Fear",
            reddit_posts=[{"score": 100}, {"score": 200}, {"score": 50}],
        )
        engine = SentimentEngine(sentiment_data=snapshot)
        signal = engine.analyze(asset_id=1, asset_symbol="BTC", df=empty_df)

        assert signal.category == "sentiment"
        assert -1.0 <= signal.score <= 1.0
        assert 0.0 <= signal.confidence <= 1.0

    def test_analyze_with_fear_greed_only_returns_reduced_confidence(
        self, empty_df: pd.DataFrame
    ) -> None:
        """Test 11: analyze() with Fear & Greed only (no Reddit) returns lower confidence (per D-12)."""
        snapshot_no_reddit = FakeSentimentSnapshot(
            fear_greed_value=50.0,
            fear_greed_classification="Neutral",
            reddit_posts=None,
        )
        snapshot_with_reddit = FakeSentimentSnapshot(
            fear_greed_value=50.0,
            fear_greed_classification="Neutral",
            reddit_posts=[{"score": 100}, {"score": 150}],
        )

        engine_no_reddit = SentimentEngine(sentiment_data=snapshot_no_reddit)
        engine_with_reddit = SentimentEngine(sentiment_data=snapshot_with_reddit)

        signal_no_reddit = engine_no_reddit.analyze(
            asset_id=1, asset_symbol="BTC", df=empty_df
        )
        signal_with_reddit = engine_with_reddit.analyze(
            asset_id=1, asset_symbol="BTC", df=empty_df
        )

        # Without Reddit, confidence should be lower (reduced by 40%)
        assert signal_no_reddit.confidence < signal_with_reddit.confidence

    def test_analyze_with_none_sentiment_data_returns_zero(
        self, empty_df: pd.DataFrame
    ) -> None:
        """Test 12: analyze() with sentiment_data=None returns score=0, confidence=0."""
        engine = SentimentEngine(sentiment_data=None)
        signal = engine.analyze(asset_id=1, asset_symbol="BTC", df=empty_df)

        assert signal.score == 0.0
        assert signal.confidence == 0.0

    def test_extreme_fear_maps_to_positive_score_contrarian(
        self, empty_df: pd.DataFrame
    ) -> None:
        """Test 13: Fear & Greed value 10 (Extreme Fear) maps to positive score (contrarian bullish)."""
        snapshot = FakeSentimentSnapshot(
            fear_greed_value=10.0,
            fear_greed_classification="Extreme Fear",
            reddit_posts=None,
        )
        engine = SentimentEngine(sentiment_data=snapshot)
        signal = engine.analyze(asset_id=1, asset_symbol="BTC", df=empty_df)

        # Extreme Fear (contrarian) should be bullish -> positive score
        assert signal.score > 0.0

    def test_extreme_greed_maps_to_negative_score_contrarian(
        self, empty_df: pd.DataFrame
    ) -> None:
        """Fear & Greed value 90 (Extreme Greed) maps to negative score (contrarian bearish)."""
        snapshot = FakeSentimentSnapshot(
            fear_greed_value=90.0,
            fear_greed_classification="Extreme Greed",
            reddit_posts=None,
        )
        engine = SentimentEngine(sentiment_data=snapshot)
        signal = engine.analyze(asset_id=1, asset_symbol="BTC", df=empty_df)

        assert signal.score < 0.0

    def test_neutral_fear_greed_produces_low_absolute_score(
        self, empty_df: pd.DataFrame
    ) -> None:
        """Neutral F&G (50) should produce near-zero score."""
        snapshot = FakeSentimentSnapshot(
            fear_greed_value=50.0,
            fear_greed_classification="Neutral",
            reddit_posts=None,
        )
        engine = SentimentEngine(sentiment_data=snapshot)
        signal = engine.analyze(asset_id=1, asset_symbol="BTC", df=empty_df)

        assert abs(signal.score) < 0.3

    def test_analyze_does_not_raise(self, empty_df: pd.DataFrame) -> None:
        """analyze() must never raise."""
        # Pass object with invalid attributes
        engine = SentimentEngine(sentiment_data=object())
        signal = engine.analyze(asset_id=1, asset_symbol="BTC", df=empty_df)
        assert signal.category == "sentiment"
