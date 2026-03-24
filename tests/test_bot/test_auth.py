"""Tests for bot authorization whitelist (D-03)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from telegram import Chat, Update

from src.bot.auth import is_authorized


@pytest.fixture
def _make_update():
    """Factory for creating Update mocks with specific chat IDs."""

    def _factory(chat_id: int | None = None) -> MagicMock:
        update = MagicMock(spec=Update)
        if chat_id is not None:
            chat = MagicMock(spec=Chat)
            chat.id = chat_id
            update.effective_chat = chat
        else:
            update.effective_chat = None
        return update

    return _factory


class TestIsAuthorized:
    """Test whitelist authorization check."""

    @patch("src.bot.auth.settings")
    def test_authorized_matching_chat_id(self, mock_settings: MagicMock, _make_update) -> None:
        """Chat ID in whitelist returns True."""
        mock_settings.telegram_chat_id = "12345"
        update = _make_update(12345)
        assert is_authorized(update) is True

    @patch("src.bot.auth.settings")
    def test_unauthorized_non_matching_chat_id(self, mock_settings: MagicMock, _make_update) -> None:
        """Chat ID not in whitelist returns False."""
        mock_settings.telegram_chat_id = "12345"
        update = _make_update(99999)
        assert is_authorized(update) is False

    @patch("src.bot.auth.settings")
    def test_unauthorized_none_effective_chat(self, mock_settings: MagicMock, _make_update) -> None:
        """effective_chat=None returns False."""
        mock_settings.telegram_chat_id = "12345"
        update = _make_update(None)
        assert is_authorized(update) is False

    @patch("src.bot.auth.settings")
    def test_authorized_comma_separated_ids(self, mock_settings: MagicMock, _make_update) -> None:
        """Comma-separated whitelist with matching ID returns True."""
        mock_settings.telegram_chat_id = "12345, 67890"
        update = _make_update(67890)
        assert is_authorized(update) is True

    @patch("src.bot.auth.settings")
    def test_unauthorized_empty_whitelist(self, mock_settings: MagicMock, _make_update) -> None:
        """Empty telegram_chat_id returns False."""
        mock_settings.telegram_chat_id = ""
        update = _make_update(12345)
        assert is_authorized(update) is False

    @patch("src.bot.auth.settings")
    def test_authorized_first_in_comma_list(self, mock_settings: MagicMock, _make_update) -> None:
        """First ID in comma-separated list is authorized."""
        mock_settings.telegram_chat_id = "11111,22222,33333"
        update = _make_update(11111)
        assert is_authorized(update) is True
