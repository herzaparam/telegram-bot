"""Tests for bot command handlers."""

from __future__ import annotations

import importlib
import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.bot.handlers.report import report_handler
from src.bot.handlers.settings import settings_handler
from src.bot.handlers.start import start_handler
from src.bot.handlers.watchlist import add_handler, remove_handler, watchlist_handler


class TestStartHandler:
    """Tests for /start command."""

    @pytest.mark.asyncio
    @patch("src.bot.handlers.start.is_authorized", return_value=True)
    async def test_authorized_user_gets_welcome(
        self, mock_auth: MagicMock, mock_update: MagicMock, mock_context: MagicMock
    ) -> None:
        """Authorized user receives welcome message with 'Welcome to Trade Signal Agent'."""
        await start_handler(mock_update, mock_context)
        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args
        assert "Welcome to Trade Signal Agent" in call_args[0][0]
        assert call_args[1]["parse_mode"] == "HTML"

    @pytest.mark.asyncio
    @patch("src.bot.handlers.start.is_authorized", return_value=False)
    async def test_unauthorized_user_gets_nothing(
        self, mock_auth: MagicMock, mock_update: MagicMock, mock_context: MagicMock
    ) -> None:
        """Unauthorized user does not get a reply."""
        await start_handler(mock_update, mock_context)
        mock_update.message.reply_text.assert_not_called()


class TestAddHandler:
    """Tests for /add command."""

    @pytest.mark.asyncio
    @patch("src.bot.handlers.watchlist.is_authorized", return_value=True)
    async def test_no_args_shows_error(
        self, mock_auth: MagicMock, mock_update: MagicMock, mock_context: MagicMock
    ) -> None:
        """Missing symbol argument replies with error."""
        mock_context.args = []
        await add_handler(mock_update, mock_context)
        call_args = mock_update.message.reply_text.call_args
        assert "Please specify a symbol" in call_args[0][0]

    @pytest.mark.asyncio
    @patch("src.bot.handlers.watchlist.is_authorized", return_value=False)
    async def test_unauthorized_no_reply(
        self, mock_auth: MagicMock, mock_update: MagicMock, mock_context: MagicMock
    ) -> None:
        """Unauthorized user does not get a reply."""
        mock_context.args = ["BBCA"]
        await add_handler(mock_update, mock_context)
        mock_update.message.reply_text.assert_not_called()


class TestRemoveHandler:
    """Tests for /remove command."""

    @pytest.mark.asyncio
    @patch("src.bot.handlers.watchlist.is_authorized", return_value=True)
    async def test_not_in_watchlist(
        self, mock_auth: MagicMock, mock_update: MagicMock, mock_context: MagicMock
    ) -> None:
        """Removing asset not in watchlist replies accordingly."""
        mock_context.args = ["XYZ"]

        # Mock the session to return no result
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)

        mock_ctx = AsyncMock()
        mock_ctx.__aenter__ = AsyncMock(return_value=mock_session)
        mock_ctx.__aexit__ = AsyncMock(return_value=None)

        with patch("src.bot.handlers.watchlist.async_session_factory", return_value=mock_ctx):
            await remove_handler(mock_update, mock_context)

        call_text = mock_update.message.reply_text.call_args[0][0]
        assert "not in your watchlist" in call_text

    @pytest.mark.asyncio
    @patch("src.bot.handlers.watchlist.is_authorized", return_value=True)
    async def test_no_args_shows_error(
        self, mock_auth: MagicMock, mock_update: MagicMock, mock_context: MagicMock
    ) -> None:
        """Missing symbol argument replies with error."""
        mock_context.args = []
        await remove_handler(mock_update, mock_context)
        call_text = mock_update.message.reply_text.call_args[0][0]
        assert "Please specify a symbol" in call_text


class TestWatchlistHandler:
    """Tests for /watchlist command."""

    @pytest.mark.asyncio
    @patch("src.bot.handlers.watchlist.is_authorized", return_value=True)
    async def test_empty_watchlist(
        self, mock_auth: MagicMock, mock_update: MagicMock, mock_context: MagicMock
    ) -> None:
        """Empty watchlist replies with appropriate message."""
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.all.return_value = []
        mock_session.execute = AsyncMock(return_value=mock_result)

        mock_ctx = AsyncMock()
        mock_ctx.__aenter__ = AsyncMock(return_value=mock_session)
        mock_ctx.__aexit__ = AsyncMock(return_value=None)

        with patch("src.bot.handlers.watchlist.async_session_factory", return_value=mock_ctx):
            await watchlist_handler(mock_update, mock_context)

        call_text = mock_update.message.reply_text.call_args[0][0]
        assert "No assets in your watchlist" in call_text


