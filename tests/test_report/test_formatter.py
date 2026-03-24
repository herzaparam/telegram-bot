"""Tests for shared report formatter."""

from __future__ import annotations

import pytest

# Will fail until formatter module exists
from src.report.formatter import (
    DEFAULT_EMOJI,
    MAX_MESSAGE_LENGTH,
    VERDICT_EMOJI,
    EvalDisplayItem,
    format_asset_card,
    format_asset_detail,
    format_report_header,
    format_scorecard_error,
    format_scorecard_message,
    format_scorecard_section,
    format_watchlist_message,
    split_report,
)


class TestVerdictEmoji:
    """Tests for VERDICT_EMOJI mapping."""

    def test_strong_buy_double_green(self):
        assert VERDICT_EMOJI["STRONG BUY"] == "\U0001f7e2\U0001f7e2"

    def test_buy_single_green(self):
        assert VERDICT_EMOJI["BUY"] == "\U0001f7e2"

    def test_hold_yellow(self):
        assert VERDICT_EMOJI["HOLD"] == "\U0001f7e1"

    def test_sell_red(self):
        assert VERDICT_EMOJI["SELL"] == "\U0001f534"

    def test_strong_sell_double_red(self):
        assert VERDICT_EMOJI["STRONG SELL"] == "\U0001f534\U0001f534"

    def test_unknown_verdict_not_in_map(self):
        assert "UNKNOWN" not in VERDICT_EMOJI

    def test_default_emoji_white_circle(self):
        assert DEFAULT_EMOJI == "\u26aa"


class TestFormatAssetCard:
    """Tests for format_asset_card."""

    def test_basic_card_structure(self):
        result = format_asset_card(
            "BBCA", "Bank Central Asia", "STRONG BUY", 0.85, 0.9,
            "Strong bullish momentum with solid fundamentals"
        )
        assert "<b>BBCA</b>" in result
        assert "Bank Central Asia" in result
        assert "STRONG BUY" in result

    def test_score_formatted_as_positive(self):
        result = format_asset_card(
            "BBCA", "Bank Central Asia", "BUY", 0.85, 0.9,
            "Good outlook"
        )
        assert "+0.85" in result

    def test_score_formatted_as_negative(self):
        result = format_asset_card(
            "TLKM", "Telkom", "SELL", -0.5, 0.75,
            "Bearish indicators"
        )
        assert "-0.50" in result

    def test_confidence_formatted_as_percentage(self):
        result = format_asset_card(
            "BBCA", "Bank Central Asia", "BUY", 0.85, 0.9,
            "Good outlook"
        )
        assert "90%" in result

    def test_emoji_in_card(self):
        result = format_asset_card(
            "BBCA", "Bank Central Asia", "STRONG BUY", 0.85, 0.9,
            "Good outlook"
        )
        assert "\U0001f7e2\U0001f7e2" in result

    def test_unknown_verdict_uses_default_emoji(self):
        result = format_asset_card(
            "XYZ", "Unknown Corp", "WEIRD", 0.0, 0.5,
            "Unknown verdict"
        )
        assert "\u26aa" in result

    def test_reasoning_under_100_chars_not_truncated(self):
        short_reasoning = "Short reasoning text"
        result = format_asset_card(
            "BTC", "Bitcoin", "HOLD", 0.1, 0.6, short_reasoning
        )
        assert short_reasoning in result
        assert "..." not in result

    def test_reasoning_over_100_chars_truncated_at_word_boundary(self):
        long_reasoning = (
            "This is a very long reasoning text that goes well beyond one hundred "
            "characters and should be truncated at a word boundary with ellipsis appended"
        )
        result = format_asset_card(
            "BTC", "Bitcoin", "HOLD", 0.1, 0.6, long_reasoning
        )
        # Should be truncated
        assert "..." in result
        # Original full text should not be present
        assert long_reasoning not in result

    def test_html_escaping_in_card(self):
        result = format_asset_card(
            "TEST", "Company <&> Inc", "BUY", 0.5, 0.8,
            "Reasoning with <html> & special chars"
        )
        assert "<&>" not in result
        assert "&amp;" in result


