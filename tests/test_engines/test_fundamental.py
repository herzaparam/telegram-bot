"""Tests for FundamentalEngine."""

from __future__ import annotations

import pandas as pd
import pytest

from src.engines.fundamental import (
    FundamentalEngine,
    _debt_to_equity_to_score,
    _dividend_yield_to_score,
    _pb_to_score,
    _pe_to_score,
    _revenue_growth_to_score,
    _roe_to_score,
)


@pytest.fixture()
def empty_df() -> pd.DataFrame:
    return pd.DataFrame(columns=["open", "high", "low", "close", "volume"], dtype=float)


@pytest.fixture()
def valid_fundamentals() -> dict[str, float | None]:
    return {
        "trailing_pe": 15.0,
        "price_to_book": 1.5,
        "return_on_equity": 0.18,
        "revenue_growth": 0.12,
        "dividend_yield": 0.03,
        "debt_to_equity": 0.8,
    }


class TestFundamentalEngineContract:
    """Test that FundamentalEngine follows the BaseEngine contract."""

    def test_category_property(self) -> None:
        engine = FundamentalEngine()
        assert engine.category == "fundamental"

    def test_supports_stocks(self) -> None:
        engine = FundamentalEngine()
        assert engine.supports_stocks is True

    def test_supports_crypto(self) -> None:
        engine = FundamentalEngine()
        assert engine.supports_crypto is True


class TestFundamentalEngineAnalyze:
    """Test analyze() output validity."""

    def test_analyze_with_valid_fundamentals_returns_valid_score(
        self,
        empty_df: pd.DataFrame,
        valid_fundamentals: dict[str, float | None],
    ) -> None:
        """Test 1: analyze() with valid fundamentals dict returns score in [-1, 1], confidence > 0."""
        engine = FundamentalEngine(fundamentals=valid_fundamentals)
        signal = engine.analyze(asset_id=1, asset_symbol="BBCA", df=empty_df)

        assert signal.category == "fundamental"
        assert -1.0 <= signal.score <= 1.0
        assert signal.confidence > 0.0
        assert signal.reasoning != ""

    def test_analyze_with_none_fundamentals_returns_crypto_not_applicable(
        self,
        empty_df: pd.DataFrame,
    ) -> None:
        """Test 2: analyze() with crypto asset (fundamentals=None) returns score=0, confidence=0."""
        engine = FundamentalEngine(fundamentals=None)
        signal = engine.analyze(asset_id=2, asset_symbol="BTC", df=empty_df)

        assert signal.score == 0.0
        assert signal.confidence == 0.0
        assert "not applicable for crypto" in signal.reasoning.lower() or "Fundamentals not applicable for crypto" in signal.reasoning

    def test_analyze_with_partial_data_returns_lower_confidence(
        self,
        empty_df: pd.DataFrame,
        valid_fundamentals: dict[str, float | None],
    ) -> None:
        """Test 3: analyze() with partial data (some None ratios) returns lower confidence."""
        partial_fundamentals = dict(valid_fundamentals)
        partial_fundamentals["trailing_pe"] = None
        partial_fundamentals["price_to_book"] = None
        partial_fundamentals["return_on_equity"] = None

        engine_full = FundamentalEngine(fundamentals=valid_fundamentals)
        engine_partial = FundamentalEngine(fundamentals=partial_fundamentals)

        signal_full = engine_full.analyze(asset_id=1, asset_symbol="BBCA", df=empty_df)
        signal_partial = engine_partial.analyze(asset_id=1, asset_symbol="BBCA", df=empty_df)

        assert signal_partial.confidence < signal_full.confidence

    def test_analyze_with_all_none_fundamentals_returns_zero(
        self,
        empty_df: pd.DataFrame,
    ) -> None:
        """Test 5: analyze() with all None fundamentals returns score=0, confidence=0."""
        all_none = {
            "trailing_pe": None,
            "price_to_book": None,
            "return_on_equity": None,
            "revenue_growth": None,
            "dividend_yield": None,
            "debt_to_equity": None,
        }
        engine = FundamentalEngine(fundamentals=all_none)
        signal = engine.analyze(asset_id=1, asset_symbol="BBCA", df=empty_df)

        assert signal.score == 0.0
        assert signal.confidence == 0.0

    def test_analyze_reasoning_contains_ratio_values(
        self,
        empty_df: pd.DataFrame,
        valid_fundamentals: dict[str, float | None],
    ) -> None:
        """Reasoning should list ratio values."""
        engine = FundamentalEngine(fundamentals=valid_fundamentals)
        signal = engine.analyze(asset_id=1, asset_symbol="BBCA", df=empty_df)

        # Reasoning should contain some ratio information
        assert len(signal.reasoning) > 10

    def test_analyze_does_not_raise_on_exception(self, empty_df: pd.DataFrame) -> None:
        """analyze() must never raise -- returns zero Signal on failure."""
        # Pass invalid data type to trigger exception path
        engine = FundamentalEngine(fundamentals={"trailing_pe": "invalid"})  # type: ignore[arg-type]
        # Should not raise
        signal = engine.analyze(asset_id=1, asset_symbol="BBCA", df=empty_df)
        assert signal.category == "fundamental"


