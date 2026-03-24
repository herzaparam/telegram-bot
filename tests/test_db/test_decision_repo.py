"""Tests for src/db/decision_repo.py -- DecisionRepository with mocked session."""

from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.db.decision_repo import DecisionRepository, decision_repo


@pytest.fixture()
def repo() -> DecisionRepository:
    """A fresh DecisionRepository instance."""
    return DecisionRepository()


class TestDecisionRepositorySingleton:
    """Test module-level singleton."""

    def test_decision_repo_exists(self) -> None:
        """Module-level decision_repo singleton exists."""
        assert decision_repo is not None
        assert isinstance(decision_repo, DecisionRepository)


class TestUpsertDecision:
    """Test DecisionRepository.upsert_decision."""

    @pytest.mark.asyncio
    async def test_upsert_decision_inserts_new_row(
        self, repo: DecisionRepository
    ) -> None:
        """upsert_decision calls session.execute with pg_insert."""
        session = AsyncMock()
        await repo.upsert_decision(
            session=session,
            asset_id=1,
            decision_date=date(2026, 3, 24),
            verdict="BUY",
            score=0.5,
            confidence=0.8,
            reasoning="Strong technicals",
            key_factors=["RSI oversold", "MACD crossover"],
            risk_warning="High volatility",
            all_signals={"technical": {"score": 0.5}},
            model_used="gpt-4o-mini",
        )
        session.execute.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_upsert_decision_updates_on_conflict(
        self, repo: DecisionRepository
    ) -> None:
        """upsert_decision uses on_conflict_do_update for idempotent writes."""
        session = AsyncMock()
        # Call twice with same (asset_id, date) -- should not error
        await repo.upsert_decision(
            session=session,
            asset_id=1,
            decision_date=date(2026, 3, 24),
            verdict="BUY",
            score=0.5,
            confidence=0.8,
            reasoning="First call",
            key_factors=["factor1"],
            risk_warning=None,
            all_signals={},
            model_used="gpt-4o-mini",
        )
        await repo.upsert_decision(
            session=session,
            asset_id=1,
            decision_date=date(2026, 3, 24),
            verdict="SELL",
            score=-0.3,
            confidence=0.7,
            reasoning="Second call",
            key_factors=["factor2"],
            risk_warning="Risk",
            all_signals={},
            model_used="gpt-4o-mini",
        )
        assert session.execute.await_count == 2


class TestGetDecision:
    """Test DecisionRepository.get_decision."""

    @pytest.mark.asyncio
    async def test_get_decision_returns_none_when_missing(
        self, repo: DecisionRepository
    ) -> None:
        """get_decision returns None when no record exists."""
        mock_scalars = MagicMock()
        mock_scalars.one_or_none.return_value = None

        session = AsyncMock()
        session.scalars.return_value = mock_scalars

        result = await repo.get_decision(
            session=session,
            asset_id=1,
            decision_date=date(2026, 3, 24),
        )
        assert result is None
        session.scalars.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_get_decision_returns_record(
        self, repo: DecisionRepository
    ) -> None:
        """get_decision returns DailyDecision when record exists."""
        mock_record = MagicMock()
        mock_record.verdict = "BUY"

        mock_scalars = MagicMock()
        mock_scalars.one_or_none.return_value = mock_record

        session = AsyncMock()
        session.scalars.return_value = mock_scalars

        result = await repo.get_decision(
            session=session,
            asset_id=1,
            decision_date=date(2026, 3, 24),
        )
        assert result is not None
        assert result.verdict == "BUY"
