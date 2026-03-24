"""Handler for /lessons command (TBOT-05)."""

from __future__ import annotations

import html

import structlog
from telegram import Update
from telegram.ext import ContextTypes

from src.bot.auth import is_authorized
from src.db.database import async_session_factory
from src.db.lesson_repo import lesson_repo
from src.report.formatter import format_lessons_message, split_report

logger = structlog.get_logger(__name__)

VALID_ASSET_TYPES = {"stock", "crypto", "all"}
VALID_ENGINES = {
    "technical", "quantitative", "fundamental", "macro", "sentiment",
    "event", "ml", "onchain", "options", "behavioral", "network",
    "game_theory", "emerging", "valuation", "news",
}


async def lessons_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /lessons command with optional asset_type and engine filter.

    Usage: /lessons [asset_type] [engine]
    asset_type: stock, crypto, all (default: all)
    engine: technical, quantitative, etc (default: all)
    Per D-17 filter syntax.
    """
    if not is_authorized(update):
        return

    logger.info(
        "lessons_command",
        chat_id=update.effective_chat.id,  # type: ignore[union-attr]
        args=context.args,
    )

    # Parse args: /lessons [asset_type] [engine]
    asset_filter: str | None = None
    engine_filter: str | None = None

    for arg in (context.args or []):
        lower = arg.lower()
        if lower in VALID_ASSET_TYPES:
            asset_filter = lower
        elif lower in VALID_ENGINES:
            engine_filter = lower
        else:
            await update.message.reply_text(  # type: ignore[union-attr]
                f"Unknown filter: <code>{html.escape(arg)}</code>\n\n"
                "Usage: /lessons [stock|crypto|all] [engine]\n"
                "Engines: technical, quantitative, fundamental, macro, sentiment",
                parse_mode="HTML",
            )
            return

    try:
        async with async_session_factory() as session:
            data = await lesson_repo.get_lessons_for_display(
                session, asset_type=asset_filter, engine_filter=engine_filter
            )

            msg = format_lessons_message(
                recently_learned=data["recently_learned"],
                top_lessons=data["top_lessons"],
                asset_filter=asset_filter,
                engine_filter=engine_filter,
            )

        # Split if needed
        if len(msg) > 4096:
            messages = split_report(msg, [])
        else:
            messages = [msg]

        for m in messages:
            await update.message.reply_text(m, parse_mode="HTML")  # type: ignore[union-attr]

    except Exception:
        logger.exception("lessons_handler_error")
        await update.message.reply_text(  # type: ignore[union-attr]
            "Failed to load lessons. Try again in a few minutes.",
            parse_mode="HTML",
        )
