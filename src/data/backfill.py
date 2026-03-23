"""CLI entry point for historical OHLCV data backfill.

Supports --from and --to date range flags. Defaults to 2 years of history.
Uses asyncio.Semaphore(5) for concurrent fetching.

Usage:
    python -m src.data.backfill --from 2024-01-01 --to 2026-03-23
"""

from __future__ import annotations

import argparse
import asyncio
from datetime import date, timedelta

import asyncpg
import structlog

from src.config import settings
from src.data.crypto import CryptoFetcher
from src.data.idx_stocks import IDXStockFetcher
from src.data.validation import validate_rows
from src.db.price_repo import upsert_prices

logger = structlog.get_logger(__name__)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse CLI arguments for the backfill command.

    Args:
        argv: Argument list (defaults to sys.argv[1:]).

    Returns:
        Parsed namespace with from_date, to_date, assets, type.
    """
    parser = argparse.ArgumentParser(
        description="Backfill historical OHLCV price data."
    )
    today = date.today()
    default_from = today - timedelta(days=730)

    parser.add_argument(
        "--from",
        dest="from_date",
        type=date.fromisoformat,
        default=default_from,
        help="Start date in YYYY-MM-DD format (default: 2 years ago)",
    )
    parser.add_argument(
        "--to",
        dest="to_date",
        type=date.fromisoformat,
        default=today,
        help="End date in YYYY-MM-DD format (default: today)",
    )
    parser.add_argument(
        "--assets",
        type=str,
        default=None,
        help="Comma-separated asset symbols (default: all active)",
    )
    parser.add_argument(
        "--type",
        dest="asset_type",
        choices=["stock", "crypto", "all"],
        default="all",
        help="Asset type to backfill (default: all)",
    )

    return parser.parse_args(argv)


async def _fetch_and_upsert(
    conn: asyncpg.Connection,  # type: ignore[type-arg]
    sem: asyncio.Semaphore,
    asset_id: int,
    symbol: str,
    asset_type: str,
    start: date,
    end: date,
) -> int:
    """Fetch and upsert data for a single asset with semaphore rate limiting."""
    async with sem:
        log = logger.bind(asset=symbol, type=asset_type)
        try:
            if asset_type == "stock":
                fetcher = IDXStockFetcher()
                rows = await fetcher.fetch(asset_id, symbol, start, end)
            else:
                fetcher = CryptoFetcher()
                rows = await fetcher.fetch(asset_id, symbol, start, end)

            validation = validate_rows(rows, asset_symbol=symbol)
            upserted = await upsert_prices(conn, validation.valid)

            # For crypto: also fetch hourly (last 7 days only)
            if asset_type == "crypto":
                hourly_start = max(start, end - timedelta(days=7))
                hourly_rows = await fetcher.fetch_hourly(asset_id, symbol, hourly_start, end)
                hourly_validation = validate_rows(hourly_rows, asset_symbol=symbol)
                await upsert_prices(conn, hourly_validation.valid, table="price_history_hourly")

            log.info("backfill_asset_complete", rows=upserted)
            return upserted
        except Exception as exc:
            log.error("backfill_asset_failed", error=str(exc))
            return 0


async def run_backfill(
    start: date,
    end: date,
    asset_type: str | None = None,
    asset_symbols: list[str] | None = None,
) -> None:
    """Run the backfill process for the specified date range.

    Args:
        start: Start date (inclusive).
        end: End date (inclusive).
        asset_type: Filter by 'stock', 'crypto', or None for all.
        asset_symbols: Filter by specific symbols, or None for all active.
    """
    raw_url = settings.database_url.replace("postgresql+asyncpg://", "postgresql://")
    conn = await asyncpg.connect(raw_url)

    try:
        # Query active assets
        query = "SELECT id, symbol, asset_type, yfinance_symbol, ccxt_symbol FROM assets WHERE is_active = true"
        conditions: list[str] = []
        args: list[object] = []

        if asset_type and asset_type != "all":
            conditions.append(f"asset_type = ${len(args) + 1}")
            args.append(asset_type)

        if asset_symbols:
            conditions.append(f"symbol = ANY(${len(args) + 1})")
            args.append(asset_symbols)

        if conditions:
            query += " AND " + " AND ".join(conditions)

        rows = await conn.fetch(query, *args)
        if not rows:
            logger.warning("no_assets_found")
            return

        sem = asyncio.Semaphore(5)
        tasks = []
        for row in rows:
            a_type = row["asset_type"]
            symbol = row["yfinance_symbol"] if a_type == "stock" else row["ccxt_symbol"]
            if symbol is None:
                symbol = row["symbol"]

            tasks.append(
                _fetch_and_upsert(
                    conn, sem, row["id"], symbol, a_type, start, end
                )
            )

        results = await asyncio.gather(*tasks, return_exceptions=True)
        total_rows = sum(r for r in results if isinstance(r, int))
        failures = sum(1 for r in results if isinstance(r, Exception))

        logger.info(
            "backfill_complete",
            assets=len(rows),
            total_rows=total_rows,
            failures=failures,
        )

    finally:
        await conn.close()


def main() -> None:
    """CLI entry point for backfill."""
    args = parse_args()
    asset_list = args.assets.split(",") if args.assets else None
    a_type = args.asset_type if args.asset_type != "all" else None

    logger.info(
        "starting_backfill",
        from_date=str(args.from_date),
        to_date=str(args.to_date),
        type=args.asset_type,
    )

    asyncio.run(run_backfill(args.from_date, args.to_date, a_type, asset_list))
