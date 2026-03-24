"""Repository for lesson extraction and management.

Uses SQLAlchemy ORM with PostgreSQL-specific INSERT for new lessons
and direct UPDATE for merges and scoring.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

import sqlalchemy as sa
from sqlalchemy import and_, func, or_, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import Lesson


class LessonRepository:
    """Async repository for Lesson persistence with scoring, tier promotion, and invalidation."""

    async def upsert_lesson(
        self,
        session: AsyncSession,
        date: date,
        asset_type: str | None,
        engine_tags: list[str] | None,
        topic: str | None,
        lesson_text: str,
        source_decision_id: int | None,
        times_observed: int = 1,
    ) -> int:
        """Insert a new lesson. Returns the new lesson ID.

        No conflict handling -- new lessons always get new rows.
        Dedup/merging is handled by merge_lesson.
        """
        stmt = (
            pg_insert(Lesson)
            .values(
                date=date,
                asset_type=asset_type,
                engine_tags=engine_tags,
                topic=topic,
                lesson=lesson_text,
                source_decision_id=source_decision_id,
                times_observed=times_observed,
            )
            .returning(Lesson.id)
        )
        result = await session.execute(stmt)
        row = result.scalar_one()
        return row

    async def merge_lesson(
        self,
        session: AsyncSession,
        lesson_id: int,
        new_text: str,
        additional_observations: int = 1,
    ) -> None:
        """Merge into an existing lesson: update text, increment observations, promote tier."""
        # First get current times_observed to compute new tier
        existing = await session.get(Lesson, lesson_id)
        if existing is None:
            return

        new_observed = existing.times_observed + additional_observations
        new_tier = _compute_tier(new_observed)

        stmt = (
            update(Lesson)
            .where(Lesson.id == lesson_id)
            .values(
                lesson=new_text,
                times_observed=new_observed,
                confidence_tier=new_tier,
                updated_at=func.now(),
            )
        )
        await session.execute(stmt)

    async def get_valid_lessons(
        self,
        session: AsyncSession,
        asset_type: str | None = None,
        engine_filter: str | None = None,
        limit: int = 50,
    ) -> list[Lesson]:
        """Get valid lessons with optional filters.

        Args:
            asset_type: Filter by exact match or "all".
            engine_filter: Check if engine_tags JSONB contains this value.
            limit: Max results.
        """
        filters = [Lesson.still_valid.is_(True)]

        if asset_type is not None:
            filters.append(
                or_(Lesson.asset_type == asset_type, Lesson.asset_type == "all")
            )

        if engine_filter is not None:
            filters.append(Lesson.engine_tags.op("@>")(f'["{engine_filter}"]'))

        stmt = (
            select(Lesson)
            .where(*filters)
            .order_by(Lesson.updated_at.desc())
            .limit(limit)
        )
        result = await session.scalars(stmt)
        return list(result.all())

    async def get_relevant_lessons(
        self,
        session: AsyncSession,
        asset_type: str,
        engine_categories: list[str],
        max_lessons: int = 20,
    ) -> list[Lesson]:
        """Get relevant lessons for injection into decisions.

        Only returns lessons with confidence_tier in ('pattern', 'rule')
        -- not active until 10+ observations.
        """
        stmt = (
            select(Lesson)
            .where(
                Lesson.still_valid.is_(True),
                Lesson.confidence_tier.in_(["pattern", "rule"]),
            )
        )
        result = await session.scalars(stmt)
        all_lessons = list(result.all())

        now = datetime.now(UTC)
        scored = [
            (self._score_lesson(lesson, asset_type, engine_categories, now), lesson)
            for lesson in all_lessons
        ]
        scored.sort(key=lambda x: x[0], reverse=True)
        return [lesson for _, lesson in scored[:max_lessons]]

    def _score_lesson(
        self,
        lesson: Lesson,
        asset_type: str,
        engine_categories: list[str],
        now: datetime,
    ) -> float:
        """Multi-factor scoring per D-13.

        Weights: recency 0.25, accuracy 0.30, asset-type match 0.25, engine relevance 0.20.
        """
        # Recency: linear decay over 90 days
        if lesson.updated_at is not None:
            updated = lesson.updated_at
            if updated.tzinfo is None:
                updated = updated.replace(tzinfo=UTC)
            age_days = (now - updated).days
        else:
            age_days = 90
        recency = max(0.0, 1.0 - (age_days / 90.0))

        # Accuracy rate
        if lesson.times_applied > 0:
            accuracy = lesson.times_correct / lesson.times_applied
        else:
            accuracy = 0.5  # prior

        # Asset-type match
        if lesson.asset_type == asset_type or lesson.asset_type == "all":
            asset_match = 1.0
        else:
            asset_match = 0.3

        # Engine relevance: fraction overlap
        tags = lesson.engine_tags if isinstance(lesson.engine_tags, list) else []
        if tags and engine_categories:
            overlap = len(set(tags) & set(engine_categories))
            engine_rel = overlap / max(len(tags), 1)
        else:
            engine_rel = 0.0

        return (
            0.25 * recency
            + 0.30 * accuracy
            + 0.25 * asset_match
            + 0.20 * engine_rel
        )

    async def increment_times_applied(
        self,
        session: AsyncSession,
        lesson_ids: list[int],
    ) -> None:
        """Increment times_applied for a batch of lessons."""
        if not lesson_ids:
            return
        stmt = (
            update(Lesson)
            .where(Lesson.id.in_(lesson_ids))
            .values(times_applied=Lesson.times_applied + 1)
        )
        await session.execute(stmt)

    async def update_lesson_accuracy(
        self,
        session: AsyncSession,
        lesson_id: int,
        was_correct: bool,
    ) -> None:
        """Update lesson accuracy. Only increments times_correct if correct."""
        if not was_correct:
            return
        stmt = (
            update(Lesson)
            .where(Lesson.id == lesson_id)
            .values(times_correct=Lesson.times_correct + 1)
        )
        await session.execute(stmt)

    async def invalidate_underperforming(
        self,
        session: AsyncSession,
    ) -> None:
        """Invalidate lessons with times_applied >= 5 and accuracy < 40%.

        Per D-09: auto-invalidate underperforming lessons.
        """
        stmt = (
            update(Lesson)
            .where(
                Lesson.times_applied >= 5,
                (Lesson.times_correct.cast(sa.Float) / Lesson.times_applied) < 0.4,
                Lesson.still_valid.is_(True),
            )
            .values(still_valid=False)
        )
        await session.execute(stmt)

    async def get_lessons_for_display(
        self,
        session: AsyncSession,
        asset_type: str | None = None,
        engine_filter: str | None = None,
    ) -> dict:
        """Return lessons for display per D-16.

        Returns dict with recently_learned and top_lessons lists.
        """
        now = datetime.now(UTC)
        week_ago = now - timedelta(days=7)

        # Recently learned
        recent_filters = [
            Lesson.still_valid.is_(True),
            Lesson.created_at >= week_ago,
        ]
        if asset_type:
            recent_filters.append(
                or_(Lesson.asset_type == asset_type, Lesson.asset_type == "all")
            )

        recent_stmt = (
            select(Lesson)
            .where(*recent_filters)
            .order_by(Lesson.created_at.desc())
            .limit(10)
        )
        recent_result = await session.scalars(recent_stmt)
        recently_learned = [_lesson_to_dict(l) for l in recent_result.all()]

        # Top lessons by accuracy
        top_filters = [
            Lesson.still_valid.is_(True),
            Lesson.times_applied >= 3,
        ]
        if asset_type:
            top_filters.append(
                or_(Lesson.asset_type == asset_type, Lesson.asset_type == "all")
            )

        top_stmt = (
            select(Lesson)
            .where(*top_filters)
            .order_by(
                (Lesson.times_correct.cast(sa.Float) / Lesson.times_applied).desc()
            )
            .limit(10)
        )
        top_result = await session.scalars(top_stmt)
        top_lessons = [_lesson_to_dict(l) for l in top_result.all()]

        return {
            "recently_learned": recently_learned,
            "top_lessons": top_lessons,
        }


def _compute_tier(times_observed: int) -> str:
    """Compute confidence tier based on observation count."""
    if times_observed >= 30:
        return "rule"
    elif times_observed >= 10:
        return "pattern"
    return "hypothesis"


def _lesson_to_dict(lesson: Lesson) -> dict:
    """Convert Lesson ORM instance to display dict."""
    accuracy = (
        round(lesson.times_correct / lesson.times_applied, 2)
        if lesson.times_applied > 0
        else None
    )
    return {
        "id": lesson.id,
        "lesson": lesson.lesson,
        "tier": lesson.confidence_tier,
        "times_observed": lesson.times_observed,
        "times_applied": lesson.times_applied,
        "accuracy": accuracy,
        "asset_type": lesson.asset_type,
        "engine_tags": lesson.engine_tags,
        "topic": lesson.topic,
        "date": lesson.date,
    }


# Module-level singleton
lesson_repo = LessonRepository()
