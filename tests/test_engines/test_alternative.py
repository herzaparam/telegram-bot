"""Tests for AlternativeDataEngine."""

from __future__ import annotations

import pandas as pd
import pytest

from src.engines.base import Signal


@pytest.fixture()
def empty_df() -> pd.DataFrame:
    return pd.DataFrame(columns=["open", "high", "low", "close", "volume"], dtype=float)


class TestAlternativeDataEngineContract:
    """Test that AlternativeDataEngine follows the BaseEngine contract."""

    def test_category_property(self) -> None:
        from src.engines.alternative import AlternativeDataEngine

        engine = AlternativeDataEngine()
        assert engine.category == "alternative"

    def test_supports_stocks_is_false(self) -> None:
        from src.engines.alternative import AlternativeDataEngine

        assert AlternativeDataEngine().supports_stocks is False

    def test_supports_crypto_is_true(self) -> None:
        from src.engines.alternative import AlternativeDataEngine

        assert AlternativeDataEngine().supports_crypto is True


class TestAlternativeDataEngineAnalyze:
    """Test analyze() output validity."""

    def test_analyze_with_none_data_returns_zero(self, empty_df: pd.DataFrame) -> None:
        from src.engines.alternative import AlternativeDataEngine

        engine = AlternativeDataEngine(github_data=None)
        signal = engine.analyze(1, "BTC", empty_df)
        assert isinstance(signal, Signal)
        assert signal.score == 0.0
        assert signal.confidence == 0.0
        assert signal.category == "alternative"

    def test_analyze_high_weekly_commits_positive(self, empty_df: pd.DataFrame) -> None:
        from src.engines.alternative import AlternativeDataEngine

        data = {"weekly_commits": 60, "stars": 80000, "forks": 35000, "open_issues": 850}
        engine = AlternativeDataEngine(github_data=data)
        signal = engine.analyze(1, "BTC", empty_df)
        assert signal.score > 0.0
        assert signal.confidence > 0.0

    def test_analyze_zero_commits_negative(self, empty_df: pd.DataFrame) -> None:
        from src.engines.alternative import AlternativeDataEngine

        data = {"weekly_commits": 0, "stars": 500, "forks": 100, "open_issues": 50}
        engine = AlternativeDataEngine(github_data=data)
        signal = engine.analyze(1, "BTC", empty_df)
        assert signal.score < 0.0

    def test_analyze_declining_activity_negative(self, empty_df: pd.DataFrame) -> None:
        from src.engines.alternative import AlternativeDataEngine

        data = {
            "weekly_commits": 10,
            "weekly_commits_prev": 50,  # Falling from 50 to 10
            "stars": 80000,
            "forks": 35000,
            "open_issues": 850,
        }
        engine = AlternativeDataEngine(github_data=data)
        signal = engine.analyze(1, "BTC", empty_df)
        assert signal.score < 0.0

    def test_analyze_rising_activity_positive(self, empty_df: pd.DataFrame) -> None:
        from src.engines.alternative import AlternativeDataEngine

        data = {
            "weekly_commits": 60,
            "weekly_commits_prev": 30,  # Rising from 30 to 60
            "stars": 80000,
            "forks": 35000,
            "open_issues": 850,
        }
        engine = AlternativeDataEngine(github_data=data)
        signal = engine.analyze(1, "BTC", empty_df)
        assert signal.score > 0.0

    def test_analyze_score_capped_at_bounds(self, empty_df: pd.DataFrame) -> None:
        from src.engines.alternative import AlternativeDataEngine

        data = {"weekly_commits": 200, "stars": 200000, "forks": 100000, "open_issues": 10}
        engine = AlternativeDataEngine(github_data=data)
        signal = engine.analyze(1, "BTC", empty_df)
        assert -1.0 <= signal.score <= 1.0
        assert 0.0 <= signal.confidence <= 1.0

    def test_analyze_indicators_contain_github_data(self, empty_df: pd.DataFrame) -> None:
        from src.engines.alternative import AlternativeDataEngine

        data = {"weekly_commits": 40, "stars": 80000, "forks": 35000, "open_issues": 850}
        engine = AlternativeDataEngine(github_data=data)
        signal = engine.analyze(1, "BTC", empty_df)
        assert "weekly_commits" in signal.indicators
        assert "stars" in signal.indicators
        assert "source" in signal.indicators
        assert signal.indicators["source"] == "github"

    def test_analyze_confidence_is_025(self, empty_df: pd.DataFrame) -> None:
        """AlternativeDataEngine confidence is 0.25 (supplementary data)."""
        from src.engines.alternative import AlternativeDataEngine

        data = {"weekly_commits": 40, "stars": 80000, "forks": 35000, "open_issues": 850}
        engine = AlternativeDataEngine(github_data=data)
        signal = engine.analyze(1, "BTC", empty_df)
        assert signal.confidence == 0.25

    def test_analyze_never_raises(self, empty_df: pd.DataFrame) -> None:
        """analyze() must never raise per BaseEngine contract."""
        from src.engines.alternative import AlternativeDataEngine

        engine = AlternativeDataEngine(github_data={"bad": "data"})
        signal = engine.analyze(1, "BTC", empty_df)
        assert isinstance(signal, Signal)
