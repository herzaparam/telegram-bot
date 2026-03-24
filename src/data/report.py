"""Pipeline report delivery stage.

Formats the daily signal report and sends to Telegram via httpx.
NOT a StageFunc -- runs after all pipeline stages complete (D-15).
Uses httpx for Telegram API, never imports python-telegram-bot (D-16).
"""

from __future__ import annotations

import asyncio
from collections import Counter
from datetime import date

import httpx
import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import settings
from src.db.evaluation_repo import evaluation_repo
from src.db.models import Asset, DailyDecision, Evaluation, Watchlist
from src.report.formatter import (
    EvalDisplayItem,
    format_asset_card,
    format_report_header,
    format_scorecard_section,
    split_report,
)

logger = structlog.get_logger(__name__)

TELEGRAM_API = "https://api.telegram.org/bot{token}/sendMessage"


def _get_chat_ids() -> list[str]:
    """Parse comma-separated chat IDs from settings."""
    return [cid.strip() for cid in settings.telegram_chat_id.split(",") if cid.strip()]


async def send_telegram_message(chat_id: str, text: str, token: str) -> bool:
    """Send a single message to a Telegram chat via httpx.

    Args:
        chat_id: Telegram chat ID.
        text: Message text (HTML).
        token: Bot token.

    Returns:
        True if message was sent successfully.
    """
    url = TELEGRAM_API.format(token=token)
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}

    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post(url, json=payload)

        if response.status_code == 200:
            return True

        if response.status_code == 429:
            # Rate limited -- retry once after waiting
            retry_after = response.json().get("parameters", {}).get("retry_after", 1)
            logger.warning(
                "telegram_rate_limited",
                chat_id=chat_id,
                retry_after=retry_after,
            )
            await asyncio.sleep(retry_after)
            response = await client.post(url, json=payload)
            return response.status_code == 200

        logger.warning(
            "telegram_send_failed",
            chat_id=chat_id,
            status_code=response.status_code,
            response_text=response.text,
        )
        return False


async def _build_scorecard_section(
    session: AsyncSession,
    run_date: date,
) -> str:
    """Build scorecard section text from matured evaluations.

    Queries recent evaluations for each window, computes weekly trend,
    and formats via format_scorecard_section().
    Returns empty string if no evaluations found (D-18).
    """
    from datetime import timedelta

    window_days_back = {"24h": 2, "3d": 4, "7d": 8, "30d": 31}
    results_by_window: dict[str, list[EvalDisplayItem]] = {}

    for window, days in window_days_back.items():
        evals = await evaluation_repo.get_recent_evaluations(
            session, window, days_back=days
        )
        if not evals:
            continue

        # Join with decisions to get verdict and symbol
        items: list[EvalDisplayItem] = []
        for ev in evals:
            decision_stmt = select(DailyDecision, Asset).join(
                Asset, DailyDecision.asset_id == Asset.id
            ).where(DailyDecision.id == ev.decision_id)
            result = await session.execute(decision_stmt)
            row = result.first()
            if row:
                decision, asset = row
                items.append(
                    EvalDisplayItem(
                        symbol=asset.symbol,
                        verdict=decision.verdict,
                        change_pct=float(ev.change_pct),
                        was_correct=ev.was_correct,
                    )
                )
        if items:
            results_by_window[window] = items

    # Compute weekly trend for 24h accuracy
    weekly_trend: str | None = None
    try:
        this_week_evals = await evaluation_repo.get_recent_evaluations(
            session, "24h", days_back=7
        )
        last_week_evals = await evaluation_repo.get_recent_evaluations(
            session, "24h", days_back=14
        )
        # Subtract this week from last week to get only last week
        this_week_ids = {e.id for e in this_week_evals}
        last_week_only = [e for e in last_week_evals if e.id not in this_week_ids]

        if this_week_evals and last_week_only:
            this_correct = sum(1 for e in this_week_evals if e.was_correct)
            this_total = len(this_week_evals)
            this_rate = round((this_correct / this_total) * 100)

            last_correct = sum(1 for e in last_week_only if e.was_correct)
            last_total = len(last_week_only)
            last_rate = round((last_correct / last_total) * 100)

            diff = this_rate - last_rate
            if diff > 2:
                direction = "^"
            elif diff < -2:
                direction = "v"
            else:
                direction = "~"

            weekly_trend = (
                f"Trending: {this_rate}% win rate this week "
                f"({direction} from {last_rate}% last week)"
            )
    except Exception:
        logger.debug("weekly_trend_computation_failed", exc_info=True)

    return format_scorecard_section(results_by_window, weekly_trend)


