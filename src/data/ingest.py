"""Ingest stage function for the PipelineRunner.

Fetches OHLCV data from external sources, validates, upserts to
TimescaleDB, and checks staleness. Supports delta-fetch, weekly
re-fetch for corrections, and adaptive backoff persistence.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, date, datetime, timedelta

import asyncpg
import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import settings
from src.data.alerts import AlertCollector
from src.data.crypto import CryptoFetcher
from src.data.idx_stocks import IDXStockFetcher
from src.data.staleness import check_staleness
from src.data.validation import validate_rows
from src.db.models import Asset, BackoffState
from src.db.price_repo import get_latest_date, upsert_prices
from src.pipeline.tiers import handle_source_failure

logger = structlog.get_logger(__name__)

# Module-level alert collector (shared within a pipeline run)
_alert_collector = AlertCollector()


def get_alert_collector() -> AlertCollector:
    """Return the module-level alert collector."""
    return _alert_collector


def reset_alert_collector() -> None:
    """Reset the module-level alert collector (called at start of pipeline run)."""
    global _alert_collector  # noqa: PLW0603
    _alert_collector = AlertCollector()


def _should_weekly_refresh(source: str) -> bool:
    """Check if today is Monday, triggering a weekly re-fetch of last 30 days.

    Args:
        source: Data source name (for logging).

    Returns:
        True if today is Monday (weekday == 0).
    """
    is_monday = date.today().weekday() == 0
    logger.info("weekly_refresh_check", source=source, is_monday=is_monday)
    return is_monday


async def _read_backoff_state(
    session: AsyncSession, source: str
) -> tuple[float, int]:
    """Read adaptive backoff state from the database.

    Creates a default row if none exists for this source.

    Args:
        session: SQLAlchemy async session.
        source: Data source name (e.g. 'yfinance', 'ccxt').

    Returns:
        Tuple of (current_delay_seconds, consecutive_failures).
    """
    result = await session.execute(
        select(BackoffState).where(BackoffState.source == source)
    )
    state = result.scalar_one_or_none()

    if state is None:
        state = BackoffState(
            source=source,
            consecutive_failures=0,
            current_delay_seconds=1.0,
        )
        session.add(state)
        await session.flush()

    logger.info(
        "backoff_state_read",
        source=source,
        delay=state.current_delay_seconds,
        failures=state.consecutive_failures,
    )
    return (state.current_delay_seconds, state.consecutive_failures)


async def _update_backoff_success(session: AsyncSession, source: str) -> None:
    """Reset backoff state after a successful fetch.

    Args:
        session: SQLAlchemy async session.
        source: Data source name.
    """
    result = await session.execute(
        select(BackoffState).where(BackoffState.source == source)
    )
    state = result.scalar_one_or_none()
    if state is not None:
        state.consecutive_failures = 0
        state.last_success_at = datetime.now(UTC)
        state.current_delay_seconds = 1.0
        await session.commit()


async def _update_backoff_failure(session: AsyncSession, source: str) -> None:
    """Increment backoff state after a failed fetch.

    Doubles delay with a cap at 300 seconds (5 minutes).

    Args:
        session: SQLAlchemy async session.
        source: Data source name.
    """
    result = await session.execute(
        select(BackoffState).where(BackoffState.source == source)
    )
    state = result.scalar_one_or_none()
    if state is not None:
        state.consecutive_failures += 1
        state.last_failure_at = datetime.now(UTC)
        state.current_delay_seconds = min(state.current_delay_seconds * 2, 300.0)
        await session.commit()


async def ingest_stage(session: AsyncSession, asset: Asset) -> None:
    """Ingest stage function matching StageFunc signature.

    Fetches OHLCV data, validates, upserts, and checks staleness.
    Supports delta-fetch, auto-backfill, weekly re-fetch, and adaptive backoff.

    Args:
        session: SQLAlchemy async session.
        asset: Asset to process.

    Raises:
        SourceCriticalError: If the fetcher fails (price_ohlcv is CRITICAL tier).
    """
    log = logger.bind(asset=asset.symbol, asset_type=asset.asset_type)

    # Select fetcher based on asset type
    if asset.asset_type == "stock":
        fetcher = IDXStockFetcher()
        symbol = asset.yfinance_symbol or asset.symbol
    else:
        fetcher = CryptoFetcher()
        symbol = asset.ccxt_symbol or asset.symbol

    # Read adaptive backoff state
    delay_seconds, failures = await _read_backoff_state(session, fetcher.source_name)
    if delay_seconds > 1.0:
        log.info(
            "adaptive_backoff_applied",
            source=fetcher.source_name,
            delay=delay_seconds,
            prior_failures=failures,
        )
        await asyncio.sleep(delay_seconds)

    # Connect to DB via raw asyncpg for hot-path operations
    raw_url = settings.database_url.replace("postgresql+asyncpg://", "postgresql://")
    conn = await asyncpg.connect(raw_url)

    try:
        # Get latest stored date
        latest = await get_latest_date(conn, asset.id)
        today = date.today()

        # Determine fetch range
        is_weekly = _should_weekly_refresh(fetcher.source_name)

        if is_weekly:
            start = today - timedelta(days=30)
            log.info("weekly_correction_refetch", refetch_start=str(start))
        elif latest is None:
            # Auto-backfill: 2 years of history
            start = today - timedelta(days=730)
            log.info("auto_backfill", start=str(start))
        else:
            start = latest.date() + timedelta(days=1)

        end = today

        if start > end:
            log.info("data_up_to_date", latest=str(latest))
            return

        # Fetch data
        try:
            rows = await fetcher.fetch(
                asset_id=asset.id, symbol=symbol, start=start, end=end
            )
            # Update backoff state on success
            await _update_backoff_success(session, fetcher.source_name)
        except Exception as exc:
            # Update backoff state on failure
            await _update_backoff_failure(session, fetcher.source_name)
            _alert_collector.add_fetch_failure(asset.symbol, str(exc))
            # price_ohlcv is CRITICAL tier -- raises SourceCriticalError
            handle_source_failure("price_ohlcv", exc)
            return  # unreachable due to raise, but satisfies type checker

        # Validate
        validation = validate_rows(rows, asset_symbol=asset.symbol)
        valid_rows = validation.valid

        # Upsert valid rows (ON CONFLICT UPDATE for idempotency + correction handling)
        upserted = await upsert_prices(conn, valid_rows)

        # For crypto: also fetch and upsert hourly candles (last 7 days)
        if asset.asset_type == "crypto" and hasattr(fetcher, "fetch_hourly"):
            hourly_start = today - timedelta(days=7)
            hourly_rows = await fetcher.fetch_hourly(
                asset_id=asset.id, symbol=symbol, start=hourly_start, end=end
            )
            hourly_validation = validate_rows(hourly_rows, asset_symbol=asset.symbol)
            await upsert_prices(conn, hourly_validation.valid, table="price_history_hourly")

        # Check staleness after upsert
        latest_after = await get_latest_date(conn, asset.id)
        staleness = check_staleness(
            asset.symbol, asset.asset_type, latest_after
        )
        if staleness.is_stale:
            _alert_collector.add_stale(asset.symbol, staleness.reason)

        log.info(
            "ingest_complete",
            rows_fetched=len(rows),
            rows_rejected=len(validation.rejected),
            rows_upserted=upserted,
            is_stale=staleness.is_stale,
            weekly_refetch=is_weekly,
        )

    finally:
        await conn.close()
