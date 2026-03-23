"""Tests for price_repo asyncpg upsert and query functions.

Uses a mock asyncpg connection since we cannot run asyncpg against SQLite.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest

from src.data.base import OHLCVRow
from src.db.price_repo import get_latest_date, upsert_prices


@pytest.fixture()
def mock_conn() -> AsyncMock:
    """Mock asyncpg connection that records calls."""
    conn = AsyncMock()
    conn.executemany = AsyncMock(return_value=None)
    conn.fetchval = AsyncMock(return_value=None)
    return conn


class TestUpsertPrices:
    """Tests for upsert_prices function."""

    async def test_inserts_three_rows(
        self, mock_conn: AsyncMock, sample_ohlcv_rows: list[OHLCVRow]
    ) -> None:
        result = await upsert_prices(mock_conn, sample_ohlcv_rows)
        assert result == 3
        mock_conn.executemany.assert_called_once()

    async def test_empty_list_returns_zero(self, mock_conn: AsyncMock) -> None:
        result = await upsert_prices(mock_conn, [])
        assert result == 0
        mock_conn.executemany.assert_not_called()

    async def test_idempotent_same_rows(
        self, mock_conn: AsyncMock, sample_ohlcv_rows: list[OHLCVRow]
    ) -> None:
        """Calling upsert twice with same data returns same count each time."""
        first = await upsert_prices(mock_conn, sample_ohlcv_rows)
        second = await upsert_prices(mock_conn, sample_ohlcv_rows)
        assert first == second == 3

    async def test_upsert_updates_on_conflict(
        self, mock_conn: AsyncMock, sample_ohlcv_rows: list[OHLCVRow]
    ) -> None:
        """Verify the SQL contains ON CONFLICT DO UPDATE."""
        await upsert_prices(mock_conn, sample_ohlcv_rows)
        call_args = mock_conn.executemany.call_args
        sql = call_args[0][0]
        assert "ON CONFLICT" in sql
        assert "DO UPDATE SET" in sql

    async def test_uses_custom_table(
        self, mock_conn: AsyncMock, sample_ohlcv_rows: list[OHLCVRow]
    ) -> None:
        await upsert_prices(mock_conn, sample_ohlcv_rows, table="price_history_hourly")
        call_args = mock_conn.executemany.call_args
        sql = call_args[0][0]
        assert "price_history_hourly" in sql


class TestGetLatestDate:
    """Tests for get_latest_date function."""

    async def test_returns_none_for_no_data(self, mock_conn: AsyncMock) -> None:
        mock_conn.fetchval.return_value = None
        result = await get_latest_date(mock_conn, asset_id=1)
        assert result is None

    async def test_returns_datetime_when_data_exists(
        self, mock_conn: AsyncMock
    ) -> None:
        expected = datetime(2026, 3, 22, 0, 0, tzinfo=timezone.utc)
        mock_conn.fetchval.return_value = expected
        result = await get_latest_date(mock_conn, asset_id=1)
        assert result == expected

    async def test_uses_custom_table(self, mock_conn: AsyncMock) -> None:
        await get_latest_date(mock_conn, asset_id=1, table="price_history_hourly")
        call_args = mock_conn.fetchval.call_args
        sql = call_args[0][0]
        assert "price_history_hourly" in sql
