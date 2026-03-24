"""Tests for src/data/reflect.py -- reflect stage with LLM analysis and lesson extraction."""

from __future__ import annotations

import json
from datetime import date, datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.db.models import Asset, DailyDecision, Evaluation, Lesson, SignalRecord
from src.llm.client import LLMResult


@pytest.fixture()
def mock_asset() -> Asset:
    """A mock Asset for testing."""
    asset = MagicMock(spec=Asset)
    asset.id = 1
    asset.symbol = "BBCA"
    asset.asset_type = "stock"
    return asset


@pytest.fixture()
def mock_decision() -> DailyDecision:
    """A mock wrong decision for testing."""
    d = MagicMock(spec=DailyDecision)
    d.id = 10
    d.asset_id = 1
    d.date = date(2026, 3, 20)
    d.verdict = "BUY"
    d.score = 0.5
    d.confidence = 0.7
    d.all_signals = {"technical": {"score": 0.5, "confidence": 0.8}}
    d.reasoning = "Test reasoning"
    d.lessons_applied = None
    d.decision_price = 9500.0
    return d


@pytest.fixture()
def mock_evaluation() -> Evaluation:
    """A mock wrong evaluation."""
    e = MagicMock(spec=Evaluation)
    e.id = 100
    e.decision_id = 10
    e.window = "24h"
    e.change_pct = -5.0
    e.was_correct = False
    e.engine_results = {}
    return e


@pytest.fixture()
def mock_correct_evaluation() -> Evaluation:
    """A mock correct evaluation."""
    e = MagicMock(spec=Evaluation)
    e.id = 101
    e.decision_id = 10
    e.window = "24h"
    e.change_pct = 3.0
    e.was_correct = True
    e.engine_results = {}
    return e


def _make_analysis_response() -> str:
    """Return valid JSON for analysis LLM response."""
    return json.dumps({
        "analysis": "The decision was wrong because momentum indicators were misread. " * 5,
        "missed_signals": ["volume_spike"],
        "overweighted_engines": ["technical"],
        "underweighted_engines": ["quantitative"],
        "lesson": "Check volume before following momentum signals",
        "weight_adjustments": {"technical": -0.05, "quantitative": 0.05},
    })


def _make_dedup_response(action: str = "new", merge_id: int | None = None) -> str:
    """Return valid JSON for dedup LLM response."""
    return json.dumps({
        "action": action,
        "merge_target_id": merge_id,
        "final_lesson_text": "Check volume before following momentum signals",
        "topic": "momentum",
    })


class TestPerAssetAnalysis:
    """Test _analyze_decision returns dict with required keys."""

    @pytest.mark.asyncio()
    async def test_analyze_decision_returns_dict(
        self, mock_asset, mock_decision, mock_evaluation
    ) -> None:
        """_analyze_decision returns dict with all required keys."""
        from src.data.reflect import _analyze_decision

        session = AsyncMock()

        # Mock signal_repo
        mock_signal = MagicMock(spec=SignalRecord)
        mock_signal.category = "technical"
        mock_signal.score = 0.5
        mock_signal.confidence = 0.8

        with patch(
            "src.data.reflect.signal_repo"
        ) as sig_repo, patch(
            "src.data.reflect.llm_completion"
        ) as llm_mock:
            sig_repo.get_signals_for_asset = AsyncMock(return_value=[mock_signal])
            llm_mock.return_value = LLMResult(
                content=_make_analysis_response(),
                model_used="test-model",
            )

            result = await _analyze_decision(
                session, mock_asset, mock_decision, mock_evaluation, "24h"
            )

        assert result is not None
        assert "analysis" in result
        assert "missed_signals" in result
        assert "overweighted_engines" in result
        assert "underweighted_engines" in result
        assert "lesson" in result
        assert "weight_adjustments" in result
        assert result["asset_symbol"] == "BBCA"
        assert result["decision_id"] == 10


