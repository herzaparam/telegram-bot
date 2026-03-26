"""Tests for src/llm/prompts.py -- prompt construction with lesson injection."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from src.llm.prompts import _SYSTEM_PROMPT, _format_engine_data, build_decision_prompt


def _make_asset(
    symbol: str = "BBCA",
    name: str = "Bank Central Asia",
    asset_type: str = "stock",
) -> MagicMock:
    """Create a mock Asset."""
    asset = MagicMock()
    asset.symbol = symbol
    asset.name = name
    asset.asset_type = asset_type
    return asset


def _make_signal(
    category: str = "technical",
    score: float = 0.5,
    confidence: float = 0.8,
) -> MagicMock:
    """Create a mock SignalRecord."""
    sig = MagicMock()
    sig.category = category
    sig.score = score
    sig.confidence = confidence
    sig.indicators = {"rsi_14": 55}
    return sig


class TestSystemPrompt:
    """Verify system prompt contains lessons guidance."""

    def test_system_prompt_contains_lessons_guidance(self) -> None:
        assert "lessons from past mistakes" in _SYSTEM_PROMPT


class TestLessonPrompt:
    """Tests for lesson injection into decision prompt."""

    def test_prompt_without_lessons(self) -> None:
        """No lessons parameter: no lesson sections in user message."""
        asset = _make_asset()
        signals = [_make_signal()]
        messages = build_decision_prompt(asset, signals, [])
        user_content = messages[1]["content"]
        assert "ASSET-SPECIFIC LESSONS" not in user_content
        assert "GENERAL LESSONS" not in user_content

    def test_prompt_with_asset_lessons(self) -> None:
        """Asset-specific lessons appear in ASSET-SPECIFIC LESSONS section."""
        asset = _make_asset()
        signals = [_make_signal()]
        lessons = [
            {
                "lesson": "RSI reversals often precede bounces",
                "asset_type": "stock",
                "engine_tags": ["technical"],
                "accuracy": 0.72,
                "times_applied": 15,
            }
        ]
        messages = build_decision_prompt(asset, signals, [], lessons=lessons)
        user_content = messages[1]["content"]
        assert "ASSET-SPECIFIC LESSONS:" in user_content
        assert "RSI reversals" in user_content
        assert "72%" in user_content
        assert "15 uses" in user_content

    def test_prompt_with_general_lessons(self) -> None:
        """General lessons appear in GENERAL LESSONS section."""
        asset = _make_asset()
        signals = [_make_signal()]
        lessons = [
            {
                "lesson": "Market overreacts to macro news",
                "asset_type": "all",
                "engine_tags": ["sentiment"],
                "accuracy": 0.65,
                "times_applied": 20,
            }
        ]
        messages = build_decision_prompt(asset, signals, [], lessons=lessons)
        user_content = messages[1]["content"]
        assert "GENERAL LESSONS:" in user_content
        assert "Market overreacts" in user_content

    def test_prompt_with_both(self) -> None:
        """Mixed asset-specific and general lessons produce both sections."""
        asset = _make_asset()
        signals = [_make_signal()]
        lessons = [
            {
                "lesson": "RSI reversals work well for IDX stocks",
                "asset_type": "stock",
                "engine_tags": ["technical"],
                "accuracy": 0.72,
                "times_applied": 15,
            },
            {
                "lesson": "Market overreacts to macro news",
                "asset_type": "all",
                "engine_tags": ["sentiment"],
                "accuracy": 0.65,
                "times_applied": 20,
            },
        ]
        messages = build_decision_prompt(asset, signals, [], lessons=lessons)
        user_content = messages[1]["content"]
        assert "ASSET-SPECIFIC LESSONS:" in user_content
        assert "GENERAL LESSONS:" in user_content

    def test_prompt_with_none_accuracy(self) -> None:
        """Lesson with no accuracy shows N/A."""
        asset = _make_asset()
        signals = [_make_signal()]
        lessons = [
            {
                "lesson": "New lesson",
                "asset_type": "stock",
                "engine_tags": [],
                "accuracy": None,
                "times_applied": 0,
            }
        ]
        messages = build_decision_prompt(asset, signals, [], lessons=lessons)
        user_content = messages[1]["content"]
        assert "N/A" in user_content

    def test_prompt_lessons_none_equals_no_lessons(self) -> None:
        """Passing lessons=None behaves same as no lessons."""
        asset = _make_asset()
        signals = [_make_signal()]
        messages = build_decision_prompt(asset, signals, [], lessons=None)
        user_content = messages[1]["content"]
        assert "ASSET-SPECIFIC LESSONS" not in user_content
        assert "GENERAL LESSONS" not in user_content


class TestDDFlags:
    """Tests for DD flags injection into decision prompt."""

    def test_dd_flags_in_prompt(self) -> None:
        """DD flags appear in formatted prompt with severity and message."""
        asset = _make_asset()
        flags = [
            {"type": "insider_selling", "severity": "warning", "message": "Major holder decreased 8%"},
        ]
        result = _format_engine_data(asset, [], [], dd_flags=flags)
        assert "DUE DILIGENCE FLAGS:" in result
        assert "[WARNING]" in result
        assert "Major holder decreased 8%" in result

    def test_dd_flags_multiple(self) -> None:
        """Multiple DD flags all appear."""
        asset = _make_asset()
        flags = [
            {"severity": "warning", "message": "Insider selling detected"},
            {"severity": "info", "message": "New institutional buyer"},
        ]
        result = _format_engine_data(asset, [], [], dd_flags=flags)
        assert "[WARNING]" in result
        assert "[INFO]" in result
        assert "Insider selling detected" in result
        assert "New institutional buyer" in result

    def test_dd_flags_none_omits_section(self) -> None:
        """No DD flags means no DUE DILIGENCE FLAGS section."""
        asset = _make_asset()
        result = _format_engine_data(asset, [], [], dd_flags=None)
        assert "DUE DILIGENCE FLAGS" not in result

    def test_dd_flags_empty_list_omits_section(self) -> None:
        """Empty DD flags list means no DUE DILIGENCE FLAGS section."""
        asset = _make_asset()
        result = _format_engine_data(asset, [], [], dd_flags=[])
        assert "DUE DILIGENCE FLAGS" not in result

    def test_dd_flags_passed_through_build_decision_prompt(self) -> None:
        """build_decision_prompt passes dd_flags through to _format_engine_data."""
        asset = _make_asset()
        flags = [{"severity": "critical", "message": "High debt warning"}]
        messages = build_decision_prompt(asset, [], [], dd_flags=flags)
        user_content = messages[1]["content"]
        assert "DUE DILIGENCE FLAGS:" in user_content
        assert "[CRITICAL]" in user_content

    def test_dd_flags_default_severity(self) -> None:
        """Missing severity defaults to INFO."""
        asset = _make_asset()
        flags = [{"message": "Some info without severity"}]
        result = _format_engine_data(asset, [], [], dd_flags=flags)
        assert "[INFO]" in result
