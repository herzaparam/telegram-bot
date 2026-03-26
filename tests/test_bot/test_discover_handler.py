"""Tests for /discover command handler (TBOT-06)."""

from __future__ import annotations

from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.bot.handlers.discover import discover_handler


class TestDiscoverHandler:
    """Tests for discover_handler."""

    @pytest.mark.asyncio
    @patch("src.bot.handlers.discover.is_authorized", return_value=False)
    async def test_unauthorized_no_response(
        self, mock_auth: MagicMock, mock_update: MagicMock, mock_context: MagicMock
    ) -> None:
        """Unauthorized user gets no response."""
        await discover_handler(mock_update, mock_context)
        mock_update.message.reply_text.assert_not_called()

    @pytest.mark.asyncio
    @patch("src.bot.handlers.discover.is_authorized", return_value=True)
    @patch("src.bot.handlers.discover.async_session_factory")
    async def test_candidates_returns_formatted_cards(
        self, mock_session_factory: MagicMock, mock_auth: MagicMock,
        mock_update: MagicMock, mock_context: MagicMock
    ) -> None:
        """Discover with candidates returns formatted cards with HTML."""
        # Create mock candidates
        candidate1 = MagicMock()
        candidate1.symbol = "BBCA"
        candidate1.name = "Bank Central Asia"
        candidate1.asset_type = "stock"
        candidate1.composite_score = 0.85
        candidate1.triggers = {"volume_spike": 0.8, "price_breakout": 0.6}
        candidate1.current_price = 9500.0
        candidate1.price_change_pct = 3.5
        candidate1.volume_ratio = 2.5

        candidate2 = MagicMock()
        candidate2.symbol = "BBRI"
        candidate2.name = "Bank Rakyat Indonesia"
        candidate2.asset_type = "stock"
        candidate2.composite_score = 0.72
        candidate2.triggers = {"momentum_surge": 0.7}
        candidate2.current_price = 5100.0
        candidate2.price_change_pct = 2.1
        candidate2.volume_ratio = 1.8

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [candidate1, candidate2]
        mock_session.execute = AsyncMock(return_value=mock_result)

        mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=False)

        await discover_handler(mock_update, mock_context)

        call_args = mock_update.message.reply_text.call_args
        msg = call_args[0][0]
        assert "Today's Discoveries" in msg
        assert "BBCA" in msg
        assert "BBRI" in msg
        assert call_args[1]["parse_mode"] == "HTML"

    @pytest.mark.asyncio
    @patch("src.bot.handlers.discover.is_authorized", return_value=True)
    @patch("src.bot.handlers.discover.async_session_factory")
    async def test_no_candidates_returns_empty_state(
        self, mock_session_factory: MagicMock, mock_auth: MagicMock,
        mock_update: MagicMock, mock_context: MagicMock
    ) -> None:
        """Discover with no candidates returns empty state message."""
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute = AsyncMock(return_value=mock_result)

        mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=False)

        await discover_handler(mock_update, mock_context)

        call_args = mock_update.message.reply_text.call_args
        assert "No new opportunities" in call_args[0][0]

    @pytest.mark.asyncio
    @patch("src.bot.handlers.discover.is_authorized", return_value=True)
    @patch("src.bot.handlers.discover.async_session_factory")
    async def test_db_error_returns_error_state(
        self, mock_session_factory: MagicMock, mock_auth: MagicMock,
        mock_update: MagicMock, mock_context: MagicMock
    ) -> None:
        """DB error returns error state message containing 'unavailable'."""
        mock_session_factory.return_value.__aenter__ = AsyncMock(
            side_effect=RuntimeError("DB connection failed")
        )
        mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=False)

        await discover_handler(mock_update, mock_context)

        call_args = mock_update.message.reply_text.call_args
        assert "unavailable" in call_args[0][0]
