"""Tests for valuation-related formatter functions (Phase 09 Plan 05)."""

from __future__ import annotations

import pytest

from src.report.formatter import (
    format_fundamentals_dashboard,
    format_idr,
    format_valuation_detail,
    format_valuation_summary,
)


class TestFormatIdr:
    """Tests for format_idr helper."""

    def test_trillions(self) -> None:
        assert format_idr(2_100_000_000_000) == "Rp 2.1T"

    def test_billions(self) -> None:
        assert format_idr(450_000_000_000) == "Rp 450B"

    def test_millions(self) -> None:
        assert format_idr(12_300_000) == "Rp 12.3M"

    def test_small_value(self) -> None:
        assert format_idr(50_000) == "Rp 50,000"

    def test_negative(self) -> None:
        assert format_idr(-600_000_000_000) == "-Rp 600B"


class TestFormatValuationDetail:
    """Tests for format_valuation_detail."""

    def test_full_valuation_has_header(self) -> None:
        result = format_valuation_detail(
            symbol="BBCA",
            asset_name="Bank Central Asia",
            current_price=8250,
            fair_value=10000,
            margin_of_safety=0.212,
            scenarios={
                "bull": {"value": 12000, "return_pct": 0.4545},
                "base": {"value": 10000, "return_pct": 0.212},
                "bear": {"value": 8000, "return_pct": -0.030},
            },
            peer_comparison={
                "pe": {"value": 10.0, "sector_avg": 15.0, "rank": "cheap"},
                "pb": {"value": 1.5, "sector_avg": 2.0, "rank": "cheap"},
            },
            sector="banking",
            period="Q3-2025",
            last_updated="2025-10-15",
        )
        assert "<b>Valuation" in result
        assert "BBCA" in result
        assert "Fair Value (DCF)" in result
        assert "Rp 8,250" in result

    def test_no_pdf_data_includes_warning(self) -> None:
        result = format_valuation_detail(
            symbol="BBRI",
            asset_name="Bank Rakyat Indonesia",
            current_price=5000,
            fair_value=6000,
            margin_of_safety=0.20,
            scenarios=None,
            peer_comparison=None,
            sector=None,
            period="Q3-2025",
            last_updated="2025-10-15",
            has_pdf_data=False,
        )
        assert "Estimated from market data only" in result
        assert "\u26a0\ufe0f" in result  # warning emoji
        assert "Estimated Fair Value" in result

    def test_scenario_returns_signed(self) -> None:
        result = format_valuation_detail(
            symbol="BBCA",
            asset_name="BCA",
            current_price=8250,
            fair_value=10000,
            margin_of_safety=0.21,
            scenarios={
                "bull": {"value": 12000, "return_pct": 0.152},
                "base": {"value": 10000, "return_pct": 0.05},
                "bear": {"value": 7000, "return_pct": -0.083},
            },
            peer_comparison=None,
            sector=None,
            period="Q3-2025",
            last_updated="2025-10-15",
        )
        assert "+15.2%" in result
        assert "-8.3%" in result


class TestFormatFundamentalsDashboard:
    """Tests for format_fundamentals_dashboard."""

    def test_includes_trend_emoji(self) -> None:
        result = format_fundamentals_dashboard(
            symbol="BBCA",
            asset_name="Bank Central Asia",
            profitability={
                "net_margin": {"value": 0.25, "qoq_change": 0.02, "trend": "up"},
            },
            valuation_ratios={"pe": 10.0, "pb": 1.5},
            leverage={"debt_equity": {"value": 0.8, "qoq_change": -0.1, "trend": "down"}},
            cash_flow={"operating_cf": 2_100_000_000_000, "fcf": 1_500_000_000_000},
            source_label="IDX financial report",
            period="Q3-2025",
        )
        assert "\u2b06\ufe0f" in result  # up arrow
        assert "\u2b07\ufe0f" in result  # down arrow
        assert "Rp 2.1T" in result

    def test_cross_validation_warning(self) -> None:
        result = format_fundamentals_dashboard(
            symbol="BBCA",
            asset_name="BCA",
            profitability={},
            valuation_ratios={"pe": 10.0},
            leverage={},
            cash_flow={},
            source_label="IDX financial report",
            period="Q3-2025",
            cross_validation_warnings=["Revenue differs from market data by 15%. Manual review recommended."],
        )
        assert "\u26a0\ufe0f" in result
        assert "Revenue differs" in result

    def test_chart_emoji_in_header(self) -> None:
        result = format_fundamentals_dashboard(
            symbol="BBCA",
            asset_name="BCA",
            profitability={},
            valuation_ratios={},
            leverage={},
            cash_flow={},
            source_label="Market data (yfinance)",
            period="Q3-2025",
        )
        assert "\U0001f4ca" in result


class TestFormatValuationSummary:
    """Tests for format_valuation_summary."""

    def test_one_line_per_stock(self) -> None:
        stocks = [
            {"symbol": "BBCA", "price": 8250, "fair_value": 10000, "margin": 0.21, "has_pdf": True, "qoq_alerts": []},
            {"symbol": "BBRI", "price": 5000, "fair_value": 6000, "margin": 0.20, "has_pdf": True, "qoq_alerts": []},
        ]
        result = format_valuation_summary(stocks)
        assert "BBCA:" in result
        assert "BBRI:" in result
        assert "Valuation Summary" in result

    def test_empty_list_returns_empty(self) -> None:
        result = format_valuation_summary([])
        assert result == ""

    def test_asterisk_footnote_no_pdf(self) -> None:
        stocks = [
            {"symbol": "BBCA", "price": 8500, "fair_value": 10000, "margin": 0.18, "has_pdf": False, "qoq_alerts": []},
        ]
        result = format_valuation_summary(stocks)
        assert "*" in result
        assert "Estimated from market data" in result

    def test_qoq_alert_lines(self) -> None:
        stocks = [
            {
                "symbol": "BBCA",
                "price": 8250,
                "fair_value": 10000,
                "margin": 0.21,
                "has_pdf": True,
                "qoq_alerts": ["Net margin dropped 5.2pp QoQ (28.1% -> 22.9%)"],
            },
        ]
        result = format_valuation_summary(stocks)
        assert "Net margin dropped" in result
        assert "\u26a0\ufe0f" in result

    def test_margin_emoji_green_above_20pct(self) -> None:
        stocks = [
            {"symbol": "BBCA", "price": 8000, "fair_value": 10000, "margin": 0.25, "has_pdf": True, "qoq_alerts": []},
        ]
        result = format_valuation_summary(stocks)
        assert "\U0001f7e2" in result  # green circle

    def test_margin_emoji_red_below_neg5pct(self) -> None:
        stocks = [
            {"symbol": "BBCA", "price": 12000, "fair_value": 10000, "margin": -0.17, "has_pdf": True, "qoq_alerts": []},
        ]
        result = format_valuation_summary(stocks)
        assert "\U0001f534" in result  # red circle