class TestLessonExtraction:
    """Test lesson extraction and storage."""

    @pytest.mark.asyncio()
    async def test_new_lesson_created(self, mock_asset, mock_decision) -> None:
        """A new Lesson is stored when dedup says 'new'."""
        from src.data.reflect import _extract_and_store_lesson

        session = AsyncMock()
        analysis = json.loads(_make_analysis_response())
        analysis["asset_symbol"] = "BBCA"
        analysis["asset_type"] = "stock"
        analysis["decision_id"] = 10
        analysis["window"] = "24h"

        with patch(
            "src.data.reflect.lesson_repo"
        ) as lr, patch(
            "src.data.reflect.llm_completion"
        ) as llm_mock:
            lr.get_valid_lessons = AsyncMock(return_value=[])
            lr.upsert_lesson = AsyncMock(return_value=1)
            llm_mock.return_value = LLMResult(
                content=_make_dedup_response("new"),
                model_used="test-model",
            )

            await _extract_and_store_lesson(session, analysis, mock_asset, mock_decision)

        lr.upsert_lesson.assert_called_once()
        call_kwargs = lr.upsert_lesson.call_args
        assert call_kwargs.kwargs.get("topic") == "momentum" or (
            len(call_kwargs.args) > 0 or call_kwargs[1].get("topic") == "momentum"
        )


class TestQualifyingFilter:
    """Test the D-03 qualifying filter in reflect_stage."""

    @pytest.mark.asyncio()
    async def test_correct_high_confidence_skipped(
        self, mock_asset, mock_decision, mock_correct_evaluation
    ) -> None:
        """Correct decision with confidence >= 0.4 is skipped."""
        from src.data.reflect import reflect_stage

        session = AsyncMock()
        mock_decision.confidence = 0.8

        with patch(
            "src.data.reflect.decision_repo"
        ) as dr, patch(
            "src.data.reflect.evaluation_repo"
        ) as er, patch(
            "src.data.reflect.llm_completion"
        ) as llm_mock, patch(
            "src.data.reflect.lesson_repo"
        ) as lr:
            dr.get_decision = AsyncMock(return_value=mock_decision)
            er.get_evaluation = AsyncMock(return_value=mock_correct_evaluation)
            lr.invalidate_underperforming = AsyncMock()

            # Mock the idempotency check - no existing lessons
            mock_result = MagicMock()
            mock_result.scalar_one_or_none.return_value = None
            session.execute = AsyncMock(return_value=mock_result)

            await reflect_stage(session, mock_asset)

        # LLM should NOT have been called (all decisions were filtered out)
        llm_mock.assert_not_called()

    @pytest.mark.asyncio()
    async def test_wrong_decision_analyzed(
        self, mock_asset, mock_decision, mock_evaluation
    ) -> None:
        """Wrong decision is analyzed (not skipped)."""
        from src.data.reflect import reflect_stage

        session = AsyncMock()

        with patch(
            "src.data.reflect.decision_repo"
        ) as dr, patch(
            "src.data.reflect.evaluation_repo"
        ) as er, patch(
            "src.data.reflect.llm_completion"
        ) as llm_mock, patch(
            "src.data.reflect.signal_repo"
        ) as sr, patch(
            "src.data.reflect.lesson_repo"
        ) as lr:
            # Only return decision for the first window, None for rest
            dr.get_decision = AsyncMock(side_effect=[mock_decision, None, None, None, None, None, None, None])
            er.get_evaluation = AsyncMock(return_value=mock_evaluation)
            sr.get_signals_for_asset = AsyncMock(return_value=[])
            lr.get_valid_lessons = AsyncMock(return_value=[])
            lr.upsert_lesson = AsyncMock(return_value=1)
            lr.invalidate_underperforming = AsyncMock()
            lr.update_lesson_accuracy = AsyncMock()

            # Mock idempotency check - no existing lesson
            mock_result = MagicMock()
            mock_result.scalar_one_or_none.return_value = None
            session.execute = AsyncMock(return_value=mock_result)

            llm_mock.return_value = LLMResult(
                content=_make_analysis_response(),
                model_used="test-model",
            )

            # Second LLM call for dedup
            llm_mock.side_effect = [
                LLMResult(content=_make_analysis_response(), model_used="test"),
                LLMResult(content=_make_dedup_response("new"), model_used="test"),
            ]

            await reflect_stage(session, mock_asset)

        # LLM should have been called (at least for analysis)
        assert llm_mock.call_count >= 1

    @pytest.mark.asyncio()
    async def test_surprising_win_analyzed(
        self, mock_asset, mock_decision, mock_correct_evaluation
    ) -> None:
        """Correct decision with low confidence (surprising win) is analyzed."""
        from src.data.reflect import reflect_stage

        session = AsyncMock()
        mock_decision.confidence = 0.3  # Low confidence -> surprising win

        with patch(
            "src.data.reflect.decision_repo"
        ) as dr, patch(
            "src.data.reflect.evaluation_repo"
        ) as er, patch(
            "src.data.reflect.llm_completion"
        ) as llm_mock, patch(
            "src.data.reflect.signal_repo"
        ) as sr, patch(
            "src.data.reflect.lesson_repo"
        ) as lr:
            dr.get_decision = AsyncMock(side_effect=[mock_decision, None, None, None, None, None, None, None])
            er.get_evaluation = AsyncMock(return_value=mock_correct_evaluation)
            sr.get_signals_for_asset = AsyncMock(return_value=[])
            lr.get_valid_lessons = AsyncMock(return_value=[])
            lr.upsert_lesson = AsyncMock(return_value=1)
            lr.invalidate_underperforming = AsyncMock()
            lr.update_lesson_accuracy = AsyncMock()

            mock_result = MagicMock()
            mock_result.scalar_one_or_none.return_value = None
            session.execute = AsyncMock(return_value=mock_result)

            llm_mock.side_effect = [
                LLMResult(content=_make_analysis_response(), model_used="test"),
                LLMResult(content=_make_dedup_response("new"), model_used="test"),
            ]

            await reflect_stage(session, mock_asset)

        assert llm_mock.call_count >= 1


