"""Handler for /start command (TBOT-01, D-13)."""

import structlog
from telegram import Update
from telegram.ext import ContextTypes

from src.bot.auth import is_authorized

logger = structlog.get_logger(__name__)

WELCOME_MESSAGE = (
    "\u2705 <b>Welcome to Trade Signal Agent</b>\n"
    "\n"
    "I deliver daily trading signals for IDX stocks and crypto assets.\n"
    "\n"
    "<b>Get started:</b>\n"
    "1. Add assets: /add BBCA or /add BTC\n"
    "2. View watchlist: /watchlist\n"
    "3. Get today's report: /report\n"
    "4. Get single asset: /report BTC\n"
    "5. Change delivery time: /settings\n"
    "\n"
    "Your watchlist is empty. Add your first asset to start receiving daily reports."
)


async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send welcome message with available commands."""
    if not is_authorized(update):
        return
    logger.info("start_command", chat_id=update.effective_chat.id)  # type: ignore[union-attr]
    await update.message.reply_text(WELCOME_MESSAGE, parse_mode="HTML")  # type: ignore[union-attr]
