"""Tests for src/db/evaluation_repo.py -- EvaluationRepository with mocked session."""

from datetime import date, datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.db.evaluation_repo import EvaluationRepository, evaluation_repo


@pytest.fixture()
def repo() -> EvaluationRepository:
    """A fresh EvaluationRepository instance."""
    return EvaluationRepository()


class TestEvaluationRepositorySingleton:
    """Test module-level singleton."""

    def test_evaluation_repo_exists(self) -> None:
        """Module-level evaluation_repo singleton exists."""
        assert evaluation_repo is not None
        assert isinstance(evaluation_repo, EvaluationRepository)


class TestEvaluationModel:
    """Test Evaluation model has required columns."""

    def test_evaluation_model_columns(self) -> None:
        """Evaluation model has all required columns."""
        from src.db.models import Evaluation

        mapper = Evaluation.__table__
        col_names = {c.name for c in mapper.columns}
        required = {
            "id", "decision_id", "window", "eval_price", "eval_price_at",
            "change_pct", "was_correct", "engine_results", "created_at",
        }
        assert required.issubset(col_names), f"Missing: {required - col_names}"

    def test_evaluation_tablename(self) -> None:
        """Evaluation model uses 'evaluations' table."""
        from src.db.models import Evaluation

        assert Evaluation.__tablename__ == "evaluations"


class TestAccuracyStatsModel:
    """Test AccuracyStats model has required columns."""

    def test_accuracy_stats_model_columns(self) -> None:
        """AccuracyStats model has all required columns."""
        from src.db.models import AccuracyStats

        mapper = AccuracyStats.__table__
        col_names = {c.name for c in mapper.columns}
        required = {
            "id", "asset_id", "engine_name", "window", "period",
            "total", "correct", "win_rate", "computed_at",
        }
        assert required.issubset(col_names), f"Missing: {required - col_names}"

    def test_accuracy_stats_tablename(self) -> None:
        """AccuracyStats model uses 'accuracy_stats' table."""
        from src.db.models import AccuracyStats

        assert AccuracyStats.__tablename__ == "accuracy_stats"


class TestIDXHolidayModel:
    """Test IDXHoliday model has required columns."""

    def test_idx_holiday_model_columns(self) -> None:
        """IDXHoliday model has all required columns."""
        from src.db.models import IDXHoliday

        mapper = IDXHoliday.__table__
        col_names = {c.name for c in mapper.columns}
        required = {"id", "holiday_date", "name", "year"}
        assert required.issubset(col_names), f"Missing: {required - col_names}"

    def test_idx_holiday_tablename(self) -> None:
        """IDXHoliday model uses 'idx_holidays' table."""
        from src.db.models import IDXHoliday

        assert IDXHoliday.__tablename__ == "idx_holidays"


class TestUpsertEvaluation:
    """Test EvaluationRepository.upsert_evaluation."""

    @pytest.mark.asyncio
    async def test_upsert_evaluation_creates_record(
        self, repo: EvaluationRepository
    ) -> None:
        """upsert_evaluation calls session.execute with pg_insert."""
        session = AsyncMock()
        now = datetime(2026, 3, 24, 10, 0, 0, tzinfo=timezone.utc)

        await repo.upsert_evaluation(
            session=session,
            decision_id=1,
            window="24h",
            eval_price=10500.0,
            eval_price_at=now,
            change_pct=2.5,
            was_correct=True,
            engine_results={"technical": {"score": 0.5, "correct": True}},
        )
        session.execute.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_upsert_evaluation_updates_on_conflict(
        self, repo: EvaluationRepository
    ) -> None:
        """upsert_evaluation with same (decision_id, window) updates instead of duplicating."""
        session = AsyncMock()
        now = datetime(2026, 3, 24, 10, 0, 0, tzinfo=timezone.utc)

        # Call twice with same decision_id + window
        await repo.upsert_evaluation(
            session=session, decision_id=1, window="24h",
            eval_price=10500.0, eval_price_at=now,
            change_pct=2.5, was_correct=True, engine_results=None,
        )
        await repo.upsert_evaluation(
            session=session, decision_id=1, window="24h",
            eval_price=10600.0, eval_price_at=now,
            change_pct=3.0, was_correct=True, engine_results=None,
        )
        assert session.execute.await_count == 2


