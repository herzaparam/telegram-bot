"""Tests for /portfolio command handler (TBOT-12)."""

from __future__ import annotations

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.bot.handlers.portfolio import portfolio_handler


class TestPortfolioHandler:
    """Tests for portfolio_handler."""

    @pytest.mark.asyncio
    @patch("src.bot.handlers.portfolio.is_authorized", return_value=False)
    async def test_unauthorized_no_response(
        self, mock_auth: MagicMock, mock_update: MagicMock, mock_context: MagicMock
    ) -> None:
        """Unauthorized user gets no response."""
        await portfolio_handler(mock_update, mock_context)
        mock_update.message.reply_text.assert_not_called()

    @pytest.mark.asyncio
    @patch("src.bot.handlers.portfolio.is_authorized", return_value=True)
    @patch("src.bot.handlers.portfolio.async_session_factory")
    async def test_empty_watchlist_returns_info(
        self, mock_session_factory: MagicMock, mock_auth: MagicMock,
        mock_update: MagicMock, mock_context: MagicMock
    ) -> None:
        """Empty watchlist returns informational message."""
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute = AsyncMock(return_value=mock_result)

        mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=False)

        await portfolio_handler(mock_update, mock_context)

        call_args = mock_update.message.reply_text.call_args
        assert "empty" in call_args[0][0].lower() or "watchlist" in call_args[0][0].lower()

    @pytest.mark.asyncio
    @patch("src.bot.handlers.portfolio.is_authorized", return_value=True)
    @patch("src.bot.handlers.portfolio.async_session_factory")
    async def test_with_assets_returns_risk_analysis(
        self, mock_session_factory: MagicMock, mock_auth: MagicMock,
        mock_update: MagicMock, mock_context: MagicMock
    ) -> None:
        """Portfolio with assets returns multi-section risk analysis."""
        # Create mock assets
        asset1 = MagicMock()
        asset1.id = 1
        asset1.symbol = "BBCA"
        asset1.name = "Bank Central Asia"
        asset1.asset_type = "stock"

        asset2 = MagicMock()
        asset2.id = 2
        asset2.symbol = "BTC/USDT"
        asset2.name = "Bitcoin"
        asset2.asset_type = "crypto"

        # Create mock price history rows
        now = datetime.now()
        price_rows = []
        for i in range(100):
            for asset in [asset1, asset2]:
                row = MagicMock()
                row.asset_id = asset.id
                row.time = now - timedelta(days=100 - i)
                row.close = 10000 + i * 10 if asset.id == 1 else 50000 + i * 100
                price_rows.append(row)

        # First call returns assets, second returns prices
        mock_session = AsyncMock()
        call_count = 0

        async def mock_execute(stmt):
            nonlocal call_count
            call_count += 1
            result = MagicMock()
            if call_count == 1:
                # Assets query
                result.scalars.return_value.all.return_value = [asset1, asset2]
            else:
                # Price history query
                result.scalars.return_value.all.return_value = price_rows
            return result

        mock_session.execute = mock_execute

        mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=False)

        await portfolio_handler(mock_update, mock_context)

        # Should have called reply_text at least once
        assert mock_update.message.reply_text.call_count >= 1
        call_args = mock_update.message.reply_text.call_args
        msg = call_args[0][0]
        assert "Portfolio Risk Analysis" in msg
        assert call_args[1]["parse_mode"] == "HTML"

    @pytest.mark.asyncio
    @patch("src.bot.handlers.portfolio.is_authorized", return_value=True)
    @patch("src.bot.handlers.portfolio.async_session_factory")
    async def test_db_error_returns_error_message(
        self, mock_session_factory: MagicMock, mock_auth: MagicMock,
        mock_update: MagicMock, mock_context: MagicMock
    ) -> None:
        """DB error returns error message."""
        mock_session_factory.return_value.__aenter__ = AsyncMock(
            side_effect=RuntimeError("DB connection failed")
        )
        mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=False)

        await portfolio_handler(mock_update, mock_context)

        call_args = mock_update.message.reply_text.call_args
        assert "unavailable" in call_args[0][0].lower() or "error" in call_args[0][0].lower()
