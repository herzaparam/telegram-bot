"""Repository for LLM trading decisions.

Uses SQLAlchemy ORM with PostgreSQL-specific UPSERT for idempotent writes.
"""

from __future__ import annotations

from datetime import date

from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import DailyDecision


class DecisionRepository:
    """Async repository for DailyDecision persistence with UPSERT semantics."""

    async def upsert_decision(
        self,
        session: AsyncSession,
        asset_id: int,
        decision_date: date,
        verdict: str,
        score: float,
        confidence: float,
        reasoning: str,
        key_factors: list[str],
        risk_warning: str | None,
        all_signals: dict[str, object],
        model_used: str,
    ) -> None:
        """Upsert a trading decision for an asset on a given date.

        Uses INSERT ... ON CONFLICT (asset_id, date) DO UPDATE
        to ensure idempotent writes when the pipeline is re-run.

        Args:
            session: An async SQLAlchemy session.
            asset_id: Database ID of the asset.
            decision_date: The date this decision applies to.
            verdict: Trading verdict (e.g., "BUY", "SELL").
            score: Decision score from -1.0 to 1.0.
            confidence: Confidence level from 0.0 to 1.0.
            reasoning: Human-readable explanation of the decision.
            key_factors: List of key factor strings.
            risk_warning: Risk warning text, or None.
            all_signals: Dict of all engine signals used.
            model_used: LLM model identifier.
        """
        stmt = pg_insert(DailyDecision).values(
            asset_id=asset_id,
            date=decision_date,
            verdict=verdict,
            score=score,
            confidence=confidence,
            reasoning=reasoning,
            key_factors=key_factors,
            risk_warning=risk_warning,
            all_signals=all_signals,
            model_used=model_used,
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=["asset_id", "date"],
            set_={
                "verdict": stmt.excluded.verdict,
                "score": stmt.excluded.score,
                "confidence": stmt.excluded.confidence,
                "reasoning": stmt.excluded.reasoning,
                "key_factors": stmt.excluded.key_factors,
                "risk_warning": stmt.excluded.risk_warning,
                "all_signals": stmt.excluded.all_signals,
                "model_used": stmt.excluded.model_used,
            },
        )
        await session.execute(stmt)

    async def update_lessons_applied(
        self,
        session: AsyncSession,
        asset_id: int,
        decision_date: date,
        lessons_applied: dict[str, str],
    ) -> None:
        """Update the lessons_applied JSONB on an existing decision.

        Args:
            session: Async SQLAlchemy session.
            asset_id: Asset database ID.
            decision_date: Decision date.
            lessons_applied: Dict mapping lesson ID (str) to lesson text.
        """
        stmt = (
            update(DailyDecision)
            .where(DailyDecision.asset_id == asset_id, DailyDecision.date == decision_date)
            .values(lessons_applied=lessons_applied)
        )
        await session.execute(stmt)

    async def get_decision(
        self,
        session: AsyncSession,
        asset_id: int,
        decision_date: date,
    ) -> DailyDecision | None:
        """Get a decision for an asset on a specific date.

        Args:
            session: An async SQLAlchemy session.
            asset_id: Database ID of the asset.
            decision_date: The date to query.

        Returns:
            DailyDecision instance or None if not found.
        """
        stmt = select(DailyDecision).where(
            DailyDecision.asset_id == asset_id,
            DailyDecision.date == decision_date,
        )
        result = await session.scalars(stmt)
        return result.one_or_none()


decision_repo = DecisionRepository()
