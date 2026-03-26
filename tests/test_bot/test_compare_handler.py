"""Tests for /compare command handler (TBOT-10)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.bot.handlers.compare import compare_handler


class TestCompareHandler:
    """Tests for compare_handler."""

    @pytest.mark.asyncio
    @patch("src.bot.handlers.compare.is_authorized", return_value=False)
    async def test_unauthorized_no_response(
        self, mock_auth: MagicMock, mock_update: MagicMock, mock_context: MagicMock
    ) -> None:
        """Unauthorized user gets no response."""
        await compare_handler(mock_update, mock_context)
        mock_update.message.reply_text.assert_not_called()

    @pytest.mark.asyncio
    @patch("src.bot.handlers.compare.is_authorized", return_value=True)
    async def test_too_few_symbols_returns_error(
        self, mock_auth: MagicMock, mock_update: MagicMock, mock_context: MagicMock
    ) -> None:
        """Less than 2 symbols returns error message."""
        mock_context.args = ["BBCA"]
        await compare_handler(mock_update, mock_context)
        call_args = mock_update.message.reply_text.call_args
        assert "2-5 IDX stock symbols" in call_args[0][0]

    @pytest.mark.asyncio
    @patch("src.bot.handlers.compare.is_authorized", return_value=True)
    async def test_no_args_returns_error(
        self, mock_auth: MagicMock, mock_update: MagicMock, mock_context: MagicMock
    ) -> None:
        """No args returns error message."""
        mock_context.args = []
        await compare_handler(mock_update, mock_context)
        call_args = mock_update.message.reply_text.call_args
        assert "2-5 IDX stock symbols" in call_args[0][0]

    @pytest.mark.asyncio
    @patch("src.bot.handlers.compare.is_authorized", return_value=True)
    async def test_too_many_symbols_returns_error(
        self, mock_auth: MagicMock, mock_update: MagicMock, mock_context: MagicMock
    ) -> None:
        """More than 5 symbols returns max symbols error."""
        mock_context.args = ["BBCA", "BBRI", "BMRI", "BBNI", "BRIS", "MEGA"]
        await compare_handler(mock_update, mock_context)
        call_args = mock_update.message.reply_text.call_args
        assert "Maximum 5" in call_args[0][0]

    @pytest.mark.asyncio
    @patch("src.bot.handlers.compare.is_authorized", return_value=True)
    @patch("src.bot.handlers.compare.async_session_factory")
    async def test_mixed_stock_crypto_warns_and_filters(
        self, mock_session_factory: MagicMock, mock_auth: MagicMock,
        mock_update: MagicMock, mock_context: MagicMock
    ) -> None:
        """Mixed stock+crypto returns warning about skipping crypto."""
        mock_context.args = ["BBCA", "BTC", "BBRI"]

        mock_stock1 = MagicMock()
        mock_stock1.id = 1
        mock_stock1.symbol = "BBCA"
        mock_stock1.asset_type = "stock"
        mock_stock1.name = "Bank Central Asia"

        mock_crypto = MagicMock()
        mock_crypto.id = 2
        mock_crypto.symbol = "BTC"
        mock_crypto.asset_type = "crypto"
        mock_crypto.name = "Bitcoin"

        mock_stock2 = MagicMock()
        mock_stock2.id = 3
        mock_stock2.symbol = "BBRI"
        mock_stock2.asset_type = "stock"
        mock_stock2.name = "Bank Rakyat Indonesia"

        mock_fund1 = MagicMock()
        mock_fund1.trailing_pe = 22.5
        mock_fund1.price_to_book = 4.8
        mock_fund1.return_on_equity = 20.1
        mock_fund1.debt_to_equity = 5.5
        mock_fund1.revenue_growth = 8.2

        mock_fund2 = MagicMock()
        mock_fund2.trailing_pe = 12.3
        mock_fund2.price_to_book = 2.1
        mock_fund2.return_on_equity = 18.5
        mock_fund2.debt_to_equity = 6.2
        mock_fund2.revenue_growth = 5.1

        mock_session = AsyncMock()
        call_count = 0
        assets = [mock_stock1, mock_crypto, mock_stock2]
        fundamentals = [mock_fund1, None, mock_fund2]  # No fundamental for crypto

        async def side_effect_execute(stmt):
            nonlocal call_count
            call_count += 1
            result = MagicMock()
            # Calls: asset1, asset2, asset3, fund1, fund2
            if call_count <= 3:
                result.scalar_one_or_none.return_value = assets[call_count - 1]
            elif call_count == 4:
                result.scalar_one_or_none.return_value = mock_fund1
            elif call_count == 5:
                result.scalar_one_or_none.return_value = mock_fund2
            return result

        mock_session.execute = AsyncMock(side_effect=side_effect_execute)

        mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=False)

        await compare_handler(mock_update, mock_context)

        call_args = mock_update.message.reply_text.call_args
        msg = call_args[0][0]
        assert "Skipping crypto" in msg
        assert "BTC" in msg
        assert "Sector Comparison" in msg

    @pytest.mark.asyncio
    @patch("src.bot.handlers.compare.is_authorized", return_value=True)
    @patch("src.bot.handlers.compare.async_session_factory")
    async def test_crypto_only_returns_idx_error(
        self, mock_session_factory: MagicMock, mock_auth: MagicMock,
        mock_update: MagicMock, mock_context: MagicMock
    ) -> None:
        """Only crypto symbols returns IDX-only error."""
        mock_context.args = ["BTC", "ETH"]

        mock_btc = MagicMock()
        mock_btc.id = 1
        mock_btc.symbol = "BTC"
        mock_btc.asset_type = "crypto"

        mock_eth = MagicMock()
        mock_eth.id = 2
        mock_eth.symbol = "ETH"
        mock_eth.asset_type = "crypto"

        mock_session = AsyncMock()
        call_count = 0

        async def side_effect_execute(stmt):
            nonlocal call_count
            call_count += 1
            result = MagicMock()
            if call_count == 1:
                result.scalar_one_or_none.return_value = mock_btc
            elif call_count == 2:
                result.scalar_one_or_none.return_value = mock_eth
            return result

        mock_session.execute = AsyncMock(side_effect=side_effect_execute)

        mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=False)

        await compare_handler(mock_update, mock_context)

        call_args = mock_update.message.reply_text.call_args
        msg = call_args[0][0]
        assert "at least 2" in msg or "2-5" in msg

    @pytest.mark.asyncio
    @patch("src.bot.handlers.compare.is_authorized", return_value=True)
    @patch("src.bot.handlers.compare.async_session_factory")
    @patch("src.bot.handlers.compare.format_compare_table")
    async def test_valid_comparison_returns_formatted_table(
        self, mock_format: MagicMock, mock_session_factory: MagicMock,
        mock_auth: MagicMock, mock_update: MagicMock, mock_context: MagicMock
    ) -> None:
        """Valid 3-stock comparison returns formatted table."""
        mock_context.args = ["BBCA", "BBRI", "BMRI"]
        mock_format.return_value = "<pre>Sector Comparison table</pre>"

        mock_assets = []
        for i, (sym, name) in enumerate([
            ("BBCA", "Bank Central Asia"),
            ("BBRI", "Bank Rakyat Indonesia"),
            ("BMRI", "Bank Mandiri"),
        ]):
            a = MagicMock()
            a.id = i + 1
            a.symbol = sym
            a.asset_type = "stock"
            a.name = name
            mock_assets.append(a)

        mock_funds = []
        for pe, pb, roe in [(22.5, 4.8, 20.1), (12.3, 2.1, 18.5), (15.0, 2.8, 16.2)]:
            f = MagicMock()
            f.trailing_pe = pe
            f.price_to_book = pb
            f.return_on_equity = roe
            f.debt_to_equity = 5.5
            f.revenue_growth = 8.2
            mock_funds.append(f)

        mock_session = AsyncMock()
        call_count = 0

        async def side_effect_execute(stmt):
            nonlocal call_count
            call_count += 1
            result = MagicMock()
            if call_count <= 3:
                result.scalar_one_or_none.return_value = mock_assets[call_count - 1]
            elif call_count <= 6:
                result.scalar_one_or_none.return_value = mock_funds[call_count - 4]
            return result

        mock_session.execute = AsyncMock(side_effect=side_effect_execute)

        mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=False)

        await compare_handler(mock_update, mock_context)

        mock_format.assert_called_once()
        call_args = mock_update.message.reply_text.call_args
        assert "Sector Comparison" in call_args[0][0]
        assert call_args[1]["parse_mode"] == "HTML"