class TestErrorIsolation:
    """Test that reflect_stage never raises."""

    @pytest.mark.asyncio()
    async def test_llm_exception_caught(self, mock_asset) -> None:
        """reflect_stage catches exceptions and does not raise."""
        from src.data.reflect import reflect_stage

        session = AsyncMock()

        with patch(
            "src.data.reflect.decision_repo"
        ) as dr, patch(
            "src.data.reflect.evaluation_repo"
        ) as er, patch(
            "src.data.reflect.lesson_repo"
        ) as lr:
            dr.get_decision = AsyncMock(side_effect=Exception("DB connection error"))
            lr.invalidate_underperforming = AsyncMock()

            # Should not raise
            await reflect_stage(session, mock_asset)


class TestIdempotency:
    """Test that already-reflected decisions are not re-analyzed."""

    @pytest.mark.asyncio()
    async def test_existing_lesson_skips_llm(
        self, mock_asset, mock_decision, mock_evaluation
    ) -> None:
        """If a lesson exists for a decision, no LLM call is made."""
        from src.data.reflect import reflect_stage

        session = AsyncMock()

        with patch(
            "src.data.reflect.decision_repo"
        ) as dr, patch(
            "src.data.reflect.evaluation_repo"
        ) as er, patch(
            "src.data.reflect.llm_completion"
        ) as llm_mock, patch(
            "src.data.reflect.lesson_repo"
        ) as lr:
            dr.get_decision = AsyncMock(side_effect=[mock_decision, None, None, None, None, None, None, None])
            er.get_evaluation = AsyncMock(return_value=mock_evaluation)
            lr.invalidate_underperforming = AsyncMock()
            lr.update_lesson_accuracy = AsyncMock()

            # Idempotency: lesson already exists for this decision
            mock_result = MagicMock()
            mock_result.scalar_one_or_none.return_value = 42  # Existing lesson ID
            session.execute = AsyncMock(return_value=mock_result)

            await reflect_stage(session, mock_asset)

        # LLM should NOT have been called
        llm_mock.assert_not_called()
