"""Repository for evaluation tracking and accuracy statistics.

Uses SQLAlchemy ORM with PostgreSQL-specific UPSERT for idempotent writes.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

from sqlalchemy import and_, func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import AccuracyStats, DailyDecision, Evaluation, IDXHoliday

# Periods for accuracy stats computation
STATS_PERIODS: dict[str, timedelta | None] = {
    "7d": timedelta(days=7),
    "30d": timedelta(days=30),
    "90d": timedelta(days=90),
    "all": None,
}

EVAL_WINDOWS = ["24h", "3d", "7d", "30d"]


class EvaluationRepository:
    """Async repository for Evaluation persistence with UPSERT semantics."""

    async def upsert_evaluation(
        self,
        session: AsyncSession,
        decision_id: int,
        window: str,
        eval_price: float,
        eval_price_at: datetime,
        change_pct: float,
        was_correct: bool,
        engine_results: dict[str, object] | None,
    ) -> None:
        """Upsert an evaluation record.

        Uses INSERT ... ON CONFLICT (decision_id, window) DO UPDATE
        to ensure idempotent writes.
        """
        stmt = pg_insert(Evaluation).values(
            decision_id=decision_id,
            window=window,
            eval_price=eval_price,
            eval_price_at=eval_price_at,
            change_pct=change_pct,
            was_correct=was_correct,
            engine_results=engine_results,
        )
        stmt = stmt.on_conflict_do_update(
            constraint="uq_evaluations_decision_window",
            set_={
                "eval_price": stmt.excluded.eval_price,
                "eval_price_at": stmt.excluded.eval_price_at,
                "change_pct": stmt.excluded.change_pct,
                "was_correct": stmt.excluded.was_correct,
                "engine_results": stmt.excluded.engine_results,
            },
        )
        await session.execute(stmt)

    async def get_evaluation(
        self,
        session: AsyncSession,
        decision_id: int,
        window: str,
    ) -> Evaluation | None:
        """Check if a decision has already been evaluated for a given window."""
        stmt = select(Evaluation).where(
            Evaluation.decision_id == decision_id,
            Evaluation.window == window,
        )
        result = await session.scalars(stmt)
        return result.one_or_none()

    async def recompute_accuracy_stats(
        self,
        session: AsyncSession,
        asset_id: int,
    ) -> None:
        """Recompute all accuracy stats for an asset across all windows and periods.

        For each (window, period) combination:
        - Count total evaluations and correct evaluations
        - Compute win_rate = correct / total
        - Also compute per-engine stats by unpacking engine_results JSONB
        - UPSERT into accuracy_stats
        """
        now = datetime.now(UTC)

        for window in EVAL_WINDOWS:
            for period_name, period_delta in STATS_PERIODS.items():
                # Build base filter for this asset's evaluations in this window
                filters = [
                    Evaluation.window == window,
                    DailyDecision.asset_id == asset_id,
                ]
                if period_delta is not None:
                    cutoff = (now - period_delta).date()
                    filters.append(DailyDecision.date >= cutoff)

                # Overall stats (engine_name = NULL) -- two separate counts
                total_stmt = (
                    select(func.count(Evaluation.id))
                    .select_from(Evaluation)
                    .join(DailyDecision, DailyDecision.id == Evaluation.decision_id)
                    .where(*filters)
                )
                total_result = await session.execute(total_stmt)
                total = total_result.scalar() or 0

                correct_stmt = (
                    select(func.count(Evaluation.id))
                    .select_from(Evaluation)
                    .join(DailyDecision, DailyDecision.id == Evaluation.decision_id)
                    .where(*filters, Evaluation.was_correct.is_(True))
                )
                correct_result = await session.execute(correct_stmt)
                correct = correct_result.scalar() or 0

                win_rate = round((correct / total) * 100, 2) if total > 0 else None

                # Upsert overall stats
                upsert_stmt = pg_insert(AccuracyStats).values(
                    asset_id=asset_id,
                    engine_name=None,
                    window=window,
                    period=period_name,
                    total=total,
                    correct=correct,
                    win_rate=win_rate,
                    computed_at=now,
                )
                upsert_stmt = upsert_stmt.on_conflict_do_update(
                    constraint="uq_accuracy_stats_lookup",
                    set_={
                        "total": upsert_stmt.excluded.total,
                        "correct": upsert_stmt.excluded.correct,
                        "win_rate": upsert_stmt.excluded.win_rate,
                        "computed_at": upsert_stmt.excluded.computed_at,
                    },
                )
                await session.execute(upsert_stmt)

                # Per-engine stats from engine_results JSONB
                # Get evaluations with engine_results for this window/period
                eval_stmt = (
                    select(Evaluation.engine_results)
                    .select_from(Evaluation)
                    .join(DailyDecision, DailyDecision.id == Evaluation.decision_id)
                    .where(*filters, Evaluation.engine_results.isnot(None))
                )
                eval_result = await session.execute(eval_stmt)
                eval_rows = eval_result.scalars().all()

                # Aggregate per-engine
                engine_totals: dict[str, int] = {}
                engine_correct: dict[str, int] = {}
                for engine_data in eval_rows:
                    if not isinstance(engine_data, dict):
                        continue
                    for eng_name, eng_info in engine_data.items():
                        engine_totals[eng_name] = engine_totals.get(eng_name, 0) + 1
                        if isinstance(eng_info, dict) and eng_info.get("correct"):
                            engine_correct[eng_name] = engine_correct.get(eng_name, 0) + 1

                for eng_name in engine_totals:
                    e_total = engine_totals[eng_name]
                    e_correct = engine_correct.get(eng_name, 0)
                    e_win_rate = round((e_correct / e_total) * 100, 2) if e_total > 0 else None

                    eng_upsert = pg_insert(AccuracyStats).values(
                        asset_id=asset_id,
                        engine_name=eng_name,
                        window=window,
                        period=period_name,
                        total=e_total,
                        correct=e_correct,
                        win_rate=e_win_rate,
                        computed_at=now,
                    )
                    eng_upsert = eng_upsert.on_conflict_do_update(
                        constraint="uq_accuracy_stats_lookup",
                        set_={
                            "total": eng_upsert.excluded.total,
                            "correct": eng_upsert.excluded.correct,
                            "win_rate": eng_upsert.excluded.win_rate,
                            "computed_at": eng_upsert.excluded.computed_at,
                        },
                    )
                    await session.execute(eng_upsert)

    async def get_scorecard_data(
        self,
        session: AsyncSession,
        period: str,
        asset_filter: int | None = None,
    ) -> dict:
        """Return scorecard data for a given period.

        Returns dict with keys:
        - win_rates_by_window: dict[str, tuple[int, int]] (correct, total)
        - total_decisions: int
        - best_engine: tuple[str, float] | None
        - worst_engine: tuple[str, float] | None
        """
        filters = [
            AccuracyStats.period == period,
            AccuracyStats.engine_name.is_(None),
        ]
        if asset_filter is not None:
            filters.append(AccuracyStats.asset_id == asset_filter)

        stmt = select(AccuracyStats).where(*filters)
        result = await session.execute(stmt)
        stats = result.scalars().all()

        win_rates_by_window: dict[str, tuple[int, int]] = {}
        total_decisions = 0
        for s in stats:
            key = s.window
            if key in win_rates_by_window:
                prev_c, prev_t = win_rates_by_window[key]
                win_rates_by_window[key] = (prev_c + s.correct, prev_t + s.total)
            else:
                win_rates_by_window[key] = (s.correct, s.total)
            if key == "24h":
                total_decisions += s.total

        # Get best/worst engine
        try:
            best, worst = await self.get_best_worst_engine(
                session, period, asset_id=asset_filter
            )
        except (ValueError, TypeError):
            best = None
            worst = None

        return {
            "win_rates_by_window": win_rates_by_window,
            "total_decisions": total_decisions,
            "best_engine": best,
            "worst_engine": worst,
        }

    async def get_best_worst_engine(
        self,
        session: AsyncSession,
        period: str,
        asset_id: int | None = None,
    ) -> tuple[tuple[str, float], tuple[str, float]]:
        """Query accuracy_stats for best and worst engine by 24h win_rate.

        Returns ((best_name, best_rate), (worst_name, worst_rate)).
        Raises ValueError if no engine stats exist.
        """
        filters = [
            AccuracyStats.window == "24h",
            AccuracyStats.period == period,
            AccuracyStats.engine_name.isnot(None),
            AccuracyStats.total > 0,
        ]
        if asset_id is not None:
            filters.append(AccuracyStats.asset_id == asset_id)

        stmt = (
            select(AccuracyStats)
            .where(*filters)
            .order_by(AccuracyStats.win_rate.desc())
        )
        result = await session.execute(stmt)
        rows = result.all()

        if len(rows) < 1:
            raise ValueError("No engine stats available")

        best_row = rows[0][0] if isinstance(rows[0], tuple) else rows[0]
        worst_row = rows[-1][0] if isinstance(rows[-1], tuple) else rows[-1]

        return (
            (best_row.engine_name, float(best_row.win_rate)),
            (worst_row.engine_name, float(worst_row.win_rate)),
        )

    async def get_recent_evaluations(
        self,
        session: AsyncSession,
        window: str,
        days_back: int,
        asset_id: int | None = None,
    ) -> list[Evaluation]:
        """Get recent evaluations for a window, ordered by created_at desc."""
        cutoff = datetime.now(UTC) - timedelta(days=days_back)
        filters = [
            Evaluation.window == window,
            Evaluation.created_at >= cutoff,
        ]
        if asset_id is not None:
            filters.append(
                Evaluation.decision_id.in_(
                    select(DailyDecision.id).where(DailyDecision.asset_id == asset_id)
                )
            )

        stmt = (
            select(Evaluation)
            .where(*filters)
            .order_by(Evaluation.created_at.desc())
        )
        result = await session.scalars(stmt)
        return list(result.all())

    async def is_idx_holiday(
        self,
        session: AsyncSession,
        check_date: date,
    ) -> bool:
        """Check if a date is an IDX holiday."""
        stmt = select(IDXHoliday).where(IDXHoliday.holiday_date == check_date)
        result = await session.scalars(stmt)
        return result.one_or_none() is not None


evaluation_repo = EvaluationRepository()