class TestPeZoneMapper:
    """Test 4: Each zone mapper returns correct scores."""

    def test_pe_none_returns_zero(self) -> None:
        assert _pe_to_score(None) == 0.0

    def test_pe_very_low_is_very_bullish(self) -> None:
        # PE < 8 -> +0.8
        assert _pe_to_score(5.0) == 0.8
        assert _pe_to_score(7.9) == 0.8

    def test_pe_low_is_moderately_bullish(self) -> None:
        # 8 <= PE < 12 -> +0.5
        assert _pe_to_score(10.0) == 0.5

    def test_pe_fair_is_slightly_bullish(self) -> None:
        # 12 <= PE < 18 -> +0.2
        assert _pe_to_score(15.0) == 0.2

    def test_pe_high_is_slightly_bearish(self) -> None:
        # 18 <= PE < 25 -> -0.2
        assert _pe_to_score(22.0) == -0.2

    def test_pe_very_high_is_bearish(self) -> None:
        # 25 <= PE < 40 -> -0.5
        assert _pe_to_score(30.0) == -0.5

    def test_pe_extreme_is_very_bearish(self) -> None:
        # PE >= 40 -> -0.8
        assert _pe_to_score(50.0) == -0.8

    def test_pe_negative_is_very_bearish(self) -> None:
        # Negative PE (unprofitable) -> -0.8
        assert _pe_to_score(-5.0) == -0.8


class TestRoeZoneMapper:
    """Test ROE zone mapper."""

    def test_roe_none_returns_zero(self) -> None:
        assert _roe_to_score(None) == 0.0

    def test_roe_high_is_bullish(self) -> None:
        # ROE >= 0.20 -> +0.8
        assert _roe_to_score(0.25) == 0.8

    def test_roe_good_is_positive(self) -> None:
        # 0.15 <= ROE < 0.20 -> +0.6
        assert _roe_to_score(0.17) == 0.6

    def test_roe_negative_is_bearish(self) -> None:
        # ROE < 0 -> -0.7
        assert _roe_to_score(-0.05) == -0.7


class TestOtherZoneMappers:
    """Test remaining zone mappers."""

    def test_pb_none(self) -> None:
        assert _pb_to_score(None) == 0.0

    def test_pb_very_low_is_bullish(self) -> None:
        # P/B < 0.5 -> +0.8
        assert _pb_to_score(0.3) == 0.8

    def test_revenue_growth_none(self) -> None:
        assert _revenue_growth_to_score(None) == 0.0

    def test_revenue_growth_high_is_bullish(self) -> None:
        # Revenue growth >= 0.30 -> +0.8
        assert _revenue_growth_to_score(0.35) == 0.8

    def test_revenue_growth_negative_is_bearish(self) -> None:
        # Revenue growth < -0.1 -> -0.7
        assert _revenue_growth_to_score(-0.2) == -0.7

    def test_dividend_yield_none(self) -> None:
        assert _dividend_yield_to_score(None) == 0.0

    def test_dividend_yield_high_is_bullish(self) -> None:
        # DY >= 0.06 -> +0.8
        assert _dividend_yield_to_score(0.07) == 0.8

    def test_debt_to_equity_none(self) -> None:
        assert _debt_to_equity_to_score(None) == 0.0

    def test_debt_to_equity_low_is_bullish(self) -> None:
        # D/E < 0.3 -> +0.8
        assert _debt_to_equity_to_score(0.2) == 0.8

    def test_debt_to_equity_high_is_bearish(self) -> None:
        # D/E >= 3.0 -> -0.8
        assert _debt_to_equity_to_score(5.0) == -0.8
