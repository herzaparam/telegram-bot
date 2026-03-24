"""Shared fixtures for bot handler tests."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from telegram import Chat, Message, Update, User


@pytest.fixture
def mock_update() -> MagicMock:
    """Create a mock Telegram Update with authorized chat."""
    update = MagicMock(spec=Update)
    chat = MagicMock(spec=Chat)
    chat.id = 12345
    update.effective_chat = chat

    message = MagicMock(spec=Message)
    message.reply_text = AsyncMock()
    update.message = message

    user = MagicMock(spec=User)
    user.id = 12345
    update.effective_user = user

    return update


@pytest.fixture
def mock_update_unauthorized() -> MagicMock:
    """Create a mock Telegram Update with unauthorized chat."""
    update = MagicMock(spec=Update)
    chat = MagicMock(spec=Chat)
    chat.id = 99999
    update.effective_chat = chat

    message = MagicMock(spec=Message)
    message.reply_text = AsyncMock()
    update.message = message

    return update


@pytest.fixture
def mock_context() -> MagicMock:
    """Create a mock PTB context."""
    from telegram.ext import ContextTypes

    context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
    context.args = []
    return context
