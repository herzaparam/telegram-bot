"""Handler for /settings command (TBOT-07, D-17)."""

from __future__ import annotations

import re

import structlog
from sqlalchemy import select
from telegram import Update
from telegram.ext import ContextTypes

from src.bot.auth import is_authorized
from src.db.database import async_session_factory
from src.db.models import BotSettings

logger = structlog.get_logger(__name__)

TIME_PATTERN = re.compile(r"^([01]\d|2[0-3]):([0-5]\d)$")
MIN_HOUR = 6
MAX_HOUR = 9
DEFAULT_DELIVERY_TIME = "06:30"


async def settings_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show or update bot settings (TBOT-07, D-17)."""
    if not is_authorized(update):
        return

    logger.info("settings_command", chat_id=update.effective_chat.id, args=context.args)  # type: ignore[union-attr]

    if context.args and len(context.args) >= 2 and context.args[0].lower() == "time":
        await _update_delivery_time(update, context.args[1])
    else:
        await _show_settings(update)


async def _show_settings(update: Update) -> None:
    """Display current settings."""
    async with async_session_factory() as session:
        result = await session.execute(
            select(BotSettings).where(BotSettings.key == "delivery_time")
        )
        setting = result.scalar_one_or_none()

    delivery_time = setting.value if setting else DEFAULT_DELIVERY_TIME
    await update.message.reply_text(  # type: ignore[union-attr]
        f"\U0001f550 <b>Settings</b>\n\nDelivery time: {delivery_time} WIB",
        parse_mode="HTML",
    )


async def _update_delivery_time(update: Update, time_str: str) -> None:
    """Validate and update delivery time."""
    match = TIME_PATTERN.match(time_str)
    if not match:
        await update.message.reply_text(  # type: ignore[union-attr]
            "\u274c Invalid time. Delivery time must be between 06:00 and 09:00 WIB.\n"
            "\nUsage: /settings time 07:00",
            parse_mode="HTML",
        )
        return

    hour = int(match.group(1))
    if hour < MIN_HOUR or hour > MAX_HOUR:
        await update.message.reply_text(  # type: ignore[union-attr]
            "\u274c Invalid time. Delivery time must be between 06:00 and 09:00 WIB.\n"
            "\nUsage: /settings time 07:00",
            parse_mode="HTML",
        )
        return

    async with async_session_factory() as session:
        result = await session.execute(
            select(BotSettings).where(BotSettings.key == "delivery_time")
        )
        setting = result.scalar_one_or_none()

        if setting:
            setting.value = time_str
        else:
            session.add(BotSettings(key="delivery_time", value=time_str))

        await session.commit()

    await update.message.reply_text(  # type: ignore[union-attr]
        f"\u2705 Delivery time updated to <b>{time_str} WIB</b>.",
        parse_mode="HTML",
    )
