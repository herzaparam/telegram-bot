"""Tests for src/data/decide.py -- decide stage with fallback, parsing, contradiction detection."""

from __future__ import annotations

import json
from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.data.decide import (
    DecisionResult,
    VALID_VERDICTS,
    _detect_contradictions,
    _deterministic_fallback,
    _parse_llm_response,
    _score_to_verdict,
    decide_stage,
)
from src.llm.client import LLM_UNAVAILABLE, LLMResult
from src.llm.prompts import build_decision_prompt


def _make_signal(
    category: str = "technical",
    score: float = 0.5,
    confidence: float = 0.8,
    indicators: dict | None = None,
) -> MagicMock:
    """Create a mock SignalRecord with the given attributes."""
    sig = MagicMock()
    sig.category = category
    sig.score = score
    sig.confidence = confidence
    sig.reasoning = f"{category} reasoning"
    sig.indicators = indicators or {"rsi_14": 55}
    sig.data_quality = {"sources_available": ["yfinance"]}
    return sig


def _make_asset(
    symbol: str = "BBCA",
    name: str = "Bank Central Asia",
    asset_type: str = "stock",
    asset_id: int = 1,
) -> MagicMock:
    """Create a mock Asset."""
    asset = MagicMock()
    asset.id = asset_id
    asset.symbol = symbol
    asset.name = name
    asset.asset_type = asset_type
    return asset


class TestContradictionDetection:
    """Test _detect_contradictions function."""

    def test_opposite_scores_high_confidence_detected(self) -> None:
        """Signals with opposite scores (>0.3, <-0.3) and high confidence produce contradiction."""
        signals = [
            _make_signal(category="technical", score=0.5, confidence=0.7),
            _make_signal(category="quantitative", score=-0.5, confidence=0.7),
        ]
        result = _detect_contradictions(signals)
        assert len(result) == 1
        assert "technical" in result[0]
        assert "quantitative" in result[0]

    def test_same_direction_no_contradiction(self) -> None:
        """Two positive signals produce no contradiction."""
        signals = [
            _make_signal(category="technical", score=0.5, confidence=0.7),
            _make_signal(category="quantitative", score=0.3, confidence=0.8),
        ]
        result = _detect_contradictions(signals)
        assert len(result) == 0

    def test_low_confidence_no_contradiction(self) -> None:
        """Opposite scores but low confidence do not trigger contradiction."""
        signals = [
            _make_signal(category="technical", score=0.5, confidence=0.3),
            _make_signal(category="quantitative", score=-0.5, confidence=0.3),
        ]
        result = _detect_contradictions(signals)
        assert len(result) == 0

    def test_scores_below_threshold_no_contradiction(self) -> None:
        """+0.2 and -0.2 do not trigger contradiction (below 0.3 threshold)."""
        signals = [
            _make_signal(category="technical", score=0.2, confidence=0.8),
            _make_signal(category="quantitative", score=-0.2, confidence=0.8),
        ]
        result = _detect_contradictions(signals)
        assert len(result) == 0


class TestDeterministicFallback:
    """Test _deterministic_fallback function."""

    def test_empty_signals_returns_hold(self) -> None:
        """Empty signals list returns HOLD with score=0.0, confidence=0.0."""
        result = _deterministic_fallback([])
        assert result.verdict == "HOLD"
        assert result.score == 0.0
        assert result.confidence == 0.0

    def test_strong_buy_threshold(self) -> None:
        """Weighted score >0.6 returns STRONG BUY."""
        signals = [_make_signal(score=0.8, confidence=1.0)]
        result = _deterministic_fallback(signals)
        assert result.verdict == "STRONG BUY"

    def test_buy_threshold(self) -> None:
        """Weighted score ~0.3 returns BUY."""
        signals = [_make_signal(score=0.3, confidence=1.0)]
        result = _deterministic_fallback(signals)
        assert result.verdict == "BUY"

    def test_hold_threshold(self) -> None:
        """Weighted score ~0.0 returns HOLD."""
        signals = [_make_signal(score=0.0, confidence=1.0)]
        result = _deterministic_fallback(signals)
        assert result.verdict == "HOLD"

    def test_sell_threshold(self) -> None:
        """Weighted score ~-0.3 returns SELL."""
        signals = [_make_signal(score=-0.3, confidence=1.0)]
        result = _deterministic_fallback(signals)
        assert result.verdict == "SELL"

    def test_strong_sell_threshold(self) -> None:
        """Weighted score <-0.6 returns STRONG SELL."""
        signals = [_make_signal(score=-0.8, confidence=1.0)]
        result = _deterministic_fallback(signals)
        assert result.verdict == "STRONG SELL"

    def test_confidence_capped_at_05(self) -> None:
        """Result confidence never exceeds 0.5."""
        signals = [_make_signal(score=0.5, confidence=1.0)]
        result = _deterministic_fallback(signals)
        assert result.confidence <= 0.5

    def test_reasoning_contains_deterministic(self) -> None:
        """Reasoning contains 'Deterministic fallback'."""
        signals = [_make_signal(score=0.5, confidence=0.8)]
        result = _deterministic_fallback(signals)
        assert "Deterministic fallback" in result.reasoning

    def test_risk_warning_present(self) -> None:
        """Risk warning contains 'LLM unavailable'."""
        signals = [_make_signal(score=0.5, confidence=0.8)]
        result = _deterministic_fallback(signals)
        assert "LLM unavailable" in result.risk_warning


