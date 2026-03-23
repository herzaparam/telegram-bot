"""Crypto fetcher using ccxt/Binance with CoinGecko fallback.

Primary path uses ccxt async for Binance OHLCV data.
Falls back to CoinGecko free API if ccxt fails.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, time
from typing import Any

import ccxt
import httpx
import structlog
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from src.data.base import BaseFetcher, OHLCVRow
from src.data.validation import validate_rows

logger = structlog.get_logger(__name__)

# Mapping of ccxt symbols to CoinGecko IDs
COINGECKO_ID_MAP: dict[str, str] = {
    "BTC/USDT": "bitcoin",
    "ETH/USDT": "ethereum",
    "SOL/USDT": "solana",
}

COINGECKO_BASE_URL = "https://api.coingecko.com/api/v3"


class CryptoFetcher(BaseFetcher):
    """Fetches crypto OHLCV via ccxt/Binance with CoinGecko fallback."""

    def __init__(self) -> None:
        self._log = logger.bind(component="crypto_fetcher")

    @property
    def source_name(self) -> str:
        return "ccxt"

    async def fetch(
        self, asset_id: int, symbol: str, start: date, end: date
    ) -> list[OHLCVRow]:
        """Fetch daily OHLCV data, trying ccxt first then CoinGecko.

        Args:
            asset_id: Database ID of the asset.
            symbol: ccxt-compatible symbol (e.g. 'BTC/USDT').
            start: Start date (inclusive).
            end: End date (inclusive).

        Returns:
            List of validated OHLCVRow instances.
        """
        exchange = ccxt.binance({"enableRateLimit": True})
        try:
            rows = await self._fetch_ccxt(exchange, asset_id, symbol, start, end, "1d")
            result = validate_rows(rows, asset_symbol=symbol)
            return result.valid
        except Exception as exc:
            self._log.warning(
                "ccxt_failed_falling_back",
                symbol=symbol,
                error=str(exc),
            )
            # Always close exchange before fallback
            await exchange.close()
            exchange = None
            return await self._fetch_coingecko(asset_id, symbol, start, end)
        finally:
            if exchange is not None:
                await exchange.close()

    async def fetch_hourly(
        self, asset_id: int, symbol: str, start: date, end: date
    ) -> list[OHLCVRow]:
        """Fetch hourly OHLCV data from ccxt only (no CoinGecko fallback for hourly).

        Args:
            asset_id: Database ID of the asset.
            symbol: ccxt-compatible symbol (e.g. 'BTC/USDT').
            start: Start date (inclusive).
            end: End date (inclusive).

        Returns:
            List of validated OHLCVRow instances with source='ccxt'.
        """
        exchange = ccxt.binance({"enableRateLimit": True})
        try:
            rows = await self._fetch_ccxt(exchange, asset_id, symbol, start, end, "1h")
            result = validate_rows(rows, asset_symbol=symbol)
            return result.valid
        finally:
            await exchange.close()

    async def _fetch_ccxt(
        self,
        exchange: Any,
        asset_id: int,
        symbol: str,
        start: date,
        end: date,
        timeframe: str,
    ) -> list[OHLCVRow]:
        """Fetch OHLCV from ccxt with pagination and retry."""
        start_ms = int(
            datetime.combine(start, time.min, tzinfo=UTC).timestamp() * 1000
        )
        end_ms = int(
            datetime.combine(end, time.max, tzinfo=UTC).timestamp() * 1000
        )

        all_candles: list[list[float]] = []
        since = start_ms

        while since <= end_ms:
            candles = await self._fetch_ccxt_page(exchange, symbol, timeframe, since)
            if not candles:
                break
            all_candles.extend(candles)
            # Advance past the last candle
            since = int(candles[-1][0]) + 1

        rows: list[OHLCVRow] = []
        for candle in all_candles:
            ts_ms, o, h, l, c, v = candle  # noqa: E741
            dt = datetime.fromtimestamp(ts_ms / 1000, tz=UTC)
            if dt.timestamp() * 1000 > end_ms:
                break
            rows.append(
                OHLCVRow(
                    time=dt,
                    asset_id=asset_id,
                    open=float(o),
                    high=float(h),
                    low=float(l),
                    close=float(c),
                    volume=float(v),
                    source="ccxt",
                )
            )

        self._log.info(
            "ccxt_fetch_complete",
            symbol=symbol,
            timeframe=timeframe,
            rows=len(rows),
        )
        return rows

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        retry=retry_if_exception_type(
            (ccxt.NetworkError, ccxt.ExchangeNotAvailable, TimeoutError)
        ),
        reraise=True,
    )
    async def _fetch_ccxt_page(
        self, exchange: Any, symbol: str, timeframe: str, since: int
    ) -> list[list[float]]:
        """Fetch a single page of OHLCV candles with retry."""
        result: list[list[float]] = await exchange.fetch_ohlcv(symbol, timeframe, since=since, limit=1000)
        return result

    async def _fetch_coingecko(
        self, asset_id: int, symbol: str, start: date, end: date
    ) -> list[OHLCVRow]:
        """Fallback: fetch OHLC from CoinGecko free API.

        Uses /coins/{id}/ohlc endpoint which returns [ts, open, high, low, close].
        Volume is set to 0 since CoinGecko OHLC endpoint does not provide it.
        """
        coin_id = COINGECKO_ID_MAP.get(symbol)
        if coin_id is None:
            raise ValueError(f"No CoinGecko mapping for symbol: {symbol}")

        days = (end - start).days + 1

        self._log.info(
            "coingecko_fallback",
            symbol=symbol,
            coin_id=coin_id,
            days=days,
        )

        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{COINGECKO_BASE_URL}/coins/{coin_id}/ohlc",
                params={"vs_currency": "usd", "days": str(days)},
                timeout=30.0,
            )
            resp.raise_for_status()
            data = resp.json()

        rows: list[OHLCVRow] = []
        for candle in data:
            ts_ms, o, h, l, c = candle  # noqa: E741
            dt = datetime.fromtimestamp(ts_ms / 1000, tz=UTC)
            rows.append(
                OHLCVRow(
                    time=dt,
                    asset_id=asset_id,
                    open=float(o),
                    high=float(h),
                    low=float(l),
                    close=float(c),
                    volume=0.0,  # CoinGecko OHLC has no volume
                    source="coingecko",
                )
            )

        result = validate_rows(rows, asset_symbol=symbol)
        self._log.info(
            "coingecko_fetch_complete",
            symbol=symbol,
            rows=len(result.valid),
        )
        return result.valid
