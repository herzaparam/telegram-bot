"""Tests for ValuationEngine: DCF, peer comparison, scenario analysis, crypto NVT + TVL proxies."""

from __future__ import annotations

import pandas as pd
import pytest

from src.engines.valuation import (
    QoQAlert,
    ValuationEngine,
    _compute_dcf,
    _compute_nvt_proxy,
    _compute_peer_score,
    _compute_scenarios,
    _compute_tvl_proxy,
    _compute_wacc,
    _margin_of_safety_to_score,
    detect_qoq_changes,
)


@pytest.fixture()
def empty_df() -> pd.DataFrame:
    """Empty price DataFrame for engine calls."""
    return pd.DataFrame(columns=["open", "high", "low", "close", "volume"])


# ---------------------------------------------------------------------------
# Test 1: DCF with valid inputs returns positive fair value
# ---------------------------------------------------------------------------


def test_dcf_valid_inputs_returns_positive_fair_value() -> None:
    """_compute_dcf with fcf=1B, growth=0.05, wacc=0.12, shares=10B returns positive."""
    result = _compute_dcf(
        fcf=1_000_000_000,
        growth_rate=0.05,
        wacc=0.12,
        shares_outstanding=10_000_000_000,
        projection_years=5,
        terminal_growth=0.03,
    )
    assert result > 0.0, f"Expected positive fair value, got {result}"


# ---------------------------------------------------------------------------
# Test 2: DCF with shares_outstanding=0 returns 0.0
# ---------------------------------------------------------------------------


def test_dcf_zero_shares_returns_zero() -> None:
    """_compute_dcf with shares_outstanding=0 returns 0.0 (guard)."""
    result = _compute_dcf(
        fcf=1_000_000_000,
        growth_rate=0.05,
        wacc=0.12,
        shares_outstanding=0,
    )
    assert result == 0.0


# ---------------------------------------------------------------------------
# Test 3: DCF with wacc <= terminal_growth returns 0.0
# ---------------------------------------------------------------------------


def test_dcf_invalid_spread_returns_zero() -> None:
    """_compute_dcf with wacc <= terminal_growth returns 0.0."""
    result = _compute_dcf(
        fcf=1_000_000_000,
        growth_rate=0.05,
        wacc=0.03,
        shares_outstanding=10_000_000_000,
        terminal_growth=0.03,
    )
    assert result == 0.0

    result2 = _compute_dcf(
        fcf=1_000_000_000,
        growth_rate=0.05,
        wacc=0.02,
        shares_outstanding=10_000_000_000,
        terminal_growth=0.03,
    )
    assert result2 == 0.0


# ---------------------------------------------------------------------------
# Test 4: Peer score -- cheaper stock returns positive
# ---------------------------------------------------------------------------


def test_peer_score_cheap_stock_positive() -> None:
    """Stock with P/E=10 vs sector avg P/E=15 should score positive (cheaper)."""
    score, label = _compute_peer_score(
        stock_metrics={"pe": 10, "pb": 1.0, "ev_ebitda": 6},
        sector_averages={"pe": 15, "pb": 2.0, "ev_ebitda": 12},
    )
    assert score > 0.0, f"Expected positive peer score, got {score}"
    assert label == "cheap"


# ---------------------------------------------------------------------------
# Test 5: Peer score -- expensive stock returns negative
# ---------------------------------------------------------------------------


def test_peer_score_expensive_stock_negative() -> None:
    """Stock with P/E=25 vs sector avg P/E=15 should score negative (expensive)."""
    score, label = _compute_peer_score(
        stock_metrics={"pe": 25, "pb": 4.0, "ev_ebitda": 18},
        sector_averages={"pe": 15, "pb": 2.0, "ev_ebitda": 12},
    )
    assert score < 0.0, f"Expected negative peer score, got {score}"
    assert label == "expensive"


# ---------------------------------------------------------------------------
# Test 6: Scenario analysis -- bull > base > bear
# ---------------------------------------------------------------------------


def test_scenarios_bull_gt_base_gt_bear() -> None:
    """_compute_scenarios returns bull > base > bear values."""
    result = _compute_scenarios(
        current_price=1000.0,
        fair_value=1200.0,
        cagr=0.10,
        std_dev=0.05,
    )
    assert result["bull"]["value"] > result["base"]["value"]
    assert result["base"]["value"] > result["bear"]["value"]


# ---------------------------------------------------------------------------
# Test 7: Scenario weighted return
# ---------------------------------------------------------------------------


def test_scenarios_weighted_return() -> None:
    """Weighted return = 0.25*bull + 0.50*base + 0.25*bear."""
    result = _compute_scenarios(
        current_price=1000.0,
        fair_value=1200.0,
        cagr=0.10,
        std_dev=0.05,
    )
    expected_weighted = (
        0.25 * result["bull"]["return_pct"]
        + 0.50 * result["base"]["return_pct"]
        + 0.25 * result["bear"]["return_pct"]
    )
    # Check weighted_return key exists and matches
    assert "weighted_return" in result
    assert abs(result["weighted_return"] - expected_weighted) < 1e-6


