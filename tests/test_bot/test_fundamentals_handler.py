"""Tests for /fundamentals command handler (TBOT-13)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.bot.handlers.fundamentals import fundamentals_handler


class TestFundamentalsHandler:
    """Tests for fundamentals_handler."""

    @pytest.mark.asyncio
    @patch("src.bot.handlers.fundamentals.is_authorized", return_value=True)
    @patch("src.bot.handlers.fundamentals.async_session_factory")
    async def test_valid_stock_returns_dashboard(
        self, mock_session_factory: MagicMock, mock_auth: MagicMock,
        mock_update: MagicMock, mock_context: MagicMock
    ) -> None:
        """Valid stock symbol returns fundamentals dashboard message."""
        mock_context.args = ["BBCA"]

        mock_asset = MagicMock()
        mock_asset.id = 1
        mock_asset.symbol = "BBCA"
        mock_asset.asset_type = "stock"
        mock_asset.name = "Bank Central Asia"

        mock_fundamental = MagicMock()
        mock_fundamental.trailing_pe = 12.5
        mock_fundamental.price_to_book = 2.1
        mock_fundamental.return_on_equity = 0.18
        mock_fundamental.debt_to_equity = 0.5
        mock_fundamental.revenue_growth = None

        mock_session = AsyncMock()
        call_count = 0

        async def mock_execute(stmt):
            nonlocal call_count
            call_count += 1
            result = MagicMock()
            if call_count == 1:
                result.scalar_one_or_none.return_value = mock_asset
            elif call_count == 2:
                # FinancialData query
                scalars_mock = MagicMock()
                scalars_mock.all.return_value = []
                result.scalars.return_value = scalars_mock
            elif call_count == 3:
                result.scalar_one_or_none.return_value = mock_fundamental
            return result

        mock_session.execute = mock_execute
        mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=False)

        await fundamentals_handler(mock_update, mock_context)
        call_args = mock_update.message.reply_text.call_args
        msg = call_args[0][0]
        assert "Fundamentals" in msg
        assert "BBCA" in msg
        assert call_args[1]["parse_mode"] == "HTML"

    @pytest.mark.asyncio
    @patch("src.bot.handlers.fundamentals.is_authorized", return_value=True)
    @patch("src.bot.handlers.fundamentals.async_session_factory")
    async def test_crypto_sends_rejection(
        self, mock_session_factory: MagicMock, mock_auth: MagicMock,
        mock_update: MagicMock, mock_context: MagicMock
    ) -> None:
        """Crypto asset gets rejection message."""
        mock_context.args = ["ETH"]

        mock_asset = MagicMock()
        mock_asset.symbol = "ETH"
        mock_asset.asset_type = "crypto"
        mock_asset.name = "Ethereum"

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_asset
        mock_session.execute = AsyncMock(return_value=mock_result)

        mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=False)

        await fundamentals_handler(mock_update, mock_context)
        call_args = mock_update.message.reply_text.call_args
        assert "not available for crypto" in call_args[0][0]

    @pytest.mark.asyncio
    @patch("src.bot.handlers.fundamentals.is_authorized", return_value=True)
    @patch("src.bot.handlers.fundamentals.async_session_factory")
    async def test_no_data_sends_empty_state(
        self, mock_session_factory: MagicMock, mock_auth: MagicMock,
        mock_update: MagicMock, mock_context: MagicMock
    ) -> None:
        """No data sends empty state message."""
        mock_context.args = ["BBCA"]

        mock_asset = MagicMock()
        mock_asset.id = 1
        mock_asset.symbol = "BBCA"
        mock_asset.asset_type = "stock"
        mock_asset.name = "Bank Central Asia"

        mock_session = AsyncMock()
        call_count = 0

        async def mock_execute(stmt):
            nonlocal call_count
            call_count += 1
            result = MagicMock()
            if call_count == 1:
                result.scalar_one_or_none.return_value = mock_asset
            elif call_count == 2:
                scalars_mock = MagicMock()
                scalars_mock.all.return_value = []
                result.scalars.return_value = scalars_mock
            elif call_count == 3:
                result.scalar_one_or_none.return_value = None
            return result

        mock_session.execute = mock_execute
        mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=False)

        await fundamentals_handler(mock_update, mock_context)
        call_args = mock_update.message.reply_text.call_args
        assert "No fundamental data available" in call_args[0][0]
