"""Handler for /report command (TBOT-02, TBOT-03, REPT-02, REPT-04)."""

from __future__ import annotations

from datetime import date

import structlog
from sqlalchemy import select
from sqlalchemy.orm import aliased
from telegram import Update
from telegram.ext import ContextTypes

from src.bot.auth import is_authorized
from src.db.database import async_session_factory
from src.db.models import Asset, DailyDecision, Watchlist
from src.report.formatter import (
    format_asset_card,
    format_asset_detail,
    format_report_header,
    split_report,
)

logger = structlog.get_logger(__name__)


async def report_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Deliver full or single-asset report (TBOT-02, TBOT-03)."""
    if not is_authorized(update):
        return

    today = date.today()
    logger.info("report_command", chat_id=update.effective_chat.id, args=context.args)  # type: ignore[union-attr]

    if context.args:
        # Single-asset mode
        symbol = context.args[0].upper()
        await _single_asset_report(update, symbol, today)
    else:
        # Full report mode
        await _full_report(update, today)


async def _single_asset_report(update: Update, symbol: str, today: date) -> None:
    """Query and send single-asset detail report."""
    async with async_session_factory() as session:
        asset_alias = aliased(Asset)
        result = await session.execute(
            select(DailyDecision, asset_alias)
            .join(asset_alias, DailyDecision.asset_id == asset_alias.id)
            .where(
                DailyDecision.date == today,
                asset_alias.symbol.ilike(symbol),
            )
        )
        row = result.first()

    if not row:
        await update.message.reply_text(  # type: ignore[union-attr]
            f"\u2139\ufe0f No signals available yet for <b>{symbol}</b> today. "
            "The pipeline runs daily.",
            parse_mode="HTML",
        )
        return

    decision, asset = row
    msg = format_asset_detail(
        symbol=asset.symbol,
        name=asset.name or asset.symbol,
        verdict=decision.verdict,
        score=float(decision.score or 0),
        confidence=float(decision.confidence or 0),
        reasoning=decision.reasoning or "",
        key_factors=decision.key_factors,
        risk_warning=decision.risk_warning,
    )
    await update.message.reply_text(msg, parse_mode="HTML")  # type: ignore[union-attr]


async def _full_report(update: Update, today: date) -> None:
    """Query watchlist and send full daily report."""
    async with async_session_factory() as session:
        # Get watchlist asset IDs
        wl_result = await session.execute(
            select(Watchlist.asset_id)
        )
        watchlist_asset_ids = [row[0] for row in wl_result.all()]

        if not watchlist_asset_ids:
            await update.message.reply_text(  # type: ignore[union-attr]
                "\u2139\ufe0f No assets in your watchlist. Add assets first with /add BBCA",
                parse_mode="HTML",
            )
            return

        # Get decisions for today's date for watchlist assets
        asset_alias = aliased(Asset)
        result = await session.execute(
            select(DailyDecision, asset_alias)
            .join(asset_alias, DailyDecision.asset_id == asset_alias.id)
            .where(
                DailyDecision.date == today,
                DailyDecision.asset_id.in_(watchlist_asset_ids),
            )
        )
        rows = result.all()

    if not rows:
        await update.message.reply_text(  # type: ignore[union-attr]
            "\u2139\ufe0f No signals available yet for today. The pipeline runs daily.",
            parse_mode="HTML",
        )
        return

    # Build distribution and risk warnings
    distribution: dict[str, int] = {}
    risk_warnings: list[str] = []
    asset_cards: list[str] = []

    for decision, asset in rows:
        verdict = decision.verdict
        distribution[verdict] = distribution.get(verdict, 0) + 1
        if decision.risk_warning:
            risk_warnings.append(f"{asset.symbol}: {decision.risk_warning}")

        card = format_asset_card(
            symbol=asset.symbol,
            name=asset.name or asset.symbol,
            verdict=verdict,
            score=float(decision.score or 0),
            confidence=float(decision.confidence or 0),
            reasoning=decision.reasoning or "",
        )
        asset_cards.append(card)

    header = format_report_header(
        run_date=today.isoformat(),
        total=len(rows),
        distribution=distribution,
        risk_warnings=risk_warnings,
    )

    messages = split_report(header, asset_cards)
    for msg in messages:
        await update.message.reply_text(msg, parse_mode="HTML")  # type: ignore[union-attr]
