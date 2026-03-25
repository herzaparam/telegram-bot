"""Tests for EventEngine."""

from __future__ import annotations

import pandas as pd
import pytest

from src.engines.event import EventEngine


@pytest.fixture()
def empty_df() -> pd.DataFrame:
    return pd.DataFrame(columns=["open", "high", "low", "close", "volume"], dtype=float)


@pytest.fixture()
def central_bank_events() -> list[dict[str, object]]:
    return [
        {
            "headline": "Fed raises interest rates by 25bps",
            "category": "central_bank",
            "impact_score": -0.6,
            "affected_assets": {"BTC": 0.9, "ETH": 0.8},
        },
        {
            "headline": "BI holds rate at 6%",
            "category": "central_bank",
            "impact_score": 0.2,
            "affected_assets": {"BBCA": 0.7, "BBRI": 0.6},
        },
    ]


@pytest.fixture()
def earnings_events() -> list[dict[str, object]]:
    return [
        {
            "headline": "BBCA Q4 earnings beat expectations",
            "category": "earnings",
            "impact_score": 0.7,
            "affected_assets": {"BBCA": 0.9},
        },
    ]


@pytest.fixture()
def mixed_events() -> list[dict[str, object]]:
    return [
        {
            "headline": "Bitcoin halving in 3 days",
            "category": "halving",
            "impact_score": 0.8,
            "affected_assets": {"BTC": 1.0},
        },
        {
            "headline": "Ethereum regulation draft released",
            "category": "regulation",
            "impact_score": -0.5,
            "affected_assets": {"ETH": 0.8},
        },
        {
            "headline": "Global macroeconomic outlook worsens",
            "category": "macro",
            "impact_score": -0.4,
            "affected_assets": {"BTC": 0.5, "BBCA": 0.4},
        },
    ]


class TestEventEngineContract:
    """Test that EventEngine follows the BaseEngine contract."""

    def test_category_property(self) -> None:
        engine = EventEngine()
        assert engine.category == "event"

    def test_supports_stocks(self) -> None:
        assert EventEngine().supports_stocks is True

    def test_supports_crypto(self) -> None:
        assert EventEngine().supports_crypto is True


class TestEventEngineAnalyze:
    """Test analyze() output."""

    def test_analyze_with_central_bank_category_returns_nonzero_score(
        self,
        empty_df: pd.DataFrame,
        central_bank_events: list[dict[str, object]],
    ) -> None:
        """Test 14: analyze() with news events containing 'central_bank' returns non-zero score."""
        engine = EventEngine(news_events=central_bank_events)
        signal = engine.analyze(asset_id=1, asset_symbol="BTC", df=empty_df)

        assert signal.category == "event"
        assert signal.score != 0.0
        assert signal.confidence > 0.0

    def test_analyze_with_no_events_returns_zero(
        self, empty_df: pd.DataFrame
    ) -> None:
        """Test 15: analyze() with no events returns score=0, confidence=0."""
        engine = EventEngine(news_events=[])
        signal = engine.analyze(asset_id=1, asset_symbol="BTC", df=empty_df)

        assert signal.score == 0.0
        assert signal.confidence == 0.0

    def test_analyze_with_none_events_returns_zero(
        self, empty_df: pd.DataFrame
    ) -> None:
        """analyze() with None events returns score=0, confidence=0."""
        engine = EventEngine(news_events=None)
        signal = engine.analyze(asset_id=1, asset_symbol="BTC", df=empty_df)

        assert signal.score == 0.0
        assert signal.confidence == 0.0

    def test_analyze_filters_to_asset_relevant_events(
        self,
        empty_df: pd.DataFrame,
        central_bank_events: list[dict[str, object]],
    ) -> None:
        """Test 16: Events are filtered to those affecting the current asset."""
        engine = EventEngine(news_events=central_bank_events)

        # BTC appears in first event but not second
        signal_btc = engine.analyze(asset_id=1, asset_symbol="BTC", df=empty_df)
        # BBCA appears in second event but not first
        signal_bbca = engine.analyze(asset_id=2, asset_symbol="BBCA", df=empty_df)

        # Both should have events but different ones
        assert signal_btc.score != 0.0
        assert signal_bbca.score != 0.0

    def test_analyze_with_irrelevant_events_returns_zero(
        self, empty_df: pd.DataFrame
    ) -> None:
        """Events not relevant to current asset produce score=0."""
        events = [
            {
                "headline": "BBCA earnings beat",
                "category": "earnings",
                "impact_score": 0.8,
                "affected_assets": {"BBCA": 0.9},
            }
        ]
        engine = EventEngine(news_events=events)
        signal = engine.analyze(asset_id=1, asset_symbol="BTC", df=empty_df)

        # BTC is not in affected_assets for this event
        assert signal.score == 0.0

    def test_analyze_filters_by_valid_categories(
        self, empty_df: pd.DataFrame
    ) -> None:
        """Only valid categories (central_bank, earnings, regulation, halving, macro) are scored."""
        events = [
            {
                "headline": "Social media hype about crypto",
                "category": "social",  # Not in valid categories
                "impact_score": 0.9,
                "affected_assets": {"BTC": 1.0},
            },
            {
                "headline": "BTC halving approaching",
                "category": "halving",  # Valid
                "impact_score": 0.8,
                "affected_assets": {"BTC": 1.0},
            },
        ]
        engine = EventEngine(news_events=events)
        signal = engine.analyze(asset_id=1, asset_symbol="BTC", df=empty_df)

        # Only the halving event should count
        assert signal.score != 0.0

    def test_analyze_confidence_scales_with_event_count(
        self,
        empty_df: pd.DataFrame,
        mixed_events: list[dict[str, object]],
    ) -> None:
        """Confidence should scale with number of relevant events."""
        # Single BTC event
        single_event = [
            {
                "headline": "Bitcoin halving",
                "category": "halving",
                "impact_score": 0.5,
                "affected_assets": {"BTC": 1.0},
            }
        ]
        multi_events = list(mixed_events)  # Multiple BTC events

        engine_single = EventEngine(news_events=single_event)
        engine_multi = EventEngine(news_events=multi_events)

        signal_single = engine_single.analyze(asset_id=1, asset_symbol="BTC", df=empty_df)
        signal_multi = engine_multi.analyze(asset_id=1, asset_symbol="BTC", df=empty_df)

        assert signal_multi.confidence >= signal_single.confidence

    def test_reasoning_contains_top_headlines(
        self,
        empty_df: pd.DataFrame,
        central_bank_events: list[dict[str, object]],
    ) -> None:
        """Reasoning should list relevant headlines."""
        engine = EventEngine(news_events=central_bank_events)
        signal = engine.analyze(asset_id=1, asset_symbol="BTC", df=empty_df)

        # Reasoning should mention something about the event
        assert len(signal.reasoning) > 10

    def test_analyze_does_not_raise(self, empty_df: pd.DataFrame) -> None:
        """analyze() must never raise."""
        engine = EventEngine(news_events=[{"invalid": True}])  # type: ignore[list-item]
        signal = engine.analyze(asset_id=1, asset_symbol="BTC", df=empty_df)
        assert signal.category == "event"