class TestFormatAssetDetail:
    """Tests for format_asset_detail."""

    def test_detail_contains_all_sections(self):
        result = format_asset_detail(
            "BBCA", "Bank Central Asia", "STRONG BUY", 0.85, 0.9,
            "Full reasoning text here",
            {"technical": "bullish", "volume": "high"},
            "Market volatility elevated"
        )
        assert "<b>Verdict:</b>" in result
        assert "<b>Score:</b>" in result
        assert "<b>Confidence:</b>" in result
        assert "<b>Reasoning:</b>" in result
        assert "<b>Key Factors:</b>" in result
        assert "<b>Risk Warning:</b>" in result

    def test_detail_no_truncation(self):
        long_reasoning = "A" * 200
        result = format_asset_detail(
            "BBCA", "Bank Central Asia", "BUY", 0.5, 0.8,
            long_reasoning, None, None
        )
        assert long_reasoning in result

    def test_detail_with_no_risk_warning(self):
        result = format_asset_detail(
            "BBCA", "Bank Central Asia", "BUY", 0.5, 0.8,
            "Reasoning", {"factor": "value"}, None
        )
        # Should still produce a result without error
        assert "BBCA" in result
        assert "Risk Warning" not in result

    def test_detail_with_no_key_factors(self):
        result = format_asset_detail(
            "BBCA", "Bank Central Asia", "BUY", 0.5, 0.8,
            "Reasoning", None, "Warning here"
        )
        assert "BBCA" in result


class TestFormatReportHeader:
    """Tests for format_report_header."""

    def test_header_contains_date(self):
        result = format_report_header("2026-03-24", 6, {"BUY": 3, "HOLD": 1, "SELL": 2}, [])
        assert "2026-03-24" in result

    def test_header_contains_asset_count(self):
        result = format_report_header("2026-03-24", 6, {"BUY": 3, "HOLD": 1, "SELL": 2}, [])
        assert "6" in result

    def test_header_contains_sentiment_distribution(self):
        result = format_report_header("2026-03-24", 6, {"BUY": 3, "HOLD": 1, "SELL": 2}, [])
        assert "BUY: 3" in result
        assert "HOLD: 1" in result
        assert "SELL: 2" in result

    def test_header_omits_zero_categories(self):
        result = format_report_header("2026-03-24", 3, {"BUY": 3, "SELL": 0}, [])
        assert "SELL" not in result

    def test_header_with_risk_warnings(self):
        result = format_report_header(
            "2026-03-24", 6, {"BUY": 3}, ["High volatility detected"]
        )
        assert "\u26a0" in result  # warning emoji
        assert "High volatility detected" in result

    def test_header_omits_risk_line_when_empty(self):
        result = format_report_header("2026-03-24", 3, {"BUY": 3}, [])
        assert "\u26a0" not in result


