"""Tests for MacroEngine."""

from __future__ import annotations

import pandas as pd
import pytest

from src.engines.macro import (
    MacroEngine,
    _cpi_to_score,
    _dxy_to_score,
    _fed_rate_to_score,
    _usd_idr_to_score,
)


@pytest.fixture()
def empty_df() -> pd.DataFrame:
    return pd.DataFrame(columns=["open", "high", "low", "close", "volume"], dtype=float)


@pytest.fixture()
def full_macro_data() -> dict[str, float]:
    return {
        "fed_funds_rate": 4.5,
        "cpi": 3.2,
        "dxy": 103.0,
        "usd_idr": 15500.0,
    }


class TestMacroEngineContract:
    """Test that MacroEngine follows the BaseEngine contract."""

    def test_category_property(self) -> None:
        engine = MacroEngine()
        assert engine.category == "macro"

    def test_supports_stocks(self) -> None:
        assert MacroEngine().supports_stocks is True

    def test_supports_crypto(self) -> None:
        assert MacroEngine().supports_crypto is True


class TestMacroEngineAnalyze:
    """Test analyze() output validity."""

    def test_analyze_with_full_macro_data_returns_valid_score(
        self,
        empty_df: pd.DataFrame,
        full_macro_data: dict[str, float],
    ) -> None:
        """Test 6: analyze() with full macro_data dict returns valid score."""
        engine = MacroEngine(macro_data=full_macro_data)
        signal = engine.analyze(asset_id=1, asset_symbol="BBCA", df=empty_df)

        assert signal.category == "macro"
        assert -1.0 <= signal.score <= 1.0
        assert 0.0 <= signal.confidence <= 1.0
        assert signal.reasoning != ""

    def test_analyze_with_none_macro_data_returns_zero(
        self, empty_df: pd.DataFrame
    ) -> None:
        """Test 7: analyze() with macro_data=None returns score=0, confidence=0."""
        engine = MacroEngine(macro_data=None)
        signal = engine.analyze(asset_id=1, asset_symbol="BBCA", df=empty_df)

        assert signal.score == 0.0
        assert signal.confidence == 0.0

    def test_analyze_with_empty_macro_data_returns_zero(
        self, empty_df: pd.DataFrame
    ) -> None:
        """analyze() with empty dict returns score=0, confidence=0."""
        engine = MacroEngine(macro_data={})
        signal = engine.analyze(asset_id=1, asset_symbol="BBCA", df=empty_df)

        assert signal.score == 0.0
        assert signal.confidence == 0.0

    def test_analyze_stock_reasoning_mentions_idx_factors(
        self,
        empty_df: pd.DataFrame,
        full_macro_data: dict[str, float],
    ) -> None:
        """Test 8: analyze() reasoning mentions IDX-relevant factors for stocks."""
        engine = MacroEngine(macro_data=full_macro_data)
        signal = engine.analyze(asset_id=1, asset_symbol="BBCA", df=empty_df)

        # For stock symbol, reasoning should mention rupiah or IDX factors
        assert any(
            keyword in signal.reasoning.lower()
            for keyword in ["rupiah", "idr", "idx", "usd_idr"]
        )

    def test_analyze_crypto_reasoning_mentions_global_factors(
        self,
        empty_df: pd.DataFrame,
        full_macro_data: dict[str, float],
    ) -> None:
        """Test 8: analyze() reasoning mentions global factors for crypto."""
        engine = MacroEngine(macro_data=full_macro_data)
        signal = engine.analyze(asset_id=2, asset_symbol="BTC", df=empty_df)

        # For crypto, reasoning should mention Fed or DXY
        assert any(
            keyword in signal.reasoning.lower()
            for keyword in ["fed", "dxy", "dollar", "global"]
        )

    def test_analyze_does_not_raise(self, empty_df: pd.DataFrame) -> None:
        """analyze() must never raise."""
        engine = MacroEngine(macro_data={"invalid_key": "not_a_number"})  # type: ignore[dict-item]
        signal = engine.analyze(asset_id=1, asset_symbol="BBCA", df=empty_df)
        assert signal.category == "macro"


class TestFedRateZoneMapper:
    """Test 9: Fed rate zone mapper edge cases."""

    def test_fed_rate_none_returns_zero(self) -> None:
        assert _fed_rate_to_score(None) == 0.0

    def test_fed_rate_zero_is_accommodative(self) -> None:
        assert _fed_rate_to_score(0.0) == 0.6

    def test_fed_rate_low_is_slightly_bullish(self) -> None:
        # 1.0 <= rate < 3.0 -> +0.2
        assert _fed_rate_to_score(2.0) == 0.2

    def test_fed_rate_high_is_slightly_bearish(self) -> None:
        # 3.0 <= rate < 5.0 -> -0.2
        assert _fed_rate_to_score(4.5) == -0.2

    def test_fed_rate_very_high_is_bearish(self) -> None:
        # 5.0 <= rate < 7.0 -> -0.5
        assert _fed_rate_to_score(6.0) == -0.5

    def test_fed_rate_extreme_is_very_bearish(self) -> None:
        # rate >= 7.0 -> -0.8
        assert _fed_rate_to_score(8.0) == -0.8

    def test_fed_rate_negative_value(self) -> None:
        # Negative rate (theoretical) -> accommodative -> +0.6
        assert _fed_rate_to_score(-0.5) == 0.6


class TestCpiZoneMapper:
    def test_cpi_none_returns_zero(self) -> None:
        assert _cpi_to_score(None) == 0.0

    def test_cpi_very_low_is_bullish(self) -> None:
        # CPI < 2.0 -> +0.5
        assert _cpi_to_score(1.5) == 0.5

    def test_cpi_high_is_bearish(self) -> None:
        # CPI >= 7.0 -> -0.8
        assert _cpi_to_score(8.0) == -0.8


class TestDxyZoneMapper:
    def test_dxy_none_returns_zero(self) -> None:
        assert _dxy_to_score(None) == 0.0

    def test_dxy_weak_is_bullish(self) -> None:
        # DXY < 90 -> +0.5
        assert _dxy_to_score(85.0) == 0.5

    def test_dxy_strong_is_bearish(self) -> None:
        # DXY >= 110 -> -0.8
        assert _dxy_to_score(115.0) == -0.8


class TestUsdIdrZoneMapper:
    def test_usd_idr_none_returns_zero(self) -> None:
        assert _usd_idr_to_score(None) == 0.0

    def test_usd_idr_strong_rupiah_is_bullish(self) -> None:
        # < 14000 -> +0.5
        assert _usd_idr_to_score(13000.0) == 0.5

    def test_usd_idr_weak_rupiah_is_bearish(self) -> None:
        # >= 17000 -> -0.8
        assert _usd_idr_to_score(18000.0) == -0.8
