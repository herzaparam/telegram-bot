"""Tests for bot command handlers."""

from __future__ import annotations

import importlib
import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.bot.handlers.report import report_handler
from src.bot.handlers.scorecard import scorecard_handler
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


class TestScorecardHandler:
    """Tests for /scorecard command handler."""

    @pytest.mark.asyncio
    @patch("src.bot.handlers.scorecard.is_authorized", return_value=True)
    async def test_scorecard_sends_formatted_message(
        self, mock_auth: MagicMock, mock_update: MagicMock, mock_context: MagicMock
    ) -> None:
        """Scorecard handler sends formatted message with scorecard data."""
        mock_context.args = []

        mock_session = AsyncMock()
        # Mock execute() to return a result with scalars().all() -> []
        mock_execute_result = MagicMock()
        mock_execute_result.scalars.return_value.all.return_value = []
        mock_session.execute = AsyncMock(return_value=mock_execute_result)

        mock_ctx = AsyncMock()
        mock_ctx.__aenter__ = AsyncMock(return_value=mock_session)
        mock_ctx.__aexit__ = AsyncMock(return_value=None)

        scorecard_data = {
            "win_rates_by_window": {"24h": (39, 60)},
            "total_decisions": 60,
            "best_engine": ("Technical", 72.0),
            "worst_engine": ("Quantitative", 48.0),
            "per_asset_buyhold": [],
        }

        with (
            patch("src.bot.handlers.scorecard.async_session_factory", return_value=mock_ctx),
            patch("src.bot.handlers.scorecard.evaluation_repo") as mock_repo,
        ):
            mock_repo.get_scorecard_data = AsyncMock(return_value=scorecard_data)
            await scorecard_handler(mock_update, mock_context)

        call_text = mock_update.message.reply_text.call_args[0][0]
        assert "Scorecard" in call_text
        assert "Technical" in call_text
        assert parse_mode_is_html(mock_update)

    @pytest.mark.asyncio
    @patch("src.bot.handlers.scorecard.is_authorized", return_value=False)
    async def test_scorecard_unauthorized_no_reply(
        self, mock_auth: MagicMock, mock_update: MagicMock, mock_context: MagicMock
    ) -> None:
        """Unauthorized user does not get a reply."""
        mock_context.args = []
        await scorecard_handler(mock_update, mock_context)
        mock_update.message.reply_text.assert_not_called()


class TestScorecardParsing:
    """Tests for /scorecard argument parsing."""

    @pytest.mark.asyncio
    @patch("src.bot.handlers.scorecard.is_authorized", return_value=True)
    async def test_period_arg_sets_period(
        self, mock_auth: MagicMock, mock_update: MagicMock, mock_context: MagicMock
    ) -> None:
        """'30d' sets period to 30d."""
        mock_context.args = ["30d"]

        mock_session = AsyncMock()
        mock_execute_result = MagicMock()
        mock_execute_result.scalars.return_value.all.return_value = []
        mock_session.execute = AsyncMock(return_value=mock_execute_result)

        mock_ctx = AsyncMock()
        mock_ctx.__aenter__ = AsyncMock(return_value=mock_session)
        mock_ctx.__aexit__ = AsyncMock(return_value=None)

        scorecard_data = {
            "win_rates_by_window": {"24h": (10, 20)},
            "total_decisions": 20,
            "best_engine": None,
            "worst_engine": None,
            "per_asset_buyhold": [],
        }

        with (
            patch("src.bot.handlers.scorecard.async_session_factory", return_value=mock_ctx),
            patch("src.bot.handlers.scorecard.evaluation_repo") as mock_repo,
        ):
            mock_repo.get_scorecard_data = AsyncMock(return_value=scorecard_data)
            await scorecard_handler(mock_update, mock_context)
            mock_repo.get_scorecard_data.assert_called_once_with(mock_session, "30d", None)

    @pytest.mark.asyncio
    @patch("src.bot.handlers.scorecard.is_authorized", return_value=True)
    async def test_asset_arg_sets_filter(
        self, mock_auth: MagicMock, mock_update: MagicMock, mock_context: MagicMock
    ) -> None:
        """'BTC' sets asset_filter to BTC."""
        mock_context.args = ["BTC"]

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = 1  # asset_id = 1
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute = AsyncMock(return_value=mock_result)

        mock_ctx = AsyncMock()
        mock_ctx.__aenter__ = AsyncMock(return_value=mock_session)
        mock_ctx.__aexit__ = AsyncMock(return_value=None)

        scorecard_data = {
            "win_rates_by_window": {"24h": (10, 20)},
            "total_decisions": 20,
            "best_engine": None,
            "worst_engine": None,
            "per_asset_buyhold": [],
        }

        with (
            patch("src.bot.handlers.scorecard.async_session_factory", return_value=mock_ctx),
            patch("src.bot.handlers.scorecard.evaluation_repo") as mock_repo,
        ):
            mock_repo.get_scorecard_data = AsyncMock(return_value=scorecard_data)
            mock_repo.get_recent_evaluations = AsyncMock(return_value=[])
            await scorecard_handler(mock_update, mock_context)
            # Should have called with asset_id=1
            mock_repo.get_scorecard_data.assert_called_once_with(mock_session, "30d", 1)

    @pytest.mark.asyncio
    @patch("src.bot.handlers.scorecard.is_authorized", return_value=True)
    async def test_period_and_asset_args(
        self, mock_auth: MagicMock, mock_update: MagicMock, mock_context: MagicMock
    ) -> None:
        """'7d BTC' sets both period and asset_filter."""
        mock_context.args = ["7d", "BTC"]

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = 1
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute = AsyncMock(return_value=mock_result)

        mock_ctx = AsyncMock()
        mock_ctx.__aenter__ = AsyncMock(return_value=mock_session)
        mock_ctx.__aexit__ = AsyncMock(return_value=None)

        scorecard_data = {
            "win_rates_by_window": {"24h": (10, 20)},
            "total_decisions": 20,
            "best_engine": None,
            "worst_engine": None,
            "per_asset_buyhold": [],
        }

        with (
            patch("src.bot.handlers.scorecard.async_session_factory", return_value=mock_ctx),
            patch("src.bot.handlers.scorecard.evaluation_repo") as mock_repo,
        ):
            mock_repo.get_scorecard_data = AsyncMock(return_value=scorecard_data)
            mock_repo.get_recent_evaluations = AsyncMock(return_value=[])
            await scorecard_handler(mock_update, mock_context)
            mock_repo.get_scorecard_data.assert_called_once_with(mock_session, "7d", 1)