class TestResponseParsing:
    """Test _parse_llm_response function."""

    def _valid_json(self, **overrides: object) -> str:
        """Create a valid JSON response string."""
        data = {
            "verdict": "BUY",
            "score": 0.5,
            "confidence": 0.8,
            "reasoning": "Strong technicals",
            "key_factors": ["RSI oversold", "MACD crossover"],
            "risk_warning": "High volatility",
        }
        data.update(overrides)
        return json.dumps(data)

    def test_valid_json_parsed(self) -> None:
        """All fields present returns DecisionResult."""
        signals = [_make_signal()]
        result = _parse_llm_response(self._valid_json(), signals)
        assert result is not None
        assert isinstance(result, DecisionResult)
        assert result.verdict == "BUY"
        assert result.score == 0.5
        assert result.confidence == 0.8

    def test_score_clamped(self) -> None:
        """Score=2.0 is clamped to 1.0."""
        signals = [_make_signal()]
        result = _parse_llm_response(self._valid_json(score=2.0), signals)
        assert result is not None
        assert result.score == 1.0

    def test_confidence_clamped(self) -> None:
        """Confidence=1.5 is clamped to 1.0."""
        signals = [_make_signal()]
        result = _parse_llm_response(self._valid_json(confidence=1.5), signals)
        assert result is not None
        assert result.confidence == 1.0

    def test_invalid_verdict_returns_none(self) -> None:
        """verdict='maybe' returns None."""
        signals = [_make_signal()]
        result = _parse_llm_response(self._valid_json(verdict="maybe"), signals)
        assert result is None

    def test_missing_field_returns_none(self) -> None:
        """Missing 'reasoning' key returns None."""
        signals = [_make_signal()]
        data = json.loads(self._valid_json())
        del data["reasoning"]
        result = _parse_llm_response(json.dumps(data), signals)
        assert result is None

    def test_invalid_json_returns_none(self) -> None:
        """Non-JSON string returns None."""
        signals = [_make_signal()]
        result = _parse_llm_response("not json at all", signals)
        assert result is None