class TestGetEvaluation:
    """Test EvaluationRepository.get_evaluation."""

    @pytest.mark.asyncio
    async def test_get_evaluation_returns_none(
        self, repo: EvaluationRepository
    ) -> None:
        """get_evaluation returns None when no record exists."""
        mock_scalars = MagicMock()
        mock_scalars.one_or_none.return_value = None

        session = AsyncMock()
        session.scalars.return_value = mock_scalars

        result = await repo.get_evaluation(session=session, decision_id=1, window="24h")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_evaluation_returns_record(
        self, repo: EvaluationRepository
    ) -> None:
        """get_evaluation returns Evaluation when record exists."""
        mock_record = MagicMock()
        mock_record.window = "24h"
        mock_record.was_correct = True

        mock_scalars = MagicMock()
        mock_scalars.one_or_none.return_value = mock_record

        session = AsyncMock()
        session.scalars.return_value = mock_scalars

        result = await repo.get_evaluation(session=session, decision_id=1, window="24h")
        assert result is not None
        assert result.was_correct is True


class TestRecomputeAccuracyStats:
    """Test EvaluationRepository.recompute_accuracy_stats."""

    @pytest.mark.asyncio
    async def test_recompute_accuracy_stats_calls_execute(
        self, repo: EvaluationRepository
    ) -> None:
        """recompute_accuracy_stats executes queries against the session."""
        session = AsyncMock()
        # Mock the various queries that recompute makes
        mock_result = MagicMock()
        mock_result.all.return_value = []
        mock_result.scalars.return_value = mock_result
        session.execute.return_value = mock_result

        await repo.recompute_accuracy_stats(session=session, asset_id=1)
        assert session.execute.await_count >= 1


class TestGetScorecardData:
    """Test EvaluationRepository.get_scorecard_data."""

    @pytest.mark.asyncio
    async def test_get_scorecard_data_returns_dict(
        self, repo: EvaluationRepository
    ) -> None:
        """get_scorecard_data returns dict with expected keys."""
        session = AsyncMock()
        mock_result = MagicMock()
        mock_result.all.return_value = []
        mock_result.scalars.return_value = mock_result
        session.execute.return_value = mock_result

        result = await repo.get_scorecard_data(session=session, period="30d")
        assert isinstance(result, dict)
        assert "win_rates_by_window" in result
        assert "total_decisions" in result


class TestGetBestWorstEngine:
    """Test EvaluationRepository.get_best_worst_engine."""

    @pytest.mark.asyncio
    async def test_get_best_worst_engine_returns_correct_names(
        self, repo: EvaluationRepository
    ) -> None:
        """get_best_worst_engine returns tuple of (best, worst) tuples."""
        session = AsyncMock()
        # Mock query results: best engine and worst engine
        mock_best = MagicMock()
        mock_best.engine_name = "technical"
        mock_best.win_rate = Decimal("75.00")
        mock_worst = MagicMock()
        mock_worst.engine_name = "sentiment"
        mock_worst.win_rate = Decimal("30.00")

        mock_result = MagicMock()
        mock_result.all.return_value = [mock_best, mock_worst]

        session.execute.return_value = mock_result

        best, worst = await repo.get_best_worst_engine(session=session, period="30d")
        assert best[0] == "technical"
        assert float(best[1]) == 75.00
        assert worst[0] == "sentiment"
        assert float(worst[1]) == 30.00


class TestGetRecentEvaluations:
    """Test EvaluationRepository.get_recent_evaluations."""

    @pytest.mark.asyncio
    async def test_get_recent_evaluations_ordered_desc(
        self, repo: EvaluationRepository
    ) -> None:
        """get_recent_evaluations returns evaluations ordered by created_at desc."""
        session = AsyncMock()
        mock_eval1 = MagicMock()
        mock_eval2 = MagicMock()

        mock_result = MagicMock()
        mock_result.all.return_value = [mock_eval1, mock_eval2]
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [mock_eval1, mock_eval2]
        session.scalars.return_value = mock_scalars

        result = await repo.get_recent_evaluations(
            session=session, window="24h", days_back=7
        )
        assert len(result) == 2


class TestIsIDXHoliday:
    """Test EvaluationRepository.is_idx_holiday."""

    @pytest.mark.asyncio
    async def test_is_idx_holiday_true(
        self, repo: EvaluationRepository
    ) -> None:
        """is_idx_holiday returns True for a known holiday date."""
        mock_scalars = MagicMock()
        mock_scalars.one_or_none.return_value = MagicMock()  # record exists

        session = AsyncMock()
        session.scalars.return_value = mock_scalars

        result = await repo.is_idx_holiday(session=session, check_date=date(2026, 1, 1))
        assert result is True

    @pytest.mark.asyncio
    async def test_is_idx_holiday_false(
        self, repo: EvaluationRepository
    ) -> None:
        """is_idx_holiday returns False for a normal trading day."""
        mock_scalars = MagicMock()
        mock_scalars.one_or_none.return_value = None

        session = AsyncMock()
        session.scalars.return_value = mock_scalars

        result = await repo.is_idx_holiday(session=session, check_date=date(2026, 3, 24))
        assert result is False