class TestSplitReport:
    """Tests for split_report."""

    def test_single_message_when_under_limit(self):
        header = "<b>Daily Signal Report</b>"
        cards = ["Card 1 content", "Card 2 content"]
        result = split_report(header, cards)
        assert len(result) == 1
        assert header in result[0]

    def test_max_message_length_constant(self):
        assert MAX_MESSAGE_LENGTH == 4096

    def test_splits_long_content(self):
        header = "<b>Daily Signal Report - 2026-03-24</b>\n"
        # Create 20 cards, each ~200 chars
        cards = [
            f"\U0001f7e2 <b>ASSET{i}</b> (Test Asset {i})\n"
            f"   BUY | Score: +0.{i:02d} | Conf: {50+i}%\n"
            f"   <i>{'x' * 150}</i>"
            for i in range(20)
        ]
        result = split_report(header, cards)
        assert len(result) > 1

    def test_no_message_exceeds_limit(self):
        header = "<b>Daily Signal Report - 2026-03-24</b>\n"
        cards = [
            f"\U0001f7e2 <b>ASSET{i}</b> (Test Asset {i})\n"
            f"   BUY | Score: +0.{i:02d} | Conf: {50+i}%\n"
            f"   <i>{'x' * 150}</i>"
            for i in range(20)
        ]
        result = split_report(header, cards)
        for msg in result:
            assert len(msg) <= MAX_MESSAGE_LENGTH, f"Message length {len(msg)} exceeds {MAX_MESSAGE_LENGTH}"

    def test_cards_never_split_mid_card(self):
        header = "<b>Report</b>\n"
        card_marker = "UNIQUE_CARD_MARKER"
        cards = [
            f"\U0001f7e2 <b>ASSET{i}</b>\n   {card_marker}_{i}\n   <i>{'y' * 150}</i>"
            for i in range(20)
        ]
        result = split_report(header, cards)
        # Each card should appear in exactly one message, fully intact
        for i in range(20):
            marker = f"{card_marker}_{i}"
            containing_msgs = [msg for msg in result if marker in msg]
            assert len(containing_msgs) == 1, f"Card {i} found in {len(containing_msgs)} messages"

    def test_first_message_has_header(self):
        header = "<b>Daily Signal Report</b>"
        cards = [f"Card {i}" for i in range(5)]
        result = split_report(header, cards)
        assert result[0].startswith(header)

    def test_continuation_header_on_subsequent(self):
        header = "<b>Daily Signal Report - 2026-03-24</b>\n"
        cards = [
            f"\U0001f7e2 <b>ASSET{i}</b> (Test Asset {i})\n"
            f"   BUY | Score: +0.{i:02d} | Conf: {50+i}%\n"
            f"   <i>{'x' * 150}</i>"
            for i in range(20)
        ]
        result = split_report(header, cards)
        if len(result) > 1:
            assert "continued" in result[1].lower()


class TestFormatWatchlistMessage:
    """Tests for format_watchlist_message."""

    def test_with_assets(self):
        assets = [
            ("BBCA", "Bank Central Asia", "IDX"),
            ("BTC", "Bitcoin", "Crypto"),
        ]
        result = format_watchlist_message(assets)
        assert "<b>BBCA</b>" in result
        assert "Bank Central Asia" in result
        assert "1." in result
        assert "2." in result

    def test_empty_list_returns_empty_state(self):
        result = format_watchlist_message([])
        assert "No assets" in result or "empty" in result.lower()
        assert "/add" in result


class TestScorecardSection:
    """Tests for format_scorecard_section (daily report integration)."""

    def test_empty_results_returns_empty_string(self):
        """D-18: return '' when no results in any window."""
        result = format_scorecard_section({}, None)
        assert result == ""

    def test_empty_lists_returns_empty_string(self):
        """D-18: return '' when all window lists are empty."""
        result = format_scorecard_section({"24h": [], "3d": []}, None)
        assert result == ""

    def test_single_window_24h_results(self):
        """24h results section with correct/wrong emoji per asset."""
        items = [
            EvalDisplayItem(symbol="BTC", verdict="BUY", change_pct=3.2, was_correct=True),
            EvalDisplayItem(symbol="ETH", verdict="BUY", change_pct=-2.1, was_correct=False),
        ]
        result = format_scorecard_section({"24h": items}, None)
        assert "<b>Yesterday's Scorecard</b>" in result
        assert "<b>24h Results (1/2)</b>" in result
        assert "\u2705 BTC" in result
        assert "\u274c ETH" in result

    def test_multiple_windows_in_order(self):
        """Multiple window sections appear in 24h, 3d, 7d, 30d order."""
        items_24h = [
            EvalDisplayItem(symbol="BTC", verdict="BUY", change_pct=3.2, was_correct=True),
        ]
        items_7d = [
            EvalDisplayItem(symbol="BTC", verdict="BUY", change_pct=8.7, was_correct=True),
        ]
        result = format_scorecard_section({"7d": items_7d, "24h": items_24h}, None)
        idx_24h = result.index("24h Results")
        idx_7d = result.index("7d Results")
        assert idx_24h < idx_7d

    def test_window_header_correct_total_count(self):
        """Window header shows correct/total like '24h Results (2/3)'."""
        items = [
            EvalDisplayItem(symbol="BTC", verdict="BUY", change_pct=3.2, was_correct=True),
            EvalDisplayItem(symbol="ETH", verdict="SELL", change_pct=-5.1, was_correct=True),
            EvalDisplayItem(symbol="SOL", verdict="HOLD", change_pct=0.5, was_correct=False),
        ]
        result = format_scorecard_section({"24h": items}, None)
        assert "<b>24h Results (2/3)</b>" in result

    def test_result_line_format(self):
        """Result line: '{emoji} {SYMBOL} -- {VERDICT} -> {sign}{pct}'."""
        items = [
            EvalDisplayItem(symbol="BTC", verdict="BUY", change_pct=3.2, was_correct=True),
        ]
        result = format_scorecard_section({"24h": items}, None)
        assert "\u2705 BTC -- BUY -> +3.2%" in result

    def test_result_line_negative_pct(self):
        """Negative change shows negative sign."""
        items = [
            EvalDisplayItem(symbol="ETH", verdict="BUY", change_pct=-2.1, was_correct=False),
        ]
        result = format_scorecard_section({"24h": items}, None)
        assert "\u274c ETH -- BUY -> -2.1%" in result

    def test_trend_line_shown_when_provided(self):
        """D-17: trend line at bottom in italics."""
        items = [
            EvalDisplayItem(symbol="BTC", verdict="BUY", change_pct=3.2, was_correct=True),
        ]
        trend = "Trending: 68% win rate this week (^ from 60% last week)"
        result = format_scorecard_section({"24h": items}, trend)
        assert f"<i>{trend}</i>" in result

    def test_no_trend_line_when_none(self):
        """No trend line when None."""
        items = [
            EvalDisplayItem(symbol="BTC", verdict="BUY", change_pct=3.2, was_correct=True),
        ]
        result = format_scorecard_section({"24h": items}, None)
        assert "<i>" not in result


