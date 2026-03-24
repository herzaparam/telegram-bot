"""Telegram user authorization via chat ID whitelist (D-03)."""

from telegram import Update

from src.config import settings


def is_authorized(update: Update) -> bool:
    """Check if the message sender is in the configured whitelist.

    Unauthorized messages are silently ignored (D-03).
    """
    if not update.effective_chat:
        return False
    chat_id = str(update.effective_chat.id)
    allowed = {cid.strip() for cid in settings.telegram_chat_id.split(",") if cid.strip()}
    return chat_id in allowed
