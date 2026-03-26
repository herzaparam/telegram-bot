"""Handler for /discover command (TBOT-06).

Shows today's top discovery candidates. Reads from discovery_candidates table.
Does NOT import pipeline/scanner modules (two-process boundary).
"""

from __future__ import annotations

from datetime import date

import structlog
from sqlalchemy import select
from telegram import Update
from telegram.ext import ContextTypes

from src.bot.auth import is_authorized
from src.db.database import async_session_factory
from src.db.models import DiscoveryCandidate
from src.report.formatter import format_discovery_card

logger = structlog.get_logger(__name__)

SEARCH_EMOJI = "\U0001f50d"
ERROR_EMOJI = "\u274c"


async def discover_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /discover command -- show today's top 5 discovery candidates."""
    if not is_authorized(update):
        return

    logger.info("discover_command", chat_id=update.effective_chat.id)  # type: ignore[union-attr]

    try:
        async with async_session_factory() as session:
            stmt = (
                select(DiscoveryCandidate)
                .where(DiscoveryCandidate.scan_date == date.today())
                .order_by(DiscoveryCandidate.composite_score.desc())
                .limit(5)
            )
            result = await session.execute(stmt)
            candidates = result.scalars().all()
    except Exception:
        logger.exception("discover_db_error")
        await update.message.reply_text(  # type: ignore[union-attr]
            f"{ERROR_EMOJI} Discovery scan data unavailable. The scanner may not have run yet today.",
            parse_mode="HTML",
        )
        return

    if not candidates:
        await update.message.reply_text(  # type: ignore[union-attr]
            f"{SEARCH_EMOJI} No new opportunities found today.\n\n"
            "The scanner checks all IHSG stocks and top 100 crypto daily. Try again tomorrow.",
            parse_mode="HTML",
        )
        return

    # Build formatted message
    header = f"<b>{SEARCH_EMOJI} Today's Discoveries</b>\n{date.today().isoformat()}"

    cards = []
    for c in candidates:
        # Convert triggers JSONB to list of dicts for formatter
        triggers_raw = c.triggers or {}
        triggers_list = [
            {"type": k, "name": k.replace("_", " ").title(), "score": v}
            for k, v in triggers_raw.items()
        ] if isinstance(triggers_raw, dict) else triggers_raw

        card = format_discovery_card({
            "symbol": c.symbol,
            "name": c.name or c.symbol,
            "asset_type": c.asset_type,
            "composite_score": c.composite_score,
            "triggers": triggers_list,
            "current_price": c.current_price or 0,
            "price_change_pct": c.price_change_pct or 0,
            "volume_ratio": c.volume_ratio or 0,
        })
        cards.append(card)

    msg = header + "\n\n" + "\n\n".join(cards)
    await update.message.reply_text(msg, parse_mode="HTML")  # type: ignore[union-attr]
