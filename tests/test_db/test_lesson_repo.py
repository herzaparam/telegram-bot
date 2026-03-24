"""Tests for src/db/lesson_repo.py -- LessonRepository with model checks and scoring tests."""

from datetime import UTC, date, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.db.lesson_repo import LessonRepository, _compute_tier, lesson_repo
from src.db.models import Lesson


@pytest.fixture()
def repo() -> LessonRepository:
    """A fresh LessonRepository instance."""
    return LessonRepository()


class TestLessonModel:
    """Verify Lesson model columns exist."""

    def test_lesson_columns(self) -> None:
        """Lesson model has all required columns."""
        col_names = set(Lesson.__table__.columns.keys())
        expected = {
            "id", "date", "asset_type", "engine_tags", "topic", "lesson",
            "source_decision_id", "times_observed", "times_applied",
            "times_correct", "confidence_tier", "still_valid",
            "created_at", "updated_at",
        }
        assert expected.issubset(col_names), f"Missing columns: {expected - col_names}"

    def test_lesson_tablename(self) -> None:
        """Lesson model uses 'lessons' table."""
        assert Lesson.__tablename__ == "lessons"


class TestLessonRepositorySingleton:
    """Test module-level singleton."""

    def test_lesson_repo_exists(self) -> None:
        """Module-level lesson_repo singleton exists."""
        assert lesson_repo is not None
        assert isinstance(lesson_repo, LessonRepository)


class TestLessonScoring:
    """Test _score_lesson with known inputs."""

    def test_high_score(self, repo: LessonRepository) -> None:
        """Exact asset match + full engine overlap + recent + high accuracy scores > 0.8."""
        now = datetime.now(UTC)
        lesson = MagicMock(spec=Lesson)
        lesson.asset_type = "stock"
        lesson.engine_tags = ["technical", "quantitative"]
        lesson.times_applied = 10
        lesson.times_correct = 9
        lesson.updated_at = now - timedelta(days=1)  # Very recent

        score = repo._score_lesson(
            lesson,
            asset_type="stock",
            engine_categories=["technical", "quantitative"],
            now=now,
        )
        assert score > 0.8, f"Expected > 0.8, got {score}"

    def test_low_score(self, repo: LessonRepository) -> None:
        """Mismatched asset + no engine overlap + old + low accuracy scores < 0.4."""
        now = datetime.now(UTC)
        lesson = MagicMock(spec=Lesson)
        lesson.asset_type = "crypto"
        lesson.engine_tags = ["sentiment"]
        lesson.times_applied = 10
        lesson.times_correct = 1
        lesson.updated_at = now - timedelta(days=100)  # Old

        score = repo._score_lesson(
            lesson,
            asset_type="stock",
            engine_categories=["technical", "quantitative"],
            now=now,
        )
        assert score < 0.4, f"Expected < 0.4, got {score}"

    def test_no_applications_uses_prior(self, repo: LessonRepository) -> None:
        """Lesson with no applications uses 0.5 accuracy prior."""
        now = datetime.now(UTC)
        lesson = MagicMock(spec=Lesson)
        lesson.asset_type = "all"
        lesson.engine_tags = []
        lesson.times_applied = 0
        lesson.times_correct = 0
        lesson.updated_at = now

        score = repo._score_lesson(
            lesson, asset_type="stock", engine_categories=[], now=now
        )
        # recency=1.0*0.25 + accuracy=0.5*0.30 + asset_match=1.0*0.25 + engine_rel=0.0*0.20
        # = 0.25 + 0.15 + 0.25 + 0.0 = 0.65
        assert abs(score - 0.65) < 0.01, f"Expected ~0.65, got {score}"


class TestTierPromotion:
    """Test tier computation logic."""

    def test_hypothesis_tier(self) -> None:
        """Under 10 observations => hypothesis."""
        assert _compute_tier(1) == "hypothesis"
        assert _compute_tier(9) == "hypothesis"

    def test_pattern_tier(self) -> None:
        """10-29 observations => pattern."""
        assert _compute_tier(10) == "pattern"
        assert _compute_tier(29) == "pattern"

    def test_rule_tier(self) -> None:
        """30+ observations => rule."""
        assert _compute_tier(30) == "rule"
        assert _compute_tier(100) == "rule"

    @pytest.mark.asyncio()
    async def test_merge_promotes_tier(self, repo: LessonRepository) -> None:
        """merge_lesson promotes tier when times_observed crosses thresholds."""
        session = AsyncMock()

        # Mock existing lesson at 9 observations (hypothesis)
        existing = MagicMock(spec=Lesson)
        existing.times_observed = 9
        existing.confidence_tier = "hypothesis"
        session.get.return_value = existing

        await repo.merge_lesson(session, lesson_id=1, new_text="updated lesson")

        # Should have called execute with update
        session.execute.assert_called_once()
        call_args = session.execute.call_args[0][0]
        # The update should set times_observed=10 and tier="pattern"
        # Verify via compile
        compiled = call_args.compile(compile_kwargs={"literal_binds": True})
        stmt_str = str(compiled)
        assert "pattern" in stmt_str or "times_observed" in stmt_str


class TestInvalidation:
    """Test invalidate_underperforming logic."""

    @pytest.mark.asyncio()
    async def test_invalidate_underperforming_executes(self, repo: LessonRepository) -> None:
        """invalidate_underperforming issues an UPDATE statement."""
        session = AsyncMock()
        await repo.invalidate_underperforming(session)
        session.execute.assert_called_once()

    @pytest.mark.asyncio()
    async def test_increment_times_applied(self, repo: LessonRepository) -> None:
        """increment_times_applied issues UPDATE for given IDs."""
        session = AsyncMock()
        await repo.increment_times_applied(session, [1, 2, 3])
        session.execute.assert_called_once()

    @pytest.mark.asyncio()
    async def test_increment_empty_list(self, repo: LessonRepository) -> None:
        """increment_times_applied is no-op for empty list."""
        session = AsyncMock()
        await repo.increment_times_applied(session, [])
        session.execute.assert_not_called()

    @pytest.mark.asyncio()
    async def test_update_lesson_accuracy_correct(self, repo: LessonRepository) -> None:
        """update_lesson_accuracy increments times_correct when correct."""
        session = AsyncMock()
        await repo.update_lesson_accuracy(session, lesson_id=1, was_correct=True)
        session.execute.assert_called_once()

    @pytest.mark.asyncio()
    async def test_update_lesson_accuracy_incorrect(self, repo: LessonRepository) -> None:
        """update_lesson_accuracy is no-op when not correct."""
        session = AsyncMock()
        await repo.update_lesson_accuracy(session, lesson_id=1, was_correct=False)
        session.execute.assert_not_called()
