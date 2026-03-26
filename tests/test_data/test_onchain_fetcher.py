"""Tests for on-chain data fetcher (DeFiLlama TVL wrapper)."""

from __future__ import annotations

import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestFetchTvlHistory:
    """Tests for fetch_tvl_history() function."""

    @pytest.mark.asyncio
    async def test_fetch_tvl_history_btc_returns_data(self) -> None:
        """fetch_tvl_history('BTC') calls DeFiLlama for Bitcoin chain TVL."""
        now = int(time.time())
        mock_data = [
            {"date": now - 86400 * 30, "tvl": 1_000_000_000.0},
            {"date": now - 86400 * 7, "tvl": 1_100_000_000.0},
            {"date": now, "tvl": 1_200_000_000.0},
        ]

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_data
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("src.data.onchain_fetcher.httpx.AsyncClient", return_value=mock_client):
            from src.data.onchain_fetcher import fetch_tvl_history

            result = await fetch_tvl_history("BTC", days=30)

        assert len(result) == 3
        assert result[0]["tvl"] == 1_000_000_000.0
        mock_client.get.assert_called_once()
        call_url = mock_client.get.call_args[0][0]
        assert "Bitcoin" in call_url

    @pytest.mark.asyncio
    async def test_fetch_tvl_history_unknown_symbol_returns_empty(self) -> None:
        """fetch_tvl_history('BBCA') returns [] for non-crypto symbol."""
        from src.data.onchain_fetcher import fetch_tvl_history

        result = await fetch_tvl_history("BBCA")
        assert result == []

    @pytest.mark.asyncio
    async def test_fetch_tvl_history_eth_maps_to_ethereum(self) -> None:
        """fetch_tvl_history('ETH') maps to Ethereum chain."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [{"date": int(time.time()), "tvl": 50_000_000_000.0}]
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("src.data.onchain_fetcher.httpx.AsyncClient", return_value=mock_client):
            from src.data.onchain_fetcher import fetch_tvl_history

            await fetch_tvl_history("ETH")

        call_url = mock_client.get.call_args[0][0]
        assert "Ethereum" in call_url


class TestFetchOnchainData:
    """Tests for fetch_onchain_data() function."""

    @pytest.mark.asyncio
    async def test_fetch_onchain_data_btc_returns_tvl_metrics(self) -> None:
        """fetch_onchain_data('BTC') returns dict with TVL metrics."""
        now = int(time.time())
        mock_history = [
            {"date": now - 86400 * 30, "tvl": 1_000_000_000.0},
            {"date": now - 86400 * 7, "tvl": 1_100_000_000.0},
            {"date": now, "tvl": 1_200_000_000.0},
        ]

        mock_session = AsyncMock()
        mock_session.execute.return_value = MagicMock()

        with patch("src.data.onchain_fetcher.fetch_tvl_history", return_value=mock_history):
            from src.data.onchain_fetcher import fetch_onchain_data

            result = await fetch_onchain_data("BTC", asset_id=1, session=mock_session)

        assert isinstance(result, dict)
        assert "tvl_current" in result
        assert "tvl_7d_change" in result
        assert "tvl_30d_change" in result
        assert result["source"] == "defillama"

    @pytest.mark.asyncio
    async def test_fetch_onchain_data_stock_returns_empty(self) -> None:
        """fetch_onchain_data('BBCA') returns empty dict for stock symbol."""
        mock_session = AsyncMock()

        with patch("src.data.onchain_fetcher.fetch_tvl_history", return_value=[]):
            from src.data.onchain_fetcher import fetch_onchain_data

            result = await fetch_onchain_data("BBCA", asset_id=1, session=mock_session)

        assert result == {}

    @pytest.mark.asyncio
    async def test_fetch_onchain_data_handles_exception_gracefully(self) -> None:
        """fetch_onchain_data returns empty dict on exception."""
        mock_session = AsyncMock()

        with patch("src.data.onchain_fetcher.fetch_tvl_history", side_effect=Exception("API down")):
            from src.data.onchain_fetcher import fetch_onchain_data

            result = await fetch_onchain_data("BTC", asset_id=1, session=mock_session)

        assert result == {}