class TestScorecardEmpty:
    """Explicitly test D-18 (returns '' for empty dict)."""

    def test_empty_dict(self):
        assert format_scorecard_section({}, None) == ""

    def test_empty_dict_with_trend(self):
        assert format_scorecard_section({}, "some trend") == ""


class TestScorecardMessage:
    """Tests for format_scorecard_message (/scorecard command)."""

    def test_title_includes_period(self):
        result = format_scorecard_message(
            period="30d", asset_filter=None,
            win_rates_by_window={"24h": (39, 60)},
            total_decisions=60, best_engine=("Technical", 72.0),
            worst_engine=("Quantitative", 48.0),
            per_asset_buyhold=[],
        )
        assert "<b>Scorecard - Last 30 Days</b>" in result

    def test_title_includes_asset_filter(self):
        result = format_scorecard_message(
            period="30d", asset_filter="BTC",
            win_rates_by_window={"24h": (14, 20)},
            total_decisions=20, best_engine=("Technical", 78.0),
            worst_engine=("Quantitative", 45.0),
            per_asset_buyhold=[],
        )
        assert "<b>Scorecard - BTC - Last 30 Days</b>" in result

    def test_win_rate_by_window_formatted(self):
        result = format_scorecard_message(
            period="30d", asset_filter=None,
            win_rates_by_window={"24h": (39, 60), "3d": (37, 60)},
            total_decisions=60, best_engine=None, worst_engine=None,
            per_asset_buyhold=[],
        )
        assert "24h:" in result
        assert "65%" in result
        assert "(39/60)" in result
        assert " 3d:" in result

    def test_best_engine_with_trophy(self):
        result = format_scorecard_message(
            period="30d", asset_filter=None,
            win_rates_by_window={"24h": (39, 60)},
            total_decisions=60, best_engine=("Technical", 72.0),
            worst_engine=("Quantitative", 48.0),
            per_asset_buyhold=[],
        )
        assert "\U0001f3c6" in result  # trophy
        assert "Technical" in result
        assert "72%" in result

    def test_worst_engine_with_warning(self):
        result = format_scorecard_message(
            period="30d", asset_filter=None,
            win_rates_by_window={"24h": (39, 60)},
            total_decisions=60, best_engine=("Technical", 72.0),
            worst_engine=("Quantitative", 48.0),
            per_asset_buyhold=[],
        )
        assert "\u26a0\ufe0f" in result  # warning
        assert "Quantitative" in result
        assert "48%" in result

    def test_buyhold_positive_alpha_bold(self):
        result = format_scorecard_message(
            period="30d", asset_filter=None,
            win_rates_by_window={"24h": (39, 60)},
            total_decisions=60, best_engine=None, worst_engine=None,
            per_asset_buyhold=[
                {"symbol": "BTC", "signal_return": 12.4, "buyhold_return": 8.1},
            ],
        )
        assert "<b>+4.3% alpha</b>" in result

    def test_buyhold_negative_underperform_italic(self):
        result = format_scorecard_message(
            period="30d", asset_filter=None,
            win_rates_by_window={"24h": (39, 60)},
            total_decisions=60, best_engine=None, worst_engine=None,
            per_asset_buyhold=[
                {"symbol": "BBCA", "signal_return": 3.2, "buyhold_return": 5.1},
            ],
        )
        assert "<i>-1.9% underperform</i>" in result

    def test_empty_state_message(self):
        result = format_scorecard_message(
            period="30d", asset_filter=None,
            win_rates_by_window={},
            total_decisions=0, best_engine=None, worst_engine=None,
            per_asset_buyhold=[],
        )
        assert "No scorecard data available yet" in result
        assert "two consecutive days" in result

    def test_period_empty_state(self):
        result = format_scorecard_message(
            period="7d", asset_filter=None,
            win_rates_by_window={},
            total_decisions=0, best_engine=None, worst_engine=None,
            per_asset_buyhold=[],
            period_empty=True,
        )
        assert "No evaluations in the last" in result
        assert "/scorecard 30d" in result

    def test_asset_filtered_with_recent_calls(self):
        result = format_scorecard_message(
            period="30d", asset_filter="BTC",
            win_rates_by_window={"24h": (14, 20)},
            total_decisions=20, best_engine=("Technical", 78.0),
            worst_engine=("Quantitative", 45.0),
            per_asset_buyhold=[
                {"symbol": "BTC", "signal_return": 12.4, "buyhold_return": 8.1},
            ],
            recent_calls=[
                {"date": "2026-03-23", "verdict": "BUY", "change_pct": 3.2, "was_correct": True, "window": "24h"},
                {"date": "2026-03-22", "verdict": "HOLD", "change_pct": 5.8, "was_correct": False, "window": "24h"},
            ],
        )
        assert "<b>Recent Calls</b>" in result
        assert "2026-03-23" in result
        assert "\u2705" in result
        assert "\u274c" in result

    def test_all_time_period_label(self):
        result = format_scorecard_message(
            period="all", asset_filter=None,
            win_rates_by_window={"24h": (100, 200)},
            total_decisions=200, best_engine=None, worst_engine=None,
            per_asset_buyhold=[],
        )
        assert "All Time" in result