async def send_daily_report(
    session: AsyncSession,
    run_date: date,
    stage_results: list | None = None,
) -> None:
    """Send the daily signal report to all configured Telegram chats.

    Queries watchlist + decisions + assets for run_date, formats using the
    shared formatter, and sends via httpx.

    Args:
        session: SQLAlchemy async session.
        run_date: The pipeline run date.
        stage_results: Optional list of StageResult from pipeline runner.
    """
    token = settings.telegram_bot_token.get_secret_value()
    if not token:
        logger.warning("no_bot_token")
        return

    chat_ids = _get_chat_ids()
    if not chat_ids:
        logger.warning("no_chat_ids")
        return

    # Query watchlist asset IDs
    wl_result = await session.execute(select(Watchlist.asset_id))
    watchlist_rows = wl_result.scalars().all()
    if not watchlist_rows:
        logger.info("empty_watchlist_no_report")
        return

    watchlist_asset_ids = [row.asset_id if hasattr(row, "asset_id") else row for row in watchlist_rows]

    # Query decisions for run_date joined with assets, filtered to watchlist
    stmt = (
        select(DailyDecision, Asset)
        .join(Asset, DailyDecision.asset_id == Asset.id)
        .where(DailyDecision.date == run_date)
        .where(DailyDecision.asset_id.in_(watchlist_asset_ids))
        .order_by(Asset.symbol)
    )
    result = await session.execute(stmt)
    results = result.all()

    # No decisions -- send "no signals" message
    if not results:
        no_signals_msg = (
            "\u2139\ufe0f No signals available yet for today. "
            "The pipeline runs daily -- signals will appear after the next run."
        )
        for cid in chat_ids:
            await send_telegram_message(cid, no_signals_msg, token)
        return

    # Build sentiment distribution
    distribution = dict(Counter(d.verdict for d, a in results))

    # Collect deduplicated risk warnings
    risk_warnings: list[str] = []
    seen_warnings: set[str] = set()
    for d, a in results:
        if d.risk_warning and d.risk_warning not in seen_warnings:
            risk_warnings.append(d.risk_warning)
            seen_warnings.add(d.risk_warning)

    # Check stage_results for failures (D-18)
    failure_notice = ""
    if stage_results:
        for sr in stage_results:
            if sr.status in ("partial", "failed") and sr.assets_failed > 0:
                failure_notice = (
                    f"\u26a0\ufe0f {sr.assets_failed} assets failed "
                    f"in {sr.stage} stage. Partial report below."
                )
                break

    # Build scorecard section from matured evaluations
    scorecard_text = await _build_scorecard_section(session, run_date)

    # Format header
    header = format_report_header(
        str(run_date), len(results), distribution, risk_warnings
    )

    if failure_notice:
        header = header + "\n\n" + failure_notice

    # Prepend scorecard section if evaluations exist
    if scorecard_text:
        header = scorecard_text + "\n\n---\n\n" + header

    # Format asset cards
    cards = [
        format_asset_card(
            a.symbol,
            a.name or a.symbol,
            d.verdict,
            float(d.score or 0),
            float(d.confidence or 0),
            d.reasoning or "",
        )
        for d, a in results
    ]

    # Split into messages respecting 4096-char limit
    messages = split_report(header, cards)

    # Send to all chat IDs
    for cid in chat_ids:
        for msg in messages:
            await send_telegram_message(cid, msg, token)

    logger.info(
        "report_sent",
        chat_ids=len(chat_ids),
        messages_per_chat=len(messages),
        assets=len(results),
    )


async def send_pipeline_failure_alert(run_date: date) -> None:
    """Send a pipeline failure alert to all configured Telegram chats.

    Args:
        run_date: The pipeline run date that failed.
    """
    token = settings.telegram_bot_token.get_secret_value()
    if not token:
        logger.warning("no_bot_token")
        return

    chat_ids = _get_chat_ids()
    if not chat_ids:
        logger.warning("no_chat_ids")
        return

    message = (
        "\u26a0\ufe0f <b>Pipeline Failed</b>\n\n"
        "Today's signal report could not be generated. "
        "The team has been notified."
    )

    for cid in chat_ids:
        await send_telegram_message(cid, message, token)

    logger.info("pipeline_failure_alert_sent", chat_ids=len(chat_ids), run_date=str(run_date))
