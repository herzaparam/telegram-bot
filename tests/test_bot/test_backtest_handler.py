"""Tests for /backtest bot handler (TBOT-08)."""

from __future__ import annotations

from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.fixture
def mock_update():
    """Create a mock Telegram Update."""
    update = MagicMock()
    update.effective_chat.id = 12345
    update.message.reply_text = AsyncMock()
    return update


@pytest.fixture
def mock_context():
    """Create a mock context with no args."""
    ctx = MagicMock()
    ctx.args = []
    return ctx


@pytest.fixture
def sample_cached_result():
    """Mock BacktestResult from DB."""
    result = MagicMock()
    result.win_rate = 0.65
    result.total_return = 0.123
    result.buy_hold_return = 0.081
    result.max_drawdown = -0.152
    result.sharpe_ratio = 1.4
    result.daily_results = {"days_tested": 30}
    return result


class TestBacktestHandler:
    """Tests for the backtest_handler function."""

    @pytest.mark.asyncio
    async def test_no_args_shows_usage(self, mock_update, mock_context):
        """No args returns usage message."""
        from src.bot.handlers.backtest import backtest_handler

        with patch("src.bot.handlers.backtest.is_authorized", return_value=True):
            await backtest_handler(mock_update, mock_context)

        mock_update.message.reply_text.assert_called_once()
        call_text = mock_update.message.reply_text.call_args[0][0]
        assert "/backtest" in call_text
        assert "7d" in call_text

    @pytest.mark.asyncio
    async def test_invalid_period(self, mock_update, mock_context):
        """Invalid period returns error message."""
        from src.bot.handlers.backtest import backtest_handler

        mock_context.args = ["BTC", "invalid"]

        with patch("src.bot.handlers.backtest.is_authorized", return_value=True):
            await backtest_handler(mock_update, mock_context)

        call_text = mock_update.message.reply_text.call_args[0][0]
        assert "Invalid period" in call_text

    @pytest.mark.asyncio
    async def test_cached_result_no_subprocess(self, mock_update, mock_context, sample_cached_result):
        """Cached result returns immediately without spawning subprocess."""
        from src.bot.handlers.backtest import backtest_handler

        mock_context.args = ["BTC", "30d"]

        mock_asset = MagicMock()
        mock_asset.id = 1
        mock_asset.symbol = "BTC"

        mock_session = AsyncMock()
        # First execute: asset lookup
        asset_result = MagicMock()
        asset_result.scalar_one_or_none.return_value = mock_asset
        # Second execute: cached result
        cached_query = MagicMock()
        cached_query.scalar_one_or_none.return_value = sample_cached_result
        mock_session.execute = AsyncMock(side_effect=[asset_result, cached_query])

        with (
            patch("src.bot.handlers.backtest.is_authorized", return_value=True),
            patch("src.bot.handlers.backtest.async_session_factory") as mock_factory,
            patch("src.bot.handlers.backtest.asyncio.create_subprocess_exec") as mock_subproc,
        ):
            mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)
            await backtest_handler(mock_update, mock_context)

        # Subprocess should NOT have been called
        mock_subproc.assert_not_called()
        # Reply should contain win rate
        call_text = mock_update.message.reply_text.call_args[0][0]
        assert "65.0%" in call_text

    @pytest.mark.asyncio
    async def test_subprocess_success(self, mock_update, mock_context):
        """Successful subprocess returns formatted results."""
        from src.bot.handlers.backtest import backtest_handler

        mock_context.args = ["BTC", "30d"]

        # No cached result
        mock_session = AsyncMock()
        asset_result = MagicMock()
        asset_result.scalar_one_or_none.return_value = MagicMock(id=1)
        cached_query = MagicMock()
        cached_query.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(side_effect=[asset_result, cached_query])

        # Mock subprocess
        result_json = '{"status": "complete", "symbol": "BTC", "period": "30d", "win_rate": 0.6, "total_return": 0.12, "buy_hold_return": 0.08, "max_drawdown": -0.15, "sharpe_ratio": 1.2, "days_tested": 25}'
        mock_proc = AsyncMock()
        mock_proc.communicate = AsyncMock(return_value=(result_json.encode(), b""))
        mock_proc.returncode = 0

        # msg returned by reply_text
        mock_msg = AsyncMock()
        mock_update.message.reply_text = AsyncMock(return_value=mock_msg)

        with (
            patch("src.bot.handlers.backtest.is_authorized", return_value=True),
            patch("src.bot.handlers.backtest.async_session_factory") as mock_factory,
            patch("src.bot.handlers.backtest.asyncio.create_subprocess_exec", return_value=mock_proc),
            patch("src.bot.handlers.backtest.asyncio.wait_for", return_value=(result_json.encode(), b"")),
        ):
            mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)
            await backtest_handler(mock_update, mock_context)

        # Should have edited the message with results
        mock_msg.edit_text.assert_called()
        edit_text = mock_msg.edit_text.call_args[0][0]
        assert "BTC" in edit_text
        assert "60.0%" in edit_text

    @pytest.mark.asyncio
    async def test_subprocess_error(self, mock_update, mock_context):
        """Subprocess returning error status shows error message."""
        from src.bot.handlers.backtest import backtest_handler

        mock_context.args = ["UNKNOWN", "30d"]

        mock_session = AsyncMock()
        asset_result = MagicMock()
        asset_result.scalar_one_or_none.return_value = None  # asset not found in cache check
        mock_session.execute = AsyncMock(return_value=asset_result)

        # Mock subprocess returning error
        result_json = '{"status": "error", "message": "Asset not found: UNKNOWN"}'
        mock_proc = AsyncMock()
        mock_proc.communicate = AsyncMock(return_value=(result_json.encode(), b""))
        mock_proc.returncode = 0

        mock_msg = AsyncMock()
        mock_update.message.reply_text = AsyncMock(return_value=mock_msg)

        with (
            patch("src.bot.handlers.backtest.is_authorized", return_value=True),
            patch("src.bot.handlers.backtest.async_session_factory") as mock_factory,
            patch("src.bot.handlers.backtest.asyncio.create_subprocess_exec", return_value=mock_proc),
            patch("src.bot.handlers.backtest.asyncio.wait_for", return_value=(result_json.encode(), b"")),
        ):
            mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)
            await backtest_handler(mock_update, mock_context)

        mock_msg.edit_text.assert_called()
        edit_text = mock_msg.edit_text.call_args[0][0]
        assert "not found" in edit_text.lower() or "error" in edit_text.lower()

    @pytest.mark.asyncio
    async def test_unauthorized_returns_early(self, mock_update, mock_context):
        """Unauthorized user gets no response."""
        from src.bot.handlers.backtest import backtest_handler

        with patch("src.bot.handlers.backtest.is_authorized", return_value=False):
            await backtest_handler(mock_update, mock_context)

        mock_update.message.reply_text.assert_not_called()


class TestTwoProcessBoundary:
    """Verify the handler does not import pipeline or LLM modules."""

    def test_no_pipeline_imports(self):
        """backtest handler should not import from src.pipeline or src.llm."""
        import inspect
        from src.bot.handlers import backtest

        source = inspect.getsource(backtest)
        assert "from src.pipeline" not in source
        assert "from src.llm" not in source
        assert "import src.pipeline" not in source
        assert "import src.llm" not in source

    def test_uses_subprocess_exec(self):
        """Handler should use create_subprocess_exec for backtest."""
        import inspect
        from src.bot.handlers import backtest

        source = inspect.getsource(backtest)
        assert "create_subprocess_exec" in source
        assert "src.data.backtest" in source