class TestDecideStage:
    """Test the decide_stage async function."""

    @pytest.mark.asyncio
    @patch("src.data.decide.lesson_repo")
    @patch("src.data.decide.decision_repo")
    @patch("src.data.decide.llm_completion")
    @patch("src.data.decide.signal_repo")
    async def test_no_signals_returns_early(
        self,
        mock_signal_repo: MagicMock,
        mock_llm: MagicMock,
        mock_decision_repo: MagicMock,
        mock_lesson_repo: MagicMock,
    ) -> None:
        """No signals: no LLM call, no decision stored."""
        mock_signal_repo.get_signals_for_asset = AsyncMock(return_value=[])
        session = AsyncMock()
        asset = _make_asset()

        await decide_stage(session, asset)

        mock_llm.assert_not_called()
        mock_decision_repo.upsert_decision.assert_not_called()

    @pytest.mark.asyncio
    @patch("src.data.decide.lesson_repo")
    @patch("src.data.decide.decision_repo")
    @patch("src.data.decide.llm_completion")
    @patch("src.data.decide.signal_repo")
    async def test_llm_success_stores_decision(
        self,
        mock_signal_repo: MagicMock,
        mock_llm: MagicMock,
        mock_decision_repo: MagicMock,
        mock_lesson_repo: MagicMock,
    ) -> None:
        """LLM returns valid JSON: decision is parsed and stored."""
        signals = [_make_signal(score=0.5, confidence=0.8)]
        mock_signal_repo.get_signals_for_asset = AsyncMock(return_value=signals)
        mock_lesson_repo.get_relevant_lessons = AsyncMock(return_value=[])

        valid_response = json.dumps({
            "verdict": "BUY",
            "score": 0.5,
            "confidence": 0.8,
            "reasoning": "Strong technicals",
            "key_factors": ["RSI oversold"],
            "risk_warning": None,
        })
        mock_llm.return_value = LLMResult(content=valid_response, model_used="gpt-4o-mini")
        mock_decision_repo.upsert_decision = AsyncMock()

        session = AsyncMock()
        asset = _make_asset()

        await decide_stage(session, asset)

        mock_decision_repo.upsert_decision.assert_awaited_once()
        call_kwargs = mock_decision_repo.upsert_decision.call_args
        assert call_kwargs[1]["verdict"] == "BUY" or call_kwargs[0][3] == "BUY"

    @pytest.mark.asyncio
    @patch("src.data.decide.lesson_repo")
    @patch("src.data.decide.decision_repo")
    @patch("src.data.decide.llm_completion")
    @patch("src.data.decide.signal_repo")
    async def test_llm_unavailable_uses_fallback(
        self,
        mock_signal_repo: MagicMock,
        mock_llm: MagicMock,
        mock_decision_repo: MagicMock,
        mock_lesson_repo: MagicMock,
    ) -> None:
        """LLM returns LLM_UNAVAILABLE: deterministic fallback is used."""
        signals = [_make_signal(score=0.5, confidence=0.8)]
        mock_signal_repo.get_signals_for_asset = AsyncMock(return_value=signals)
        mock_lesson_repo.get_relevant_lessons = AsyncMock(return_value=[])
        mock_llm.return_value = LLM_UNAVAILABLE
        mock_decision_repo.upsert_decision = AsyncMock()

        session = AsyncMock()
        asset = _make_asset()

        await decide_stage(session, asset)

        mock_decision_repo.upsert_decision.assert_awaited_once()
        call_kwargs = mock_decision_repo.upsert_decision.call_args
        # Fallback stores model_used="none"
        assert "none" in str(call_kwargs)

    @pytest.mark.asyncio
    @patch("src.data.decide.lesson_repo")
    @patch("src.data.decide.decision_repo")
    @patch("src.data.decide.llm_completion")
    @patch("src.data.decide.signal_repo")
    async def test_malformed_json_retries_then_fallback(
        self,
        mock_signal_repo: MagicMock,
        mock_llm: MagicMock,
        mock_decision_repo: MagicMock,
        mock_lesson_repo: MagicMock,
    ) -> None:
        """Malformed JSON twice: retries once, then falls back with LLM_PARSE_ERROR."""
        signals = [_make_signal(score=0.3, confidence=0.8)]
        mock_signal_repo.get_signals_for_asset = AsyncMock(return_value=signals)
        mock_lesson_repo.get_relevant_lessons = AsyncMock(return_value=[])
        # Both calls return malformed JSON
        mock_llm.side_effect = [
            LLMResult(content="not json", model_used="gpt-4o-mini"),
            LLMResult(content="still not json", model_used="gpt-4o-mini"),
        ]
        mock_decision_repo.upsert_decision = AsyncMock()

        session = AsyncMock()
        asset = _make_asset()

        await decide_stage(session, asset)

        # LLM called twice (initial + retry)
        assert mock_llm.call_count == 2
        mock_decision_repo.upsert_decision.assert_awaited_once()
        # Fallback verdict stored
        call_str = str(mock_decision_repo.upsert_decision.call_args)
        assert "LLM_PARSE_ERROR" in call_str or "fallback" in call_str.lower()


