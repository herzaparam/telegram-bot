"""Staleness detection for IDX stock and crypto data.

IDX stocks are stale if no data exists for the last trading day (Mon-Fri).
Crypto is stale if no data in the last 24 hours (24/7 market).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import structlog

logger = structlog.get_logger(__name__)


@dataclass
class StalenessResult:
    """Result of a staleness check for an asset."""

    asset_symbol: str
    asset_type: str
    is_stale: bool
    latest_data_time: datetime | None
    expected_by: datetime
    reason: str


def _last_trading_day(now: datetime) -> datetime:
    """Find the most recent trading day (Mon-Fri) up to and including now."""
    d = now.date()
    while d.weekday() >= 5:  # Saturday=5, Sunday=6
        d -= timedelta(days=1)
    return datetime(d.year, d.month, d.day, 23, 59, tzinfo=UTC)


def check_staleness(
    asset_symbol: str,
    asset_type: str,
    latest_data_time: datetime | None,
    now: datetime | None = None,
) -> StalenessResult:
    """Check whether an asset's data is stale.

    Args:
        asset_symbol: Human-readable symbol (e.g. 'BBCA.JK', 'BTC').
        asset_type: Either 'stock' or 'crypto'.
        latest_data_time: Most recent data timestamp, or None if no data.
        now: Current time (defaults to UTC now). Inject for testing.

    Returns:
        StalenessResult with is_stale flag and reason.
    """
    if now is None:
        now = datetime.now(UTC)

    if asset_type == "stock":
        return _check_stock_staleness(asset_symbol, latest_data_time, now)
    return _check_crypto_staleness(asset_symbol, latest_data_time, now)


def _check_stock_staleness(
    asset_symbol: str,
    latest_data_time: datetime | None,
    now: datetime,
) -> StalenessResult:
    """IDX stock staleness: stale if no data for last trading day."""
    expected_by = _last_trading_day(now)
    last_td = expected_by.date()

    if latest_data_time is None:
        reason = "No data at all"
        is_stale = True
    elif latest_data_time.date() < last_td:
        reason = f"No data for last trading day {last_td}"
        is_stale = True
    else:
        reason = ""
        is_stale = False

    if is_stale:
        logger.warning("asset_stale", asset=asset_symbol, type="stock", reason=reason)

    return StalenessResult(
        asset_symbol=asset_symbol,
        asset_type="stock",
        is_stale=is_stale,
        latest_data_time=latest_data_time,
        expected_by=expected_by,
        reason=reason,
    )


def _check_crypto_staleness(
    asset_symbol: str,
    latest_data_time: datetime | None,
    now: datetime,
) -> StalenessResult:
    """Crypto staleness: stale if no data in last 24 hours."""
    expected_by = now - timedelta(hours=24)

    if latest_data_time is None:
        reason = "No data at all"
        is_stale = True
    elif (now - latest_data_time) > timedelta(hours=24):
        reason = "No data in last 24 hours"
        is_stale = True
    else:
        reason = ""
        is_stale = False

    if is_stale:
        logger.warning("asset_stale", asset=asset_symbol, type="crypto", reason=reason)

    return StalenessResult(
        asset_symbol=asset_symbol,
        asset_type="crypto",
        is_stale=is_stale,
        latest_data_time=latest_data_time,
        expected_by=expected_by,
        reason=reason,
    )