# ---------------------------------------------------------------------------
# Test 8: Margin of safety -- deeply undervalued
# ---------------------------------------------------------------------------


def test_mos_deeply_undervalued() -> None:
    """_margin_of_safety_to_score(0.50) returns 0.8."""
    assert _margin_of_safety_to_score(0.50) == 0.8


# ---------------------------------------------------------------------------
# Test 9: Margin of safety -- deeply overvalued
# ---------------------------------------------------------------------------


def test_mos_deeply_overvalued() -> None:
    """_margin_of_safety_to_score(-0.50) returns -0.8."""
    assert _margin_of_safety_to_score(-0.50) == -0.8


# ---------------------------------------------------------------------------
# Test 10: Margin of safety -- fairly valued
# ---------------------------------------------------------------------------


def test_mos_fairly_valued() -> None:
    """_margin_of_safety_to_score(0.0) returns 0.0."""
    assert _margin_of_safety_to_score(0.0) == 0.0


# ---------------------------------------------------------------------------
# Test 11: Engine analyze with valid data returns non-zero signal
# ---------------------------------------------------------------------------


def test_engine_analyze_valid_data(empty_df: pd.DataFrame) -> None:
    """analyze() with valid financial_data returns Signal with category='valuation'."""
    engine = ValuationEngine(
        financial_data=[
            {
                "operating_cash_flow": 5_000_000_000,
                "capex": -1_000_000_000,
                "revenue": 20_000_000_000,
            },
            {
                "operating_cash_flow": 4_500_000_000,
                "capex": -900_000_000,
                "revenue": 18_000_000_000,
            },
        ],
        peer_data=[
            {"pe": 15, "pb": 2.0, "ev_ebitda": 12},
        ],
        macro_rates={"risk_free_rate": 0.06, "beta": 1.2},
        shares_outstanding=10_000_000_000,
    )
    # Provide a df with at least a close price
    df = pd.DataFrame({"close": [5000.0], "open": [4900], "high": [5100], "low": [4800], "volume": [1000000]})
    signal = engine.analyze(asset_id=1, asset_symbol="BBCA", df=df)
    assert signal.category == "valuation"
    assert signal.score != 0.0 or signal.confidence != 0.0


# ---------------------------------------------------------------------------
# Test 12: Engine analyze with no data returns zero signal
# ---------------------------------------------------------------------------


def test_engine_analyze_no_data(empty_df: pd.DataFrame) -> None:
    """analyze() with financial_data=None returns score=0.0, confidence=0.0."""
    engine = ValuationEngine()
    signal = engine.analyze(asset_id=1, asset_symbol="BBCA", df=empty_df)
    assert signal.category == "valuation"
    assert signal.score == 0.0
    assert signal.confidence == 0.0


# ---------------------------------------------------------------------------
# Test 13: NVT proxy with valid data
# ---------------------------------------------------------------------------


def test_nvt_proxy_valid_data() -> None:
    """_compute_nvt_proxy with market_cap=500B, volume_24h=20B returns score."""
    score, confidence, reasoning = _compute_nvt_proxy(
        nvt_data={"market_cap": 500_000_000_000, "volume_24h": 20_000_000_000}
    )
    assert isinstance(score, float)
    assert isinstance(confidence, float)
    assert confidence > 0.0
    assert len(reasoning) > 0


# ---------------------------------------------------------------------------
# Test 14: NVT proxy with None data
# ---------------------------------------------------------------------------


def test_nvt_proxy_none_data() -> None:
    """_compute_nvt_proxy with nvt_data=None returns score=0, confidence=0."""
    score, confidence, reasoning = _compute_nvt_proxy(nvt_data=None)
    assert score == 0.0
    assert confidence == 0.0


# ---------------------------------------------------------------------------
# Test 15: TVL proxy with valid data
# ---------------------------------------------------------------------------


def test_tvl_proxy_valid_data() -> None:
    """_compute_tvl_proxy with market_cap=1B, tvl=500M returns score based on ratio."""
    score, confidence, reasoning = _compute_tvl_proxy(
        tvl_data={"market_cap": 1_000_000_000, "tvl": 500_000_000}
    )
    assert isinstance(score, float)
    assert confidence > 0.0
    # mcap/tvl = 2.0 -> neutral range (1.0-3.0) -> score = 0.1
    assert score == pytest.approx(0.1)


# ---------------------------------------------------------------------------
# Test 16: TVL proxy with None or zero tvl
# ---------------------------------------------------------------------------


def test_tvl_proxy_none_data() -> None:
    """_compute_tvl_proxy with tvl=None returns score=0, confidence=0."""
    score, confidence, reasoning = _compute_tvl_proxy(tvl_data=None)
    assert score == 0.0
    assert confidence == 0.0

    score2, confidence2, reasoning2 = _compute_tvl_proxy(
        tvl_data={"market_cap": 1_000_000_000, "tvl": 0}
    )
    assert score2 == 0.0
    assert confidence2 == 0.0


