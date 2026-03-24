"""Handler for /scorecard command (TBOT-04)."""

from __future__ import annotations

import structlog
from telegram import Update
from telegram.ext import ContextTypes

from src.bot.auth import is_authorized
from src.db.database import async_session_factory
from src.db.evaluation_repo import evaluation_repo
from src.report.formatter import (
    format_scorecard_error,
    format_scorecard_message,
    split_report,
)

logger = structlog.get_logger(__name__)

VALID_PERIODS = {"7d", "30d", "90d", "all"}

# Period to days-back mapping for recent evaluations
_PERIOD_DAYS: dict[str, int] = {
    "7d": 7,
    "30d": 30,
    "90d": 90,
    "all": 3650,  # ~10 years as proxy for "all"
}


async def scorecard_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /scorecard command with optional period and asset filter.

    Usage: /scorecard [period] [asset]
    Period: 7d, 30d, 90d, all (default: 30d)
    Asset: symbol to filter (e.g., BTC, BBCA)
    """
    if not is_authorized(update):
        return

    logger.info(
        "scorecard_command",
        chat_id=update.effective_chat.id,  # type: ignore[union-attr]
        args=context.args,
    )

    # Parse args: /scorecard [period] [asset]
    period = "30d"
    asset_filter: str | None = None

    for arg in (context.args or []):
        lower = arg.lower()
        if lower in VALID_PERIODS:
            period = lower
        elif _looks_like_period(lower):
            # Looks like a period but invalid (e.g., "5d")
            await update.message.reply_text(  # type: ignore[union-attr]
                "\u274c Invalid period. Use: 7d, 30d, 90d, or all.\n\n"
                "Example: /scorecard 30d BTC",
                parse_mode="HTML",
            )
            return
        else:
            asset_filter = arg.upper()

    try:
        async with async_session_factory() as session:
            # If asset filter, resolve to asset_id
            asset_id: int | None = None
            if asset_filter:
                from sqlalchemy import select

                from src.db.models import Asset, Watchlist

                stmt = (
                    select(Asset.id)
                    .join(Watchlist, Watchlist.asset_id == Asset.id)
                    .where(Asset.symbol.ilike(asset_filter))
                )
                result = await session.execute(stmt)
                row = result.scalar_one_or_none()
                if row is None:
                    await update.message.reply_text(  # type: ignore[union-attr]
                        f"\u274c Asset <code>{asset_filter}</code> not found in your watchlist.\n\n"
                        "Use /watchlist to see your tracked assets.",
                        parse_mode="HTML",
                    )
                    return
                asset_id = row

            data = await evaluation_repo.get_scorecard_data(session, period, asset_id)

            total_decisions = data["total_decisions"]
            win_rates = data["win_rates_by_window"]

            # Determine empty states
            if total_decisions == 0 and not win_rates:
                if period != "all" and not asset_filter:
                    # Period-empty: suggest longer period
                    msg = format_scorecard_message(
                        period=period,
                        asset_filter=asset_filter,
                        win_rates_by_window={},
                        total_decisions=0,
                        best_engine=None,
                        worst_engine=None,
                        per_asset_buyhold=[],
                        period_empty=True,
                    )
                else:
                    # Absolute empty
                    msg = format_scorecard_message(
                        period=period,
                        asset_filter=asset_filter,
                        win_rates_by_window={},
                        total_decisions=0,
                        best_engine=None,
                        worst_engine=None,
                        per_asset_buyhold=[],
                    )
                await update.message.reply_text(msg, parse_mode="HTML")  # type: ignore[union-attr]
                return

            # Build buy-and-hold data (from scorecard data if available)
            per_asset_buyhold = data.get("per_asset_buyhold", [])

            # Fetch recent calls if asset-filtered
            recent_calls: list[dict[str, object]] | None = None
            if asset_filter and asset_id is not None:
                days_back = _PERIOD_DAYS.get(period, 30)
                recent_evals = await evaluation_repo.get_recent_evaluations(
                    session, "24h", days_back, asset_id
                )
                if recent_evals:
                    from sqlalchemy import select as sel

                    from src.db.models import Asset as A
                    from src.db.models import DailyDecision as DD

                    recent_calls = []
                    for ev in recent_evals[:5]:
                        dd_stmt = sel(DD).where(DD.id == ev.decision_id)
                        dd_result = await session.execute(dd_stmt)
                        dd = dd_result.scalar_one_or_none()
                        if dd:
                            recent_calls.append({
                                "date": str(dd.date),
                                "verdict": dd.verdict,
                                "change_pct": float(ev.change_pct),
                                "was_correct": ev.was_correct,
                                "window": ev.window,
                            })

            msg = format_scorecard_message(
                period=period,
                asset_filter=asset_filter,
                win_rates_by_window=win_rates,
                total_decisions=total_decisions,
                best_engine=data["best_engine"],
                worst_engine=data["worst_engine"],
                per_asset_buyhold=per_asset_buyhold,
                recent_calls=recent_calls,
            )

        # Split if message is too long
        if len(msg) > 4096:
            messages = split_report(msg, [])
        else:
            messages = [msg]

        for m in messages:
            await update.message.reply_text(m, parse_mode="HTML")  # type: ignore[union-attr]

    except Exception:
        logger.exception("scorecard_handler_error")
        error_msg = format_scorecard_error()
        await update.message.reply_text(error_msg, parse_mode="HTML")  # type: ignore[union-attr]


def _looks_like_period(s: str) -> bool:
    """Check if a string looks like a period pattern (e.g., '5d', '10d')."""
    if len(s) < 2:
        return False
    return s[-1] == "d" and s[:-1].isdigit()
