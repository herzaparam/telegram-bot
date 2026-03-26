"""Tests for OnChainEngine."""

from __future__ import annotations

import pandas as pd
import pytest

from src.engines.base import Signal


@pytest.fixture()
def empty_df() -> pd.DataFrame:
    return pd.DataFrame(columns=["open", "high", "low", "close", "volume"], dtype=float)


class TestOnChainEngineContract:
    """Test that OnChainEngine follows the BaseEngine contract."""

    def test_category_property(self) -> None:
        from src.engines.onchain import OnChainEngine

        engine = OnChainEngine()
        assert engine.category == "onchain"

    def test_supports_stocks_is_false(self) -> None:
        from src.engines.onchain import OnChainEngine

        assert OnChainEngine().supports_stocks is False

    def test_supports_crypto_is_true(self) -> None:
        from src.engines.onchain import OnChainEngine

        assert OnChainEngine().supports_crypto is True


class TestOnChainEngineAnalyze:
    """Test analyze() output validity."""

    def test_analyze_with_none_data_returns_zero(self, empty_df: pd.DataFrame) -> None:
        from src.engines.onchain import OnChainEngine

        engine = OnChainEngine(onchain_data=None)
        signal = engine.analyze(1, "BTC", empty_df)
        assert isinstance(signal, Signal)
        assert signal.score == 0.0
        assert signal.confidence == 0.0
        assert signal.category == "onchain"

    def test_analyze_with_empty_data_returns_zero(self, empty_df: pd.DataFrame) -> None:
        from src.engines.onchain import OnChainEngine

        engine = OnChainEngine(onchain_data={})
        signal = engine.analyze(1, "BTC", empty_df)
        assert signal.score == 0.0
        assert signal.confidence == 0.0

    def test_analyze_with_rising_tvl_returns_positive(self, empty_df: pd.DataFrame) -> None:
        from src.engines.onchain import OnChainEngine

        data = {
            "tvl_current": 1_200_000_000.0,
            "tvl_7d_change": 0.10,  # 10% rise
            "tvl_30d_change": 0.15,  # 15% rise (confirms 7d)
            "source": "defillama",
        }
        engine = OnChainEngine(onchain_data=data)
        signal = engine.analyze(1, "BTC", empty_df)
        assert signal.score > 0.0
        assert signal.confidence > 0.0
        assert signal.category == "onchain"

    def test_analyze_with_falling_tvl_returns_negative(self, empty_df: pd.DataFrame) -> None:
        from src.engines.onchain import OnChainEngine

        data = {
            "tvl_current": 800_000_000.0,
            "tvl_7d_change": -0.12,  # 12% drop
            "tvl_30d_change": -0.20,  # 20% drop (confirms 7d)
            "source": "defillama",
        }
        engine = OnChainEngine(onchain_data=data)
        signal = engine.analyze(1, "BTC", empty_df)
        assert signal.score < 0.0

    def test_analyze_with_strong_tvl_rise_higher_than_moderate(self, empty_df: pd.DataFrame) -> None:
        from src.engines.onchain import OnChainEngine

        moderate_data = {"tvl_current": 1e9, "tvl_7d_change": 0.06, "tvl_30d_change": 0.06, "source": "defillama"}
        strong_data = {"tvl_current": 1e9, "tvl_7d_change": 0.15, "tvl_30d_change": 0.15, "source": "defillama"}

        moderate_signal = OnChainEngine(onchain_data=moderate_data).analyze(1, "BTC", empty_df)
        strong_signal = OnChainEngine(onchain_data=strong_data).analyze(1, "BTC", empty_df)
        assert strong_signal.score > moderate_signal.score

    def test_analyze_with_exchange_flow_data(self, empty_df: pd.DataFrame) -> None:
        from src.engines.onchain import OnChainEngine

        data = {
            "tvl_current": 1e9,
            "tvl_7d_change": 0.06,
            "tvl_30d_change": 0.06,
            "exchange_outflow": 100_000.0,
            "exchange_inflow": 50_000.0,
            "source": "defillama",
        }
        engine = OnChainEngine(onchain_data=data)
        signal = engine.analyze(1, "BTC", empty_df)
        # Net outflow is bullish
        assert signal.score > 0.0

    def test_analyze_score_capped_at_bounds(self, empty_df: pd.DataFrame) -> None:
        from src.engines.onchain import OnChainEngine

        data = {
            "tvl_current": 1e9,
            "tvl_7d_change": 0.50,
            "tvl_30d_change": 0.50,
            "exchange_outflow": 1_000_000.0,
            "exchange_inflow": 0.0,
            "source": "defillama",
        }
        engine = OnChainEngine(onchain_data=data)
        signal = engine.analyze(1, "BTC", empty_df)
        assert -1.0 <= signal.score <= 1.0
        assert 0.0 <= signal.confidence <= 1.0

    def test_analyze_indicators_contain_tvl_data(self, empty_df: pd.DataFrame) -> None:
        from src.engines.onchain import OnChainEngine

        data = {"tvl_current": 1e9, "tvl_7d_change": 0.06, "tvl_30d_change": 0.06, "source": "defillama"}
        engine = OnChainEngine(onchain_data=data)
        signal = engine.analyze(1, "BTC", empty_df)
        assert "tvl_current" in signal.indicators
        assert "source" in signal.indicators

    def test_analyze_never_raises(self, empty_df: pd.DataFrame) -> None:
        """analyze() must never raise per BaseEngine contract."""
        from src.engines.onchain import OnChainEngine

        # Even with garbage data
        engine = OnChainEngine(onchain_data={"bad_key": "not_a_number"})
        signal = engine.analyze(1, "BTC", empty_df)
        assert isinstance(signal, Signal)
