"""Tests for /valuation command handler (TBOT-09)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.bot.handlers.valuation import valuation_handler


class TestValuationHandler:
    """Tests for valuation_handler."""

    @pytest.mark.asyncio
    @patch("src.bot.handlers.valuation.is_authorized", return_value=True)
    async def test_no_args_sends_error(
        self, mock_auth: MagicMock, mock_update: MagicMock, mock_context: MagicMock
    ) -> None:
        """Missing symbol argument replies with error containing 'Please specify'."""
        mock_context.args = []
        await valuation_handler(mock_update, mock_context)
        call_args = mock_update.message.reply_text.call_args
        assert "Please specify" in call_args[0][0]

    @pytest.mark.asyncio
    @patch("src.bot.handlers.valuation.is_authorized", return_value=True)
    @patch("src.bot.handlers.valuation.async_session_factory")
    async def test_crypto_symbol_sends_rejection(
        self, mock_session_factory: MagicMock, mock_auth: MagicMock,
        mock_update: MagicMock, mock_context: MagicMock
    ) -> None:
        """Crypto asset gets rejection message containing 'not available for crypto'."""
        mock_context.args = ["BTC"]

        # Mock asset with crypto type
        mock_asset = MagicMock()
        mock_asset.symbol = "BTC"
        mock_asset.asset_type = "crypto"
        mock_asset.name = "Bitcoin"

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_asset
        mock_session.execute = AsyncMock(return_value=mock_result)

        mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=False)

        await valuation_handler(mock_update, mock_context)
        call_args = mock_update.message.reply_text.call_args
        assert "not available for crypto" in call_args[0][0]

    @pytest.mark.asyncio
    @patch("src.bot.handlers.valuation.is_authorized", return_value=True)
    @patch("src.bot.handlers.valuation.async_session_factory")
    async def test_unknown_symbol_sends_not_found(
        self, mock_session_factory: MagicMock, mock_auth: MagicMock,
        mock_update: MagicMock, mock_context: MagicMock
    ) -> None:
        """Unknown symbol sends 'not found' message."""
        mock_context.args = ["ZZXX"]

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)

        mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=False)

        await valuation_handler(mock_update, mock_context)
        call_args = mock_update.message.reply_text.call_args
        assert "not found" in call_args[0][0]

    @pytest.mark.asyncio
    @patch("src.bot.handlers.valuation.is_authorized", return_value=True)
    @patch("src.bot.handlers.valuation.async_session_factory")
    async def test_valid_stock_sends_formatted_message(
        self, mock_session_factory: MagicMock, mock_auth: MagicMock,
        mock_update: MagicMock, mock_context: MagicMock
    ) -> None:
        """Valid stock symbol queries DB and sends formatted valuation message."""
        mock_context.args = ["BBCA"]

        # Mock asset
        mock_asset = MagicMock()
        mock_asset.id = 1
        mock_asset.symbol = "BBCA"
        mock_asset.asset_type = "stock"
        mock_asset.name = "Bank Central Asia"

        # Mock signal with indicators
        mock_signal = MagicMock()
        mock_signal.date = "2025-10-15"
        mock_signal.indicators = {
            "fair_value": 10000.0,
            "margin_of_safety": 0.21,
            "current_price": 8250.0,
            "scenarios": {
                "bull": {"value": 12000, "return_pct": 0.45},
                "base": {"value": 10000, "return_pct": 0.21},
                "bear": {"value": 8000, "return_pct": -0.03},
            },
            "peer_comparison": {
                "pe": {"value": 10.0, "sector_avg": 15.0, "rank": "cheap"},
            },
            "sector": "banking",
            "period": "Q3-2025",
            "has_pdf_data": True,
        }

        # Mock fundamental (not needed since we have signal)
        mock_fundamental = None

        mock_session = AsyncMock()
        call_count = 0

        async def mock_execute(stmt):
            nonlocal call_count
            call_count += 1
            result = MagicMock()
            if call_count == 1:
                # Asset lookup
                result.scalar_one_or_none.return_value = mock_asset
            elif call_count == 2:
                # Signal lookup
                result.scalar_one_or_none.return_value = mock_signal
            elif call_count == 3:
                # Fundamental lookup
                result.scalar_one_or_none.return_value = mock_fundamental
            return result

        mock_session.execute = mock_execute

        mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=False)

        await valuation_handler(mock_update, mock_context)
        call_args = mock_update.message.reply_text.call_args
        msg = call_args[0][0]
        assert "<b>Valuation" in msg
        assert "BBCA" in msg
        assert call_args[1]["parse_mode"] == "HTML"
