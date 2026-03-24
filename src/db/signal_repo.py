"""Repository for engine-generated trading signals.

Uses SQLAlchemy ORM with PostgreSQL-specific UPSERT for idempotent writes.
"""

from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import SignalRecord
from src.engines.base import Signal


class SignalRepository:
    """Async repository for Signal persistence with UPSERT semantics."""

    async def upsert_signals(
        self,
        session: AsyncSession,
        asset_id: int,
        signal_date: date,
        signals: list[Signal],
        price_at_signal: float,
    ) -> int:
        """Upsert engine signals for an asset on a given date.

        Uses INSERT ... ON CONFLICT (asset_id, date, category) DO UPDATE
        to ensure idempotent writes when the pipeline is re-run.

        Args:
            session: An async SQLAlchemy session.
            asset_id: Database ID of the asset.
            signal_date: The date these signals apply to.
            signals: List of Signal dataclass instances from engines.
            price_at_signal: Asset price at the time signals were generated.

        Returns:
            Number of signals upserted.
        """
        for sig in signals:
            stmt = pg_insert(SignalRecord).values(
                asset_id=asset_id,
                date=signal_date,
                category=sig.category,
                score=sig.score,
                confidence=sig.confidence,
                reasoning=sig.reasoning,
                indicators=sig.indicators,
                data_quality=sig.data_quality,
                price_at_signal=price_at_signal,
            )
            stmt = stmt.on_conflict_do_update(
                index_elements=["asset_id", "date", "category"],
                set_={
                    "score": stmt.excluded.score,
                    "confidence": stmt.excluded.confidence,
                    "reasoning": stmt.excluded.reasoning,
                    "indicators": stmt.excluded.indicators,
                    "data_quality": stmt.excluded.data_quality,
                    "price_at_signal": stmt.excluded.price_at_signal,
                },
            )
            await session.execute(stmt)

        return len(signals)

    async def get_signals_for_asset(
        self,
        session: AsyncSession,
        asset_id: int,
        signal_date: date,
    ) -> list[SignalRecord]:
        """Get all signals for an asset on a specific date.

        Args:
            session: An async SQLAlchemy session.
            asset_id: Database ID of the asset.
            signal_date: The date to query.

        Returns:
            List of SignalRecord instances.
        """
        stmt = (
            select(SignalRecord)
            .where(SignalRecord.asset_id == asset_id, SignalRecord.date == signal_date)
            .order_by(SignalRecord.category)
        )
        result = await session.scalars(stmt)
        return list(result.all())

    async def get_latest_signals(
        self,
        session: AsyncSession,
        asset_id: int,
        limit: int = 30,
    ) -> list[SignalRecord]:
        """Get the most recent signals for an asset.

        Args:
            session: An async SQLAlchemy session.
            asset_id: Database ID of the asset.
            limit: Maximum number of records to return.

        Returns:
            List of SignalRecord instances ordered by date descending.
        """
        stmt = (
            select(SignalRecord)
            .where(SignalRecord.asset_id == asset_id)
            .order_by(SignalRecord.date.desc(), SignalRecord.category)
            .limit(limit)
        )
        result = await session.scalars(stmt)
        return list(result.all())


signal_repo = SignalRepository()
