"""Fundamental data fetcher using yfinance .info for IDX stocks.

Fetches P/E, P/B, ROE, revenue growth, dividend yield, and debt/equity
ratios from yfinance and caches them in the stock_fundamentals table with
a 7-day refresh window.

Crypto assets are skipped -- fundamental ratios are not applicable.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from typing import Any

import structlog
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import Asset, StockFundamental

logger = structlog.get_logger(__name__)

_CACHE_TTL_DAYS = 7


def _fetch_yfinance_info(symbol: str) -> dict[str, Any]:
    """Synchronous yfinance Ticker.info call.

    Extracts fundamental fields and returns them with snake_case keys.
    Catches all exceptions and returns an empty dict on failure.

    Args:
        symbol: yfinance-compatible ticker symbol (e.g. "BBCA.JK").

    Returns:
        Dict with fundamental fields or empty dict if fetch failed.
    """
    try:
        import yfinance as yf

        info = yf.Ticker(symbol).info
        return {
            "trailing_pe": info.get("trailingPE"),
            "forward_pe": info.get("forwardPE"),
            "price_to_book": info.get("priceToBook"),
            "return_on_equity": info.get("returnOnEquity"),
            "revenue_growth": info.get("revenueGrowth"),
            "dividend_yield": info.get("dividendYield"),
            "debt_to_equity": info.get("debtToEquity"),
        }
    except Exception as exc:  # noqa: BLE001
        log = logger.bind(component="fundamental_fetcher")
        log.warning("yfinance_info_failed", symbol=symbol, error=str(exc))
        return {}


async def fetch_fundamentals(session: AsyncSession, asset: Asset) -> None:
    """Fetch and cache fundamental data for a single asset.

    Skips crypto assets. Respects a 7-day cache freshness window -- if an
    existing row was fetched within the last 7 days the function returns
    immediately without hitting yfinance.

    On yfinance failure the function logs a warning and returns gracefully
    (IMPORTANT tier: pipeline continues with degraded data quality).

    Args:
        session: Active SQLAlchemy async session.
        asset: Asset ORM instance to fetch fundamentals for.
    """
    log = logger.bind(component="fundamental_fetcher", asset=asset.symbol)

    # Fundamental ratios are only meaningful for stocks
    if asset.asset_type != "stock":
        log.debug("skipping_non_stock", asset_type=asset.asset_type)
        return

    # Check cache freshness
    result = await session.execute(
        select(StockFundamental).where(StockFundamental.asset_id == asset.id)
    )
    existing: StockFundamental | None = result.scalar_one_or_none()

    if existing is not None:
        age = datetime.now(UTC) - existing.fetched_at.replace(tzinfo=UTC) if existing.fetched_at.tzinfo is None else datetime.now(UTC) - existing.fetched_at
        if age < timedelta(days=_CACHE_TTL_DAYS):
            log.debug(
                "cache_fresh",
                asset_id=asset.id,
                age_days=age.days,
                ttl_days=_CACHE_TTL_DAYS,
            )
            return

    # Resolve yfinance symbol
    yf_symbol = asset.yfinance_symbol or f"{asset.symbol}.JK"

    log.info("fetching_fundamentals", symbol=yf_symbol)

    loop = asyncio.get_event_loop()
    info = await loop.run_in_executor(None, _fetch_yfinance_info, yf_symbol)

    if not info:
        log.warning(
            "fundamental_fetch_empty",
            symbol=yf_symbol,
            note="yfinance returned no data or raised an exception",
        )
        return

    # UPSERT into stock_fundamentals (conflict on asset_id -- one row per asset)
    stmt = pg_insert(StockFundamental).values(
        asset_id=asset.id,
        trailing_pe=info.get("trailing_pe"),
        forward_pe=info.get("forward_pe"),
        price_to_book=info.get("price_to_book"),
        return_on_equity=info.get("return_on_equity"),
        revenue_growth=info.get("revenue_growth"),
        dividend_yield=info.get("dividend_yield"),
        debt_to_equity=info.get("debt_to_equity"),
    ).on_conflict_do_update(
        constraint="uq_stock_fundamentals_asset",
        set_={
            "trailing_pe": info.get("trailing_pe"),
            "forward_pe": info.get("forward_pe"),
            "price_to_book": info.get("price_to_book"),
            "return_on_equity": info.get("return_on_equity"),
            "revenue_growth": info.get("revenue_growth"),
            "dividend_yield": info.get("dividend_yield"),
            "debt_to_equity": info.get("debt_to_equity"),
            "fetched_at": datetime.now(UTC),
        },
    )

    await session.execute(stmt)
    await session.commit()

    log.info(
        "fundamentals_upserted",
        asset_id=asset.id,
        symbol=yf_symbol,
        trailing_pe=info.get("trailing_pe"),
    )