class TestReportHandler:
    """Tests for /report command."""

    @pytest.mark.asyncio
    @patch("src.bot.handlers.report.is_authorized", return_value=True)
    async def test_empty_watchlist(
        self, mock_auth: MagicMock, mock_update: MagicMock, mock_context: MagicMock
    ) -> None:
        """Empty watchlist replies with 'No assets in your watchlist'."""
        mock_context.args = []

        mock_session = AsyncMock()
        # First query: watchlist asset IDs (empty)
        mock_wl_result = MagicMock()
        mock_wl_result.all.return_value = []
        mock_session.execute = AsyncMock(return_value=mock_wl_result)

        mock_ctx = AsyncMock()
        mock_ctx.__aenter__ = AsyncMock(return_value=mock_session)
        mock_ctx.__aexit__ = AsyncMock(return_value=None)

        with patch("src.bot.handlers.report.async_session_factory", return_value=mock_ctx):
            await report_handler(mock_update, mock_context)

        call_text = mock_update.message.reply_text.call_args[0][0]
        assert "No assets in your watchlist" in call_text

    @pytest.mark.asyncio
    @patch("src.bot.handlers.report.is_authorized", return_value=False)
    async def test_unauthorized_no_reply(
        self, mock_auth: MagicMock, mock_update: MagicMock, mock_context: MagicMock
    ) -> None:
        """Unauthorized user does not get a reply."""
        mock_context.args = []
        await report_handler(mock_update, mock_context)
        mock_update.message.reply_text.assert_not_called()


class TestSettingsHandler:
    """Tests for /settings command."""

    @pytest.mark.asyncio
    @patch("src.bot.handlers.settings.is_authorized", return_value=True)
    async def test_show_settings_no_args(
        self, mock_auth: MagicMock, mock_update: MagicMock, mock_context: MagicMock
    ) -> None:
        """No args shows current delivery time."""
        mock_context.args = []

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None  # No setting yet, uses default
        mock_session.execute = AsyncMock(return_value=mock_result)

        mock_ctx = AsyncMock()
        mock_ctx.__aenter__ = AsyncMock(return_value=mock_session)
        mock_ctx.__aexit__ = AsyncMock(return_value=None)

        with patch("src.bot.handlers.settings.async_session_factory", return_value=mock_ctx):
            await settings_handler(mock_update, mock_context)

        call_text = mock_update.message.reply_text.call_args[0][0]
        assert "Delivery time:" in call_text

    @pytest.mark.asyncio
    @patch("src.bot.handlers.settings.is_authorized", return_value=True)
    async def test_invalid_time_out_of_range(
        self, mock_auth: MagicMock, mock_update: MagicMock, mock_context: MagicMock
    ) -> None:
        """Time outside 06:00-09:00 range returns error."""
        mock_context.args = ["time", "05:00"]
        await settings_handler(mock_update, mock_context)
        call_text = mock_update.message.reply_text.call_args[0][0]
        assert "Invalid time" in call_text

    @pytest.mark.asyncio
    @patch("src.bot.handlers.settings.is_authorized", return_value=True)
    async def test_invalid_time_too_late(
        self, mock_auth: MagicMock, mock_update: MagicMock, mock_context: MagicMock
    ) -> None:
        """Time at 10:00 is rejected."""
        mock_context.args = ["time", "10:00"]
        await settings_handler(mock_update, mock_context)
        call_text = mock_update.message.reply_text.call_args[0][0]
        assert "Invalid time" in call_text


class TestTwoProcessBoundary:
    """Verify bot modules do not import from pipeline or llm."""

    def test_no_pipeline_or_llm_imports_in_bot(self) -> None:
        """All src/bot/ modules must not import from src.pipeline or src.llm."""
        import ast
        import pathlib

        bot_dir = pathlib.Path("src/bot")
        violations: list[str] = []

        for py_file in bot_dir.rglob("*.py"):
            source = py_file.read_text()
            tree = ast.parse(source)
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom) and node.module:
                    if node.module.startswith("src.pipeline") or node.module.startswith("src.llm"):
                        violations.append(f"{py_file}: from {node.module}")
                elif isinstance(node, ast.Import):
                    for alias in node.names:
                        if alias.name.startswith("src.pipeline") or alias.name.startswith("src.llm"):
                            violations.append(f"{py_file}: import {alias.name}")

        assert violations == [], f"Two-process boundary violations: {violations}"