class TestLessonInjection:
    """Tests for lesson injection into the decide stage."""

    @pytest.mark.asyncio
    @patch("src.data.decide.lesson_repo")
    @patch("src.data.decide.decision_repo")
    @patch("src.data.decide.llm_completion")
    @patch("src.data.decide.signal_repo")
    async def test_lessons_queried_and_injected(
        self,
        mock_signal_repo: MagicMock,
        mock_llm: MagicMock,
        mock_decision_repo: MagicMock,
        mock_lesson_repo: MagicMock,
    ) -> None:
        """Relevant lessons are queried and passed to build_decision_prompt."""
        signals = [_make_signal(score=0.5, confidence=0.8)]
        mock_signal_repo.get_signals_for_asset = AsyncMock(return_value=signals)

        # Create mock Lesson objects
        lesson1 = MagicMock()
        lesson1.id = 1
        lesson1.lesson = "RSI reversal pattern"
        lesson1.asset_type = "stock"
        lesson1.engine_tags = ["technical"]
        lesson1.times_applied = 10
        lesson1.times_correct = 7

        lesson2 = MagicMock()
        lesson2.id = 2
        lesson2.lesson = "Momentum divergence warning"
        lesson2.asset_type = "all"
        lesson2.engine_tags = ["quantitative"]
        lesson2.times_applied = 5
        lesson2.times_correct = 3

        mock_lesson_repo.get_relevant_lessons = AsyncMock(return_value=[lesson1, lesson2])
        mock_lesson_repo.increment_times_applied = AsyncMock()

        valid_response = json.dumps({
            "verdict": "BUY",
            "score": 0.5,
            "confidence": 0.8,
            "reasoning": "Strong technicals",
            "key_factors": ["RSI oversold"],
            "risk_warning": None,
        })
        mock_llm.return_value = LLMResult(content=valid_response, model_used="gpt-4o-mini")
        mock_decision_repo.upsert_decision = AsyncMock()
        mock_decision_repo.update_lessons_applied = AsyncMock()

        session = AsyncMock()
        asset = _make_asset()

        with patch("src.data.decide.build_decision_prompt", wraps=build_decision_prompt) as mock_build:
            await decide_stage(session, asset)
            # Verify lessons were passed to the prompt builder
            call_kwargs = mock_build.call_args
            lessons_arg = call_kwargs[1].get("lessons") or call_kwargs[0][3] if len(call_kwargs[0]) > 3 else call_kwargs[1].get("lessons")
            assert lessons_arg is not None
            assert len(lessons_arg) == 2

    @pytest.mark.asyncio
    @patch("src.data.decide.lesson_repo")
    @patch("src.data.decide.decision_repo")
    @patch("src.data.decide.llm_completion")
    @patch("src.data.decide.signal_repo")
    async def test_lessons_applied_recorded(
        self,
        mock_signal_repo: MagicMock,
        mock_llm: MagicMock,
        mock_decision_repo: MagicMock,
        mock_lesson_repo: MagicMock,
    ) -> None:
        """After decide_stage completes, lessons_applied is recorded and counters incremented."""
        signals = [_make_signal(score=0.5, confidence=0.8)]
        mock_signal_repo.get_signals_for_asset = AsyncMock(return_value=signals)

        lesson1 = MagicMock()
        lesson1.id = 1
        lesson1.lesson = "RSI reversal"
        lesson1.asset_type = "stock"
        lesson1.engine_tags = ["technical"]
        lesson1.times_applied = 10
        lesson1.times_correct = 7

        mock_lesson_repo.get_relevant_lessons = AsyncMock(return_value=[lesson1])
        mock_lesson_repo.increment_times_applied = AsyncMock()

        valid_response = json.dumps({
            "verdict": "BUY",
            "score": 0.5,
            "confidence": 0.8,
            "reasoning": "Strong technicals",
            "key_factors": ["RSI oversold"],
            "risk_warning": None,
        })
        mock_llm.return_value = LLMResult(content=valid_response, model_used="gpt-4o-mini")
        mock_decision_repo.upsert_decision = AsyncMock()
        mock_decision_repo.update_lessons_applied = AsyncMock()

        session = AsyncMock()
        asset = _make_asset()

        await decide_stage(session, asset)

        mock_decision_repo.update_lessons_applied.assert_awaited_once()
        call_args = mock_decision_repo.update_lessons_applied.call_args
        lessons_applied_data = call_args[1].get("lessons_applied") or call_args[0][3]
        assert "1" in lessons_applied_data
        assert lessons_applied_data["1"] == "RSI reversal"

        mock_lesson_repo.increment_times_applied.assert_awaited_once()
        increment_args = mock_lesson_repo.increment_times_applied.call_args
        lesson_ids = increment_args[1].get("lesson_ids") or increment_args[0][1]
        assert lesson_ids == [1]

    @pytest.mark.asyncio
    @patch("src.data.decide.lesson_repo")
    @patch("src.data.decide.decision_repo")
    @patch("src.data.decide.llm_completion")
    @patch("src.data.decide.signal_repo")
    async def test_no_lessons_available(
        self,
        mock_signal_repo: MagicMock,
        mock_llm: MagicMock,
        mock_decision_repo: MagicMock,
        mock_lesson_repo: MagicMock,
    ) -> None:
        """No relevant lessons: build_decision_prompt called with lessons=None."""
        signals = [_make_signal(score=0.5, confidence=0.8)]
        mock_signal_repo.get_signals_for_asset = AsyncMock(return_value=signals)
        mock_lesson_repo.get_relevant_lessons = AsyncMock(return_value=[])

        valid_response = json.dumps({
            "verdict": "BUY",
            "score": 0.5,
            "confidence": 0.8,
            "reasoning": "Strong technicals",
            "key_factors": ["RSI oversold"],
            "risk_warning": None,
        })
        mock_llm.return_value = LLMResult(content=valid_response, model_used="gpt-4o-mini")
        mock_decision_repo.upsert_decision = AsyncMock()

        session = AsyncMock()
        asset = _make_asset()

        with patch("src.data.decide.build_decision_prompt", wraps=build_decision_prompt) as mock_build:
            await decide_stage(session, asset)
            call_kwargs = mock_build.call_args
            lessons_arg = call_kwargs[1].get("lessons")
            assert lessons_arg is None

        # No lessons_applied update should happen
        mock_decision_repo.update_lessons_applied = AsyncMock()
        # Already ran; check it was not called during the stage
        # (it wasn't mocked before the call, so check lesson_repo.increment was not called)
        mock_lesson_repo.increment_times_applied.assert_not_called()
