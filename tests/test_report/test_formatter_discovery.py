"""Tests for discovery card, section, DD report, and compare table formatters."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from src.report.formatter import (
    CROWN_EMOJI,
    DISCOVERY_EMOJI,
    TRIGGER_ICONS,
    format_compare_table,
    format_dd_report,
    format_discovery_card,
    format_discovery_section,
)


def _make_candidate(
    symbol: str = "ACES.JK",
    name: str = "Ace Hardware",
    asset_type: str = "stock",
    composite_score: float = 0.82,
    current_price: float = 1250,
    price_change_pct: float = 8.5,
    volume_ratio: float = 3.2,
    triggers: list | None = None,
) -> dict:
    """Create a discovery candidate dict."""
    if triggers is None:
        triggers = [
            {"type": "volume_spike", "name": "Volume 3.2x", "score": 0.9},
            {"type": "price_breakout", "name": "52w High", "score": 0.7},
        ]
    return {
        "symbol": symbol,
        "name": name,
        "asset_type": asset_type,
        "composite_score": composite_score,
        "triggers": triggers,
        "current_price": current_price,
        "price_change_pct": price_change_pct,
        "volume_ratio": volume_ratio,
    }


class TestFormatDiscoveryCard:
    """Tests for format_discovery_card."""

    def test_basic_stock_card(self) -> None:
        """Stock card uses Rp price format and trigger emojis."""
        candidate = _make_candidate()
        result = format_discovery_card(candidate)
        assert "<b>ACES.JK</b>" in result
        assert "Ace Hardware" in result
        assert "[stock]" in result
        assert "Rp 1,250" in result
        assert "+8.5%" in result
        assert "0.82" in result
        assert TRIGGER_ICONS["volume_spike"] in result
        assert TRIGGER_ICONS["price_breakout"] in result

    def test_crypto_card_uses_dollar(self) -> None:
        """Crypto card uses $ price format."""
        candidate = _make_candidate(
            symbol="BTC/USDT", name="Bitcoin", asset_type="crypto",
            current_price=67500.50, price_change_pct=2.3,
        )
        result = format_discovery_card(candidate)
        assert "$67,500.50" in result
        assert "[crypto]" in result

    def test_top_3_triggers(self) -> None:
        """Only top 3 triggers by score are shown."""
        triggers = [
            {"type": "volume_spike", "name": "Vol", "score": 0.5},
            {"type": "price_breakout", "name": "Breakout", "score": 0.9},
            {"type": "momentum_surge", "name": "Momentum", "score": 0.7},
            {"type": "statistical_anomaly", "name": "Anomaly", "score": 0.3},
        ]
        candidate = _make_candidate(triggers=triggers)
        result = format_discovery_card(candidate)
        # Breakout (0.9), Momentum (0.7), Vol (0.5) should be shown
        assert "Breakout" in result
        assert "Momentum" in result
        assert "Vol" in result
        # Anomaly (0.3) should not be shown
        assert "Anomaly" not in result

    def test_negative_change_pct(self) -> None:
        """Negative price change shows minus sign."""
        candidate = _make_candidate(price_change_pct=-3.2)
        result = format_discovery_card(candidate)
        assert "-3.2%" in result

    def test_html_escape(self) -> None:
        """HTML special chars in name are escaped."""
        candidate = _make_candidate(name="A&B <Corp>")
        result = format_discovery_card(candidate)
        assert "A&amp;B &lt;Corp&gt;" in result


class TestFormatDiscoverySection:
    """Tests for format_discovery_section."""

    def test_empty_candidates_returns_empty(self) -> None:
        """Empty list returns empty string (section omitted)."""
        result = format_discovery_section([])
        assert result == ""

    def test_top_5_only(self) -> None:
        """Only top 5 candidates are shown even if 7 provided."""
        candidates = [
            _make_candidate(symbol=f"SYM{i}.JK", name=f"Company {i}")
            for i in range(7)
        ]
        result = format_discovery_section(candidates)
        assert "SYM0.JK" in result
        assert "SYM4.JK" in result
        assert "SYM5.JK" not in result
        assert "SYM6.JK" not in result

    def test_section_has_header(self) -> None:
        """Section includes New Opportunities header."""
        candidates = [_make_candidate()]
        result = format_discovery_section(candidates)
        assert f"<b>{DISCOVERY_EMOJI} New Opportunities</b>" in result

    def test_section_has_date(self) -> None:
        """Section includes scan date."""
        from datetime import date

        candidates = [_make_candidate()]
        result = format_discovery_section(candidates)
        # Date should appear in the result (today's ISO date)
        assert date.today().isoformat() in result


class TestFormatDDReport:
    """Tests for format_dd_report."""

    def test_full_dd_report(self) -> None:
        """Full DD report contains all sections."""
        dd_data = {
            "sector": "Banking",
            "sector_rank": {
                "pe": {"value": 12.5, "median": 15.0},
                "pb": {"value": 2.1, "median": 1.8},
                "roe": {"value": 18.5, "median": 14.0},
                "net_margin": {"value": 25.3, "median": 20.0},
                "debt_to_equity": {"value": 0.5, "median": 0.8},
            },
            "management_quality": {
                "label": "Good",
                "score": 0.65,
                "revenue_cagr": 12.3,
                "roe_trend": "improving",
            },
            "ownership_changes": {
                "holders": [
                    {"name": "BlackRock", "pct": 8.5, "delta": 1.2},
                    {"name": "Vanguard", "pct": 5.2, "delta": -0.5},
                ],
                "last_updated": "2026-03-20",
            },
            "competitive_position": {
                "rank": 2,
                "total": 10,
                "metric": "ROE",
                "moat_summary": "Strong brand, low cost of funds",
            },
        }
        result = format_dd_report("BBCA.JK", "Bank Central Asia", dd_data)
        assert "Due Diligence: BBCA.JK" in result
        assert "Bank Central Asia" in result
        assert "Banking" in result
        assert "Sector Ranking" in result
        assert "P/E" in result
        assert "Management Quality" in result
        assert "Good" in result
        assert "Ownership" in result
        assert "BlackRock" in result
        assert "Competitive Position" in result
        assert "#2 of 10" in result

    def test_dd_report_ownership_arrows(self) -> None:
        """Ownership changes show correct up/down arrows."""
        dd_data = {
            "sector": "Banking",
            "ownership_changes": {
                "holders": [
                    {"name": "Buyer", "pct": 10.0, "delta": 2.0},
                    {"name": "Seller", "pct": 5.0, "delta": -1.5},
                ],
            },
        }
        result = format_dd_report("TEST.JK", "Test Corp", dd_data)
        assert "\u2b06\ufe0f" in result  # up arrow for positive delta
        assert "\u2b07\ufe0f" in result  # down arrow for negative delta


class TestFormatCompareTable:
    """Tests for format_compare_table."""

    def test_crown_on_best_values(self) -> None:
        """Crown emoji appears after best value in each row."""
        data = [
            {"symbol": "BBCA", "pe": 15.0, "pb": 3.0, "roe": 20.0, "net_margin": 30.0, "debt_to_equity": 0.5, "revenue_cagr": 12.0},
            {"symbol": "BBRI", "pe": 10.0, "pb": 2.0, "roe": 18.0, "net_margin": 25.0, "debt_to_equity": 0.8, "revenue_cagr": 15.0},
        ]
        result = format_compare_table(["BBCA", "BBRI"], data, "Banking")
        assert CROWN_EMOJI in result
        assert "Sector Comparison" in result
        assert "Banking" in result

    def test_empty_data(self) -> None:
        """Empty data returns empty string."""
        result = format_compare_table([], [], "Banking")
        assert result == ""

    def test_pre_block(self) -> None:
        """Table uses <pre> block for alignment."""
        data = [
            {"symbol": "A", "pe": 10.0, "pb": 1.5, "roe": 15.0, "net_margin": 20.0, "debt_to_equity": 0.5, "revenue_cagr": 8.0},
        ]
        result = format_compare_table(["A"], data, "Tech")
        assert "<pre>" in result
        assert "</pre>" in result