# ---------------------------------------------------------------------------
# Test 17: Crypto analyze routes to NVT or TVL proxy
# ---------------------------------------------------------------------------


def test_engine_crypto_routes_to_proxy(empty_df: pd.DataFrame) -> None:
    """analyze() for crypto routes to NVT/TVL proxy based on available data."""
    # With NVT data only
    engine_nvt = ValuationEngine(
        nvt_data={"market_cap": 500_000_000_000, "volume_24h": 20_000_000_000},
    )
    signal = engine_nvt.analyze(asset_id=100, asset_symbol="BTC", df=empty_df)
    assert signal.category == "valuation"
    assert signal.confidence > 0.0

    # With TVL data only
    engine_tvl = ValuationEngine(
        tvl_data={"market_cap": 1_000_000_000, "tvl": 500_000_000},
    )
    signal2 = engine_tvl.analyze(asset_id=101, asset_symbol="UNI", df=empty_df)
    assert signal2.category == "valuation"
    assert signal2.confidence > 0.0

    # With both NVT and TVL
    engine_both = ValuationEngine(
        nvt_data={"market_cap": 500_000_000_000, "volume_24h": 20_000_000_000},
        tvl_data={"market_cap": 1_000_000_000, "tvl": 500_000_000},
    )
    signal3 = engine_both.analyze(asset_id=102, asset_symbol="ETH", df=empty_df)
    assert signal3.category == "valuation"
    assert signal3.confidence > 0.0


# ---------------------------------------------------------------------------
# WACC computation tests
# ---------------------------------------------------------------------------


def test_wacc_basic() -> None:
    """WACC with default equity risk premium and no debt returns cost of equity."""
    wacc = _compute_wacc(risk_free_rate=0.06, beta=1.0)
    # cost_of_equity = 0.06 + 1.0 * 0.065 = 0.125
    # WACC = 0.125 * (1-0) + 0 = 0.125
    assert wacc == pytest.approx(0.125, abs=0.001)


def test_wacc_clamped() -> None:
    """WACC is clamped to [0.05, 0.25]."""
    wacc_low = _compute_wacc(risk_free_rate=0.01, beta=0.1)
    assert wacc_low >= 0.05

    wacc_high = _compute_wacc(risk_free_rate=0.15, beta=2.0)
    assert wacc_high <= 0.25


# ---------------------------------------------------------------------------
# QoQ ratio change detection tests
# ---------------------------------------------------------------------------


def test_qoq_detects_margin_drop() -> None:
    """detect_qoq_changes with 5pp net_margin drop returns alert (>3pp threshold)."""
    data = [
        {"period": "Q3-2025", "net_margin": 0.25, "revenue": 1e12},
        {"period": "Q2-2025", "net_margin": 0.30, "revenue": 1e12},
    ]
    alerts = detect_qoq_changes(data)
    assert len(alerts) >= 1
    margin_alerts = [a for a in alerts if a.metric_name == "net_margin"]
    assert len(margin_alerts) == 1
    assert margin_alerts[0].is_percentage_point is True


def test_qoq_no_alert_small_margin_change() -> None:
    """detect_qoq_changes with 1pp net_margin change returns no alert (<3pp threshold)."""
    data = [
        {"period": "Q3-2025", "net_margin": 0.25, "revenue": 1e12},
        {"period": "Q2-2025", "net_margin": 0.24, "revenue": 1e12},
    ]
    alerts = detect_qoq_changes(data)
    margin_alerts = [a for a in alerts if a.metric_name == "net_margin"]
    assert len(margin_alerts) == 0


def test_qoq_detects_revenue_surge() -> None:
    """detect_qoq_changes with 25% revenue change returns alert (>10% threshold)."""
    data = [
        {"period": "Q3-2025", "net_margin": 0.25, "revenue": 100e9},
        {"period": "Q2-2025", "net_margin": 0.25, "revenue": 80e9},
    ]
    alerts = detect_qoq_changes(data)
    rev_alerts = [a for a in alerts if a.metric_name == "revenue"]
    assert len(rev_alerts) == 1
    assert rev_alerts[0].is_percentage_point is False


def test_qoq_max_two_alerts() -> None:
    """detect_qoq_changes returns max 2 alerts even with many changes."""
    data = [
        {
            "period": "Q3-2025",
            "net_margin": 0.10,
            "gross_margin": 0.20,
            "operating_margin": 0.05,
            "revenue": 200e9,
            "net_profit": 30e9,
            "total_debt": 500e9,
        },
        {
            "period": "Q2-2025",
            "net_margin": 0.30,
            "gross_margin": 0.50,
            "operating_margin": 0.25,
            "revenue": 100e9,
            "net_profit": 10e9,
            "total_debt": 200e9,
        },
    ]
    alerts = detect_qoq_changes(data)
    assert len(alerts) <= 2


def test_qoq_single_period_returns_empty() -> None:
    """detect_qoq_changes with only one period returns empty list."""
    data = [
        {"period": "Q3-2025", "net_margin": 0.25, "revenue": 1e12},
    ]
    alerts = detect_qoq_changes(data)
    assert alerts == []
