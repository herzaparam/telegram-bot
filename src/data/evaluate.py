"""Evaluate prior decisions against actual prices (EVAL-01).

Runs as the FIRST pipeline stage each morning (D-11), before ingest.
Compares yesterday's decisions at multiple time windows against actual prices.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Any

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.decision_repo import decision_repo
from src.db.evaluation_repo import evaluation_repo
from src.db.models import Asset, DailyDecision, PriceHistory, PriceHistoryHourly
from src.db.signal_repo import signal_repo

logger = structlog.get_logger(__name__)

# HOLD band thresholds per window and asset type (D-01, D-02, D-04)
HOLD_BANDS: dict[str, dict[str, float]] = {
    "24h": {"stock": 0.02, "crypto": 0.05},
    "3d": {"stock": 0.03, "crypto": 0.08},
    "7d": {"stock": 0.05, "crypto": 0.12},
    "30d": {"stock": 0.08, "crypto": 0.20},
}

# Evaluation windows: (name, timedelta offset from today to find the decision date)
EVAL_WINDOWS = [
    ("24h", timedelta(days=1)),
    ("3d", timedelta(days=3)),
    ("7d", timedelta(days=7)),
    ("30d", timedelta(days=30)),
]


def _classify_result(
    verdict: str,
    decision_price: float,
    eval_price: float,
    asset_type: str,
    window: str,
) -> tuple[float, bool]:
    """Classify whether a decision was correct based on price movement.

    Args:
        verdict: The decision verdict (BUY, SELL, HOLD, STRONG BUY, STRONG SELL).
        decision_price: Price at decision time.
        eval_price: Price at evaluation time.
        asset_type: "stock" or "crypto".
        window: Evaluation window ("24h", "3d", "7d", "30d").

    Returns:
        Tuple of (change_pct as percentage, was_correct boolean).
    """
    change_pct = ((eval_price - decision_price) / decision_price) * 100

    if verdict in ("BUY", "STRONG BUY"):
        was_correct = change_pct > 0
    elif verdict in ("SELL", "STRONG SELL"):
        was_correct = change_pct < 0
    elif verdict == "HOLD":
        band = HOLD_BANDS.get(window, {}).get(asset_type, 0.02)
        was_correct = abs(change_pct) <= (band * 100)
    else:
        # Unknown verdict -- treat as incorrect
        was_correct = False

    return change_pct, was_correct


async def _get_next_trading_day(
    session: AsyncSession,
    after_date: date,
) -> date:
    """Find the next IDX trading day after a given date.

    Skips weekends (Sat/Sun) and IDX holidays.

    Args:
        session: Async SQLAlchemy session.
        after_date: Date to search from (exclusive).

    Returns:
        The next valid trading day.
    """
    candidate = after_date + timedelta(days=1)
    for _ in range(10):
        # Skip weekends
        if candidate.weekday() >= 5:
            candidate += timedelta(days=1)
            continue
        # Skip IDX holidays
        if await evaluation_repo.is_idx_holiday(session, candidate):
            candidate += timedelta(days=1)
            continue
        return candidate
    # Fallback: return candidate even if we exhausted iterations
    return candidate


async def _get_evaluation_price(
    session: AsyncSession,
    asset: Asset,
    decision: DailyDecision,
    window_name: str,
    window_delta: timedelta,
) -> tuple[float, datetime] | None:
    """Get the evaluation price for a decision at a specific window.

    For stocks:
        - Uses daily close from the next trading day (24h) or N calendar days after.
    For crypto:
        - 24h/3d: Uses hourly candle closest to decision_price_at + window_delta.
        - 7d/30d: Falls back to daily close (hourly retention is only 7 days).

    Returns:
        Tuple of (price, timestamp) or None if price not found.
    """
    if asset.asset_type == "stock":
        # For all stock windows: find the appropriate trading day close
        if window_name == "24h":
            target_date = await _get_next_trading_day(session, decision.date)
        else:
            # For 3d/7d/30d: find the trading day closest to N calendar days after
            target_date = decision.date + window_delta
            # Adjust to next trading day if it falls on weekend/holiday
            while target_date.weekday() >= 5:
                target_date += timedelta(days=1)
            if await evaluation_repo.is_idx_holiday(session, target_date):
                target_date = await _get_next_trading_day(session, target_date - timedelta(days=1))

        # Query daily close from price_history
        stmt = select(PriceHistory).where(
            PriceHistory.asset_id == asset.id,
            PriceHistory.time >= datetime(target_date.year, target_date.month, target_date.day, tzinfo=timezone.utc),
            PriceHistory.time < datetime(target_date.year, target_date.month, target_date.day, tzinfo=timezone.utc) + timedelta(days=1),
        ).order_by(PriceHistory.time.desc()).limit(1)
        result = await session.scalars(stmt)
        row = result.one_or_none()

        if row is None:
            return None
        return float(row.close), row.time

    elif asset.asset_type == "crypto":
        if window_name in ("24h", "3d"):
            # Use hourly candle closest to target time
            if decision.decision_price_at is None:
                return None
            target_time = decision.decision_price_at + window_delta
            margin = timedelta(minutes=30)

            stmt = select(PriceHistoryHourly).where(
                PriceHistoryHourly.asset_id == asset.id,
                PriceHistoryHourly.time >= target_time - margin,
                PriceHistoryHourly.time <= target_time + margin,
            ).order_by(
                # Order by absolute distance from target (closest first)
                PriceHistoryHourly.time
            ).limit(1)
            result = await session.scalars(stmt)
            row = result.one_or_none()

            if row is not None:
                return float(row.close), row.time

            # Fallback to daily close if hourly not available
            target_date = (decision.date + window_delta)
            stmt = select(PriceHistory).where(
                PriceHistory.asset_id == asset.id,
                PriceHistory.time >= datetime(target_date.year, target_date.month, target_date.day, tzinfo=timezone.utc),
                PriceHistory.time < datetime(target_date.year, target_date.month, target_date.day, tzinfo=timezone.utc) + timedelta(days=1),
            ).order_by(PriceHistory.time.desc()).limit(1)
            result = await session.scalars(stmt)
            row = result.one_or_none()

            if row is None:
                return None
            return float(row.close), row.time

        else:
            # 7d/30d: use daily close (hourly retention is only 7 days)
            target_date = decision.date + window_delta
            stmt = select(PriceHistory).where(
                PriceHistory.asset_id == asset.id,
                PriceHistory.time >= datetime(target_date.year, target_date.month, target_date.day, tzinfo=timezone.utc),
                PriceHistory.time < datetime(target_date.year, target_date.month, target_date.day, tzinfo=timezone.utc) + timedelta(days=1),
            ).order_by(PriceHistory.time.desc()).limit(1)
            result = await session.scalars(stmt)
            row = result.one_or_none()

            if row is None:
                return None
            return float(row.close), row.time

    return None


async def _compute_engine_results(
    session: AsyncSession,
    asset_id: int,
    decision_date: date,
    change_pct: float,
) -> dict[str, dict[str, Any]]:
    """Compute per-engine correctness from signals.

    For each signal engine:
    - Engine is correct if its score direction matches actual price direction
    - Positive score + positive change = correct
    - Negative score + negative change = correct
    - Zero score = correct (neutral is always right about nothing)

    Returns:
        Dict mapping engine category to {"score": float, "correct": bool}.
    """
    signals = await signal_repo.get_signals_for_asset(session, asset_id, decision_date)

    result: dict[str, dict[str, Any]] = {}
    for sig in signals:
        if sig.score > 0 and change_pct > 0:
            engine_correct = True
        elif sig.score < 0 and change_pct < 0:
            engine_correct = True
        elif sig.score == 0:
            engine_correct = True
        else:
            engine_correct = False

        result[sig.category] = {
            "score": sig.score,
            "correct": engine_correct,
        }

    return result


async def evaluate_stage(session: AsyncSession, asset: Asset) -> None:
    """Evaluate prior decisions against actual prices.

    This is the FIRST pipeline stage (D-11), running before ingest.
    For each evaluation window, checks if a mature decision exists and evaluates it.

    Per D-09: evaluate what's ready, skip pending.
    Per D-10: only read decision_price, never write it.
    """
    log = logger.bind(asset=asset.symbol, asset_id=asset.id)

    try:
        today = date.today()
        evaluated_any = False

        for window_name, window_delta in EVAL_WINDOWS:
            # The decision date we're evaluating for this window
            target_date = today - window_delta

            # Get the decision for that date
            decision = await decision_repo.get_decision(session, asset.id, target_date)
            if decision is None:
                continue

            # Skip if decision_price is null (Pitfall 3)
            if decision.decision_price is None:
                log.debug(
                    "skipping_null_decision_price",
                    window=window_name,
                    target_date=str(target_date),
                )
                continue

            # Check if already evaluated (idempotent)
            existing = await evaluation_repo.get_evaluation(
                session, decision.id, window_name
            )
            if existing is not None:
                continue

            # Get evaluation price
            price_result = await _get_evaluation_price(
                session, asset, decision, window_name, window_delta
            )
            if price_result is None:
                log.warning(
                    "eval_price_not_found",
                    window=window_name,
                    target_date=str(target_date),
                )
                continue

            eval_price, eval_price_at = price_result

            # Classify result
            change_pct, was_correct = _classify_result(
                decision.verdict,
                float(decision.decision_price),
                eval_price,
                asset.asset_type,
                window_name,
            )

            # Compute engine results
            engine_results = await _compute_engine_results(
                session, asset.id, decision.date, change_pct
            )

            # Upsert evaluation
            await evaluation_repo.upsert_evaluation(
                session=session,
                decision_id=decision.id,
                window=window_name,
                eval_price=eval_price,
                eval_price_at=eval_price_at,
                change_pct=change_pct,
                was_correct=was_correct,
                engine_results=engine_results,
            )

            # For 24h window: also update DailyDecision evaluation fields
            if window_name == "24h":
                decision.evaluation_price = eval_price
                decision.evaluation_price_at = eval_price_at

            evaluated_any = True
            log.info(
                "evaluation_complete",
                window=window_name,
                change_pct=f"{change_pct:.2f}%",
                was_correct=was_correct,
            )

        # Recompute accuracy stats after all windows
        if evaluated_any:
            await evaluation_repo.recompute_accuracy_stats(session, asset.id)

    except Exception:
        log.exception("evaluate_stage_error")
        # Do not raise -- per pipeline pattern, error isolation