class TestScorecardInvalidPeriod:
    """Tests for invalid period argument."""

    @pytest.mark.asyncio
    @patch("src.bot.handlers.scorecard.is_authorized", return_value=True)
    async def test_invalid_period_returns_error(
        self, mock_auth: MagicMock, mock_update: MagicMock, mock_context: MagicMock
    ) -> None:
        """'5d' returns error message."""
        mock_context.args = ["5d"]
        await scorecard_handler(mock_update, mock_context)
        call_text = mock_update.message.reply_text.call_args[0][0]
        assert "Invalid period" in call_text
        assert "7d, 30d, 90d, or all" in call_text


class TestScorecardUnknownAsset:
    """Tests for unknown asset filter."""

    @pytest.mark.asyncio
    @patch("src.bot.handlers.scorecard.is_authorized", return_value=True)
    async def test_unknown_asset_returns_error(
        self, mock_auth: MagicMock, mock_update: MagicMock, mock_context: MagicMock
    ) -> None:
        """Asset not in watchlist returns error."""
        mock_context.args = ["XYZ"]

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)

        mock_ctx = AsyncMock()
        mock_ctx.__aenter__ = AsyncMock(return_value=mock_session)
        mock_ctx.__aexit__ = AsyncMock(return_value=None)

        with patch("src.bot.handlers.scorecard.async_session_factory", return_value=mock_ctx):
            await scorecard_handler(mock_update, mock_context)

        call_text = mock_update.message.reply_text.call_args[0][0]
        assert "not found in your watchlist" in call_text
        assert "XYZ" in call_text


class TestScorecardEmpty:
    """Tests for empty scorecard state."""

    @pytest.mark.asyncio
    @patch("src.bot.handlers.scorecard.is_authorized", return_value=True)
    async def test_no_data_returns_empty_state(
        self, mock_auth: MagicMock, mock_update: MagicMock, mock_context: MagicMock
    ) -> None:
        """No data returns empty state message."""
        mock_context.args = []

        mock_session = AsyncMock()
        mock_execute_result = MagicMock()
        mock_execute_result.scalars.return_value.all.return_value = []
        mock_session.execute = AsyncMock(return_value=mock_execute_result)

        mock_ctx = AsyncMock()
        mock_ctx.__aenter__ = AsyncMock(return_value=mock_session)
        mock_ctx.__aexit__ = AsyncMock(return_value=None)

        empty_data = {
            "win_rates_by_window": {},
            "total_decisions": 0,
            "best_engine": None,
            "worst_engine": None,
            "per_asset_buyhold": [],
        }

        with (
            patch("src.bot.handlers.scorecard.async_session_factory", return_value=mock_ctx),
            patch("src.bot.handlers.scorecard.evaluation_repo") as mock_repo,
        ):
            mock_repo.get_scorecard_data = AsyncMock(return_value=empty_data)
            await scorecard_handler(mock_update, mock_context)

        call_text = mock_update.message.reply_text.call_args[0][0]
        assert "No evaluations in the last" in call_text or "No scorecard data" in call_text


def parse_mode_is_html(mock_update: MagicMock) -> bool:
    """Helper to check if reply_text was called with parse_mode='HTML'."""
    call_kwargs = mock_update.message.reply_text.call_args[1]
    return call_kwargs.get("parse_mode") == "HTML"


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
