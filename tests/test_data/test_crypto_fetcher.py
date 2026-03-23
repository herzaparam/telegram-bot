"""Tests for crypto fetcher (ccxt/Binance with CoinGecko fallback)."""

from __future__ import annotations

from datetime import date, datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from tenacity import wait_none

from src.data.base import OHLCVRow
from src.data.crypto import CryptoFetcher


class TestCryptoFetcher:
    """CryptoFetcher unit tests with mocked ccxt and httpx."""

    def setup_method(self) -> None:
        self.fetcher = CryptoFetcher()

    def test_source_name(self) -> None:
        assert self.fetcher.source_name == "ccxt"

    @pytest.mark.asyncio
    async def test_fetch_returns_ohlcv_rows_ccxt(self, mock_ccxt_ohlcv: list[list[float]]) -> None:
        """fetch() returns list of OHLCVRow with source='ccxt'."""
        mock_exchange = AsyncMock()
        mock_exchange.fetch_ohlcv = AsyncMock(side_effect=[mock_ccxt_ohlcv, []])
        mock_exchange.close = AsyncMock()

        with patch("src.data.crypto.ccxt.binance", return_value=mock_exchange):
            rows = await self.fetcher.fetch(
                asset_id=10,
                symbol="BTC/USDT",
                start=date(2026, 3, 16),
                end=date(2026, 3, 20),
            )

        assert len(rows) == 5
        assert all(isinstance(r, OHLCVRow) for r in rows)
        assert all(r.source == "ccxt" for r in rows)
        assert all(r.asset_id == 10 for r in rows)
        mock_exchange.close.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_fetch_falls_back_to_coingecko(
        self, mock_coingecko_ohlc_response: list[list[float]]
    ) -> None:
        """fetch() falls back to CoinGecko on ccxt exception, rows have source='coingecko'."""
        mock_exchange = AsyncMock()
        mock_exchange.fetch_ohlcv = AsyncMock(side_effect=Exception("ccxt failure"))
        mock_exchange.close = AsyncMock()

        mock_response = MagicMock()
        mock_response.json.return_value = mock_coingecko_ohlc_response
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(return_value=mock_response)

        with (
            patch("src.data.crypto.ccxt.binance", return_value=mock_exchange),
            patch("src.data.crypto.httpx.AsyncClient", return_value=mock_client),
        ):
            rows = await self.fetcher.fetch(
                asset_id=10,
                symbol="BTC/USDT",
                start=date(2026, 3, 16),
                end=date(2026, 3, 20),
            )

        assert len(rows) == 5
        assert all(r.source == "coingecko" for r in rows)
        mock_exchange.close.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_exchange_closed_on_error(self) -> None:
        """exchange.close() is always called even on ccxt error (and no CoinGecko fallback)."""
        mock_exchange = AsyncMock()
        mock_exchange.fetch_ohlcv = AsyncMock(side_effect=Exception("ccxt failure"))
        mock_exchange.close = AsyncMock()

        # CoinGecko also fails
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(side_effect=Exception("coingecko failure"))

        with (
            patch("src.data.crypto.ccxt.binance", return_value=mock_exchange),
            patch("src.data.crypto.httpx.AsyncClient", return_value=mock_client),
        ):
            with pytest.raises(Exception, match="coingecko failure"):
                await self.fetcher.fetch(
                    asset_id=10,
                    symbol="BTC/USDT",
                    start=date(2026, 3, 16),
                    end=date(2026, 3, 20),
                )

        mock_exchange.close.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_fetch_hourly_returns_hourly_candles(self, mock_ccxt_ohlcv: list[list[float]]) -> None:
        """fetch_hourly() returns hourly candles with source='ccxt'."""
        mock_exchange = AsyncMock()
        mock_exchange.fetch_ohlcv = AsyncMock(side_effect=[mock_ccxt_ohlcv, []])
        mock_exchange.close = AsyncMock()

        with patch("src.data.crypto.ccxt.binance", return_value=mock_exchange):
            rows = await self.fetcher.fetch_hourly(
                asset_id=10,
                symbol="BTC/USDT",
                start=date(2026, 3, 16),
                end=date(2026, 3, 20),
            )

        assert len(rows) == 5
        assert all(r.source == "ccxt" for r in rows)
        # Verify it was called with 1h timeframe
        call_args = mock_exchange.fetch_ohlcv.call_args_list[0]
        assert call_args[0][1] == "1h"

    @pytest.mark.asyncio
    async def test_fetch_retries_on_network_error(self, mock_ccxt_ohlcv: list[list[float]]) -> None:
        """fetch() retries 3x on ccxt NetworkError."""
        import ccxt as ccxt_mod

        call_count = 0

        async def flaky_fetch(*args: object, **kwargs: object) -> list[list[float]]:
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ccxt_mod.NetworkError("timeout")
            # Return data on 3rd call, then empty to stop pagination
            if call_count == 3:
                return mock_ccxt_ohlcv
            return []

        mock_exchange = AsyncMock()
        mock_exchange.fetch_ohlcv = AsyncMock(side_effect=flaky_fetch)
        mock_exchange.close = AsyncMock()

        # Patch tenacity wait to avoid real delays in tests
        original_wait = self.fetcher._fetch_ccxt_page.retry.wait
        self.fetcher._fetch_ccxt_page.retry.wait = wait_none()
        try:
            with patch("src.data.crypto.ccxt.binance", return_value=mock_exchange):
                rows = await self.fetcher.fetch(
                    asset_id=10,
                    symbol="BTC/USDT",
                    start=date(2026, 3, 16),
                    end=date(2026, 3, 20),
                )
        finally:
            self.fetcher._fetch_ccxt_page.retry.wait = original_wait

        # Should have retried and eventually returned data
        assert call_count >= 3
        assert len(rows) == 5
