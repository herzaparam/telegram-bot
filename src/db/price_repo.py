"""Asyncpg raw SQL repository for OHLCV price data.

Uses raw asyncpg for hot-path performance (10-50x faster than ORM for bulk inserts).
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import asyncpg

from src.data.base import OHLCVRow


async def upsert_prices(
    conn: asyncpg.Connection,
    rows: list[OHLCVRow],
    table: str = "price_history",
) -> int:
    """Bulk upsert OHLCV rows into a price table.

    Uses INSERT ... ON CONFLICT (asset_id, time) DO UPDATE for idempotency.

    Args:
        conn: An asyncpg connection (not a SQLAlchemy session).
        rows: Validated OHLCVRow instances to insert.
        table: Target table name (default: price_history).

    Returns:
        Number of rows processed.
    """
    if not rows:
        return 0

    sql = f"""
        INSERT INTO {table} (time, asset_id, open, high, low, close, volume, source)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
        ON CONFLICT (asset_id, time)
        DO UPDATE SET open = EXCLUDED.open, high = EXCLUDED.high,
                      low = EXCLUDED.low, close = EXCLUDED.close,
                      volume = EXCLUDED.volume, source = EXCLUDED.source
    """

    args = [
        (r.time, r.asset_id, r.open, r.high, r.low, r.close, r.volume, r.source)
        for r in rows
    ]
    await conn.executemany(sql, args)
    return len(rows)


async def get_latest_date(
    conn: asyncpg.Connection,
    asset_id: int,
    table: str = "price_history",
) -> datetime | None:
    """Get the most recent timestamp for an asset in a price table.

    Args:
        conn: An asyncpg connection.
        asset_id: Database ID of the asset.
        table: Target table name (default: price_history).

    Returns:
        The most recent datetime, or None if no data exists.
    """
    sql = f"SELECT MAX(time) FROM {table} WHERE asset_id = $1"
    return await conn.fetchval(sql, asset_id)
