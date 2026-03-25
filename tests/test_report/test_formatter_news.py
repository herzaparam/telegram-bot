"""Tests for format_news_digest in the daily report formatter.

TDD tests for Phase 08-04 Task 2.
"""

from __future__ import annotations

import pytest


class TestFormatNewsDigest:
    """Tests for the format_news_digest function."""

    def test_empty_list_returns_empty_string(self):
        """format_news_digest() with empty list returns empty string."""
        from src.report.formatter import format_news_digest

        result = format_news_digest([])
        assert result == ""

    def test_none_impact_score_items_filtered(self):
        """Items without impact_score are filtered out."""
        from src.report.formatter import format_news_digest

        items = [
            {
                "headline": "Headline without score",
                "source": "kontan",
                "category": "macro",
                "impact_score": None,
                "affected_assets": {},
            }
        ]
        result = format_news_digest(items)
        assert result == ""

    def test_five_high_impact_headlines_formatted(self):
        """format_news_digest() with 5 high-impact headlines returns HTML section."""
        from src.report.formatter import format_news_digest

        items = [
            {
                "headline": "Bank Indonesia raises rates",
                "source": "kontan",
                "category": "central_bank",
                "impact_score": 0.8,
                "affected_assets": {"BBCA": 0.5, "BBRI": 0.3},
            },
            {
                "headline": "Bitcoin ETF approved",
                "source": "coindesk",
                "category": "regulation",
                "impact_score": 0.9,
                "affected_assets": {"BTC": 1.0},
            },
            {
                "headline": "TLKM reports record revenue",
                "source": "bisnis",
                "category": "earnings",
                "impact_score": 0.6,
                "affected_assets": {"TLKM": 0.8},
            },
            {
                "headline": "CPI above expectations",
                "source": "reuters",
                "category": "macro",
                "impact_score": -0.5,
                "affected_assets": {},
            },
            {
                "headline": "BTC halving imminent",
                "source": "coindesk",
                "category": "halving",
                "impact_score": 0.7,
                "affected_assets": {"BTC": 0.9},
            },
        ]
        result = format_news_digest(items)

        assert result != ""
        assert "<b>News &amp; Events</b>" in result
        assert "Bank Indonesia raises rates" in result
        assert "Bitcoin ETF approved" in result

    def test_caps_at_ten_headlines(self):
        """format_news_digest() caps at 10 headlines per D-19."""
        from src.report.formatter import format_news_digest

        # Create 15 items
        items = [
            {
                "headline": f"Headline {i}",
                "source": "kontan",
                "category": "macro",
                "impact_score": float(i) / 10,
                "affected_assets": {},
            }
            for i in range(1, 16)
        ]
        result = format_news_digest(items)

        # Count how many headlines appear -- should be at most 10
        headline_count = sum(1 for i in range(1, 16) if f"Headline {i}" in result)
        assert headline_count <= 10

    def test_escapes_html_in_headline(self):
        """format_news_digest() escapes HTML special characters in headlines."""
        from src.report.formatter import format_news_digest

        items = [
            {
                "headline": "Market <B&O> crash: stocks fall 5%",
                "source": "kontan",
                "category": "market",
                "impact_score": -0.8,
                "affected_assets": {},
            }
        ]
        result = format_news_digest(items)

        assert "&lt;B&amp;O&gt;" in result
        # Should not contain unescaped HTML
        assert "<B&O>" not in result

    def test_shows_source_and_affected_assets(self):
        """format_news_digest() shows source and affected assets per headline."""
        from src.report.formatter import format_news_digest

        items = [
            {
                "headline": "BBCA Q4 earnings beat",
                "source": "bisnis",
                "category": "earnings",
                "impact_score": 0.75,
                "affected_assets": {"BBCA": 0.8, "BBRI": 0.3},
            }
        ]
        result = format_news_digest(items)

        assert "bisnis" in result
        assert "BBCA" in result

    def test_groups_by_category(self):
        """format_news_digest() groups headlines by category with labels."""
        from src.report.formatter import format_news_digest

        items = [
            {
                "headline": "Fed raises rates",
                "source": "reuters",
                "category": "central_bank",
                "impact_score": -0.7,
                "affected_assets": {},
            },
            {
                "headline": "BBCA beats earnings",
                "source": "bisnis",
                "category": "earnings",
                "impact_score": 0.6,
                "affected_assets": {"BBCA": 0.8},
            },
        ]
        result = format_news_digest(items)

        # Category labels should appear
        assert "<b>Central Bank</b>" in result
        assert "<b>Earnings</b>" in result

    def test_positive_impact_gets_green_indicator(self):
        """Items with positive impact (> 0.1) get green circle indicator."""
        from src.report.formatter import format_news_digest

        items = [
            {
                "headline": "Stock market rallies",
                "source": "kontan",
                "category": "market",
                "impact_score": 0.5,
                "affected_assets": {},
            }
        ]
        result = format_news_digest(items)

        # Green circle = \U0001f7e2
        assert "\U0001f7e2" in result

    def test_negative_impact_gets_red_indicator(self):
        """Items with negative impact (< -0.1) get red circle indicator."""
        from src.report.formatter import format_news_digest

        items = [
            {
                "headline": "Market sell-off",
                "source": "kontan",
                "category": "market",
                "impact_score": -0.5,
                "affected_assets": {},
            }
        ]
        result = format_news_digest(items)

        # Red circle = \U0001f534
        assert "\U0001f534" in result

    def test_neutral_impact_gets_white_indicator(self):
        """Items near-zero impact (between -0.1 and 0.1) get white/neutral circle."""
        from src.report.formatter import format_news_digest

        items = [
            {
                "headline": "Market stable",
                "source": "kontan",
                "category": "market",
                "impact_score": 0.05,
                "affected_assets": {},
            }
        ]
        result = format_news_digest(items)

        # White/gray circle = \u26aa
        assert "\u26aa" in result

    def test_general_affected_assets_shows_general(self):
        """Items with empty/missing affected_assets show 'general'."""
        from src.report.formatter import format_news_digest

        items = [
            {
                "headline": "Global macro event",
                "source": "reuters",
                "category": "macro",
                "impact_score": 0.3,
                "affected_assets": {},
            }
        ]
        result = format_news_digest(items)

        assert "general" in result

    def test_sorts_by_absolute_impact_score(self):
        """format_news_digest() sorts by absolute impact score descending."""
        from src.report.formatter import format_news_digest

        items = [
            {
                "headline": "Low impact news",
                "source": "kontan",
                "category": "macro",
                "impact_score": 0.1,
                "affected_assets": {},
            },
            {
                "headline": "High impact news",
                "source": "kontan",
                "category": "macro",
                "impact_score": 0.9,
                "affected_assets": {},
            },
        ]
        result = format_news_digest(items)

        # High impact should appear before low impact
        high_idx = result.find("High impact news")
        low_idx = result.find("Low impact news")
        assert high_idx < low_idx


class TestReportStageNewsIntegration:
    """Tests for news digest integration in send_daily_report."""

    def test_report_py_queries_news_events(self):
        """src/data/report.py imports and calls format_news_digest."""
        import inspect

        import src.data.report as report_module

        source = inspect.getsource(report_module)
        assert "format_news_digest" in source
        assert "NewsEvent" in source

    def test_formatter_has_format_news_digest(self):
        """src/report/formatter.py exports format_news_digest."""
        from src.report.formatter import format_news_digest

        assert callable(format_news_digest)
