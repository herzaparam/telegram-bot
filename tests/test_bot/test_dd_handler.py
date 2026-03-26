"""Tests for /duediligence command handler (TBOT-11)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.bot.handlers.duediligence import duediligence_handler


class TestDueDiligenceHandler:
    """Tests for duediligence_handler."""

    @pytest.mark.asyncio
    @patch("src.bot.handlers.duediligence.is_authorized", return_value=False)
    async def test_unauthorized_no_response(
        self, mock_auth: MagicMock, mock_update: MagicMock, mock_context: MagicMock
    ) -> None:
        """Unauthorized user gets no response."""
        await duediligence_handler(mock_update, mock_context)
        mock_update.message.reply_text.assert_not_called()

    @pytest.mark.asyncio
    @patch("src.bot.handlers.duediligence.is_authorized", return_value=True)
    async def test_no_symbol_returns_error(
        self, mock_auth: MagicMock, mock_update: MagicMock, mock_context: MagicMock
    ) -> None:
        """Missing symbol argument replies with 'Please specify' error."""
        mock_context.args = []
        await duediligence_handler(mock_update, mock_context)
        call_args = mock_update.message.reply_text.call_args
        assert "Please specify" in call_args[0][0]

    @pytest.mark.asyncio
    @patch("src.bot.handlers.duediligence.is_authorized", return_value=True)
    @patch("src.bot.handlers.duediligence.async_session_factory")
    async def test_crypto_symbol_returns_rejection(
        self, mock_session_factory: MagicMock, mock_auth: MagicMock,
        mock_update: MagicMock, mock_context: MagicMock
    ) -> None:
        """Crypto asset gets rejection message."""
        mock_context.args = ["BTC"]

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

        await duediligence_handler(mock_update, mock_context)
        call_args = mock_update.message.reply_text.call_args
        assert "not available for crypto" in call_args[0][0]

    @pytest.mark.asyncio
    @patch("src.bot.handlers.duediligence.is_authorized", return_value=True)
    @patch("src.bot.handlers.duediligence.async_session_factory")
    async def test_unknown_symbol_returns_not_found(
        self, mock_session_factory: MagicMock, mock_auth: MagicMock,
        mock_update: MagicMock, mock_context: MagicMock
    ) -> None:
        """Unknown symbol returns 'not found' message."""
        mock_context.args = ["ZZXX"]

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)

        mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=False)

        await duediligence_handler(mock_update, mock_context)
        call_args = mock_update.message.reply_text.call_args
        assert "not found" in call_args[0][0]

    @pytest.mark.asyncio
    @patch("src.bot.handlers.duediligence.is_authorized", return_value=True)
    @patch("src.bot.handlers.duediligence.async_session_factory")
    async def test_no_dd_data_returns_weekly_refresh_message(
        self, mock_session_factory: MagicMock, mock_auth: MagicMock,
        mock_update: MagicMock, mock_context: MagicMock
    ) -> None:
        """Stock with no DD report returns weekly refresh message."""
        mock_context.args = ["BBCA"]

        mock_asset = MagicMock()
        mock_asset.id = 1
        mock_asset.symbol = "BBCA"
        mock_asset.asset_type = "stock"
        mock_asset.name = "Bank Central Asia"

        mock_session = AsyncMock()
        # First call: asset lookup returns asset
        # Second call (prefix fallback): skipped because first succeeds
        # Third call: DD report returns None
        call_count = 0

        async def side_effect_execute(stmt):
            nonlocal call_count
            call_count += 1
            result = MagicMock()
            if call_count == 1:
                # Asset lookup
                result.scalar_one_or_none.return_value = mock_asset
            elif call_count == 2:
                # DD report lookup
                result.scalar_one_or_none.return_value = None
            return result

        mock_session.execute = AsyncMock(side_effect=side_effect_execute)

        mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=False)

        await duediligence_handler(mock_update, mock_context)
        call_args = mock_update.message.reply_text.call_args
        assert "No due diligence data" in call_args[0][0]
        assert "weekly" in call_args[0][0].lower()

    @pytest.mark.asyncio
    @patch("src.bot.handlers.duediligence.is_authorized", return_value=True)
    @patch("src.bot.handlers.duediligence.async_session_factory")
    @patch("src.bot.handlers.duediligence.format_dd_report")
    async def test_valid_stock_returns_formatted_dd_report(
        self, mock_format: MagicMock, mock_session_factory: MagicMock,
        mock_auth: MagicMock, mock_update: MagicMock, mock_context: MagicMock
    ) -> None:
        """Valid IDX stock with DD data returns formatted report."""
        mock_context.args = ["BBCA"]
        mock_format.return_value = "<b>Due Diligence: BBCA</b>\nTest report"

        mock_asset = MagicMock()
        mock_asset.id = 1
        mock_asset.symbol = "BBCA"
        mock_asset.asset_type = "stock"
        mock_asset.name = "Bank Central Asia"

        mock_dd = MagicMock()
        mock_dd.sector = "banking"
        mock_dd.sector_rank = {"pe": {"value": 15.2, "median": 18.0}}
        mock_dd.management_quality = {"score": 0.72, "label": "Good"}
        mock_dd.ownership_changes = {}
        mock_dd.competitive_position = {"market_position": "leader"}

        mock_ownership = MagicMock()
        mock_ownership.shareholders = [{"name": "Hartono Family", "pct": 47.1}]
        mock_ownership.public_float_pct = 52.9

        mock_session = AsyncMock()
        call_count = 0

        async def side_effect_execute(stmt):
            nonlocal call_count
            call_count += 1
            result = MagicMock()
            if call_count == 1:
                # Asset lookup
                result.scalar_one_or_none.return_value = mock_asset
            elif call_count == 2:
                # DD report lookup
                result.scalar_one_or_none.return_value = mock_dd
            elif call_count == 3:
                # Ownership lookup
                result.scalar_one_or_none.return_value = mock_ownership
            return result

        mock_session.execute = AsyncMock(side_effect=side_effect_execute)

        mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=False)

        await duediligence_handler(mock_update, mock_context)

        mock_format.assert_called_once()
        call_args = mock_update.message.reply_text.call_args
        assert "Due Diligence: BBCA" in call_args[0][0]
        assert call_args[1]["parse_mode"] == "HTML"