class TestBuyAndHold:
    """Test alpha formatting (positive bold, negative italic)."""

    def test_positive_alpha(self):
        result = format_scorecard_message(
            period="30d", asset_filter=None,
            win_rates_by_window={"24h": (10, 20)},
            total_decisions=20, best_engine=None, worst_engine=None,
            per_asset_buyhold=[
                {"symbol": "ETH", "signal_return": 7.8, "buyhold_return": 6.0},
            ],
        )
        assert "<b>+1.8% alpha</b>" in result

    def test_negative_underperform(self):
        result = format_scorecard_message(
            period="30d", asset_filter=None,
            win_rates_by_window={"24h": (10, 20)},
            total_decisions=20, best_engine=None, worst_engine=None,
            per_asset_buyhold=[
                {"symbol": "BBCA", "signal_return": 3.2, "buyhold_return": 5.1},
            ],
        )
        assert "<i>-1.9% underperform</i>" in result

    def test_zero_alpha(self):
        result = format_scorecard_message(
            period="30d", asset_filter=None,
            win_rates_by_window={"24h": (10, 20)},
            total_decisions=20, best_engine=None, worst_engine=None,
            per_asset_buyhold=[
                {"symbol": "SOL", "signal_return": 5.0, "buyhold_return": 5.0},
            ],
        )
        assert "+0.0% alpha" in result


class TestScorecardError:
    """Test format_scorecard_error."""

    def test_error_message(self):
        result = format_scorecard_error()
        assert "Failed to load scorecard data" in result
