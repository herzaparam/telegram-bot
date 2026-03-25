"""Ingest stage function for the PipelineRunner.

Fetches OHLCV data from external sources, validates, upserts to
TimescaleDB, and checks staleness. Supports delta-fetch, weekly
re-fetch for corrections, and adaptive backoff persistence.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, date, datetime, timedelta
from typing import cast

import asyncpg
import httpx
import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import settings
from src.data.alerts import AlertCollector
from src.data.base import BaseFetcher
from src.data.crypto import CryptoFetcher
from src.data.idx_doc_fetcher import fetch_idx_docs
from src.data.idx_stocks import IDXStockFetcher
from src.data.staleness import check_staleness
from src.data.validation import validate_rows
from src.db.models import Asset, BackoffState, FinancialData, FinancialDoc
from src.db.price_repo import get_latest_date, upsert_prices
from src.llm.doc_parser import parse_financial_doc
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


def _period_to_date(period: str) -> date:
    """Convert period string like 'Q3 2025' or 'FY 2025' to a period-end date.

    Q1 -> March 31, Q2 -> June 30, Q3 -> September 30, Q4/FY -> December 31.
    """
    parts = period.strip().split()
    if len(parts) < 2:
        return date.today()

    prefix = parts[0].upper()
    try:
        year = int(parts[-1])
    except ValueError:
        year = date.today().year

    quarter_end = {
        "Q1": (year, 3, 31),
        "Q2": (year, 6, 30),
        "Q3": (year, 9, 30),
        "Q4": (year, 12, 31),
        "FY": (year, 12, 31),
    }

    y, m, d = quarter_end.get(prefix, (year, 12, 31))
    return date(y, m, d)


async def _fetch_and_parse_docs(session: AsyncSession, asset: Asset) -> None:
    """Fetch IDX financial docs and parse pending ones.

    1. Calls fetch_idx_docs to download new PDFs.
    2. On fetch exception: logs error and sends Telegram alert (D-05).
    3. Queries pending FinancialDoc rows and parses each via LLM.
    4. Creates FinancialData rows for each parsed metric.

    Args:
        session: SQLAlchemy async session.
        asset: Stock asset to process.
    """
    log = logger.bind(component="doc_pipeline", asset=asset.symbol)

    # 1. Fetch new docs (with Telegram alert on failure per D-05)
    try:
        await fetch_idx_docs(session, asset)
    except Exception as exc:
        log.error("idx_doc_fetch_failed", asset=asset.symbol, error=str(exc))
        # Send Telegram alert per D-05
        try:
            token = settings.telegram_bot_token.get_secret_value()
            chat_id = settings.telegram_chat_id
            if token and chat_id:
                alert_text = f"IDX doc fetch failed for {asset.symbol}: {exc}"
                url = f"https://api.telegram.org/bot{token}/sendMessage"
                async with httpx.AsyncClient(timeout=10.0) as client:
                    await client.post(url, json={"chat_id": chat_id, "text": alert_text})
        except Exception:
            log.warning("telegram_alert_failed", asset=asset.symbol)

    # 2. Parse pending docs
    try:
        result = await session.execute(
            select(FinancialDoc)
            .where(FinancialDoc.asset_id == asset.id)
            .where(FinancialDoc.parse_status == "pending")
        )
        pending_docs = result.scalars().all()

        for doc in pending_docs:
            parsed = await parse_financial_doc(doc.file_path, asset.symbol)

            if parsed is None:
                doc.parse_status = "failed"
                continue

            # Create FinancialData rows for each field
            period_str = parsed.get("period", "")
            period_dt = _period_to_date(period_str)
            # Normalize period string (e.g. "Q3 2025" -> "Q3-2025")
            period_label = period_str.replace(" ", "-") if period_str else ""

            text_fields = {"management_outlook", "currency_unit"}
            skip_fields = {"period", "currency_unit"}

            for key, value in parsed.items():
                if key in skip_fields:
                    continue
                if value is None:
                    continue

                fd = FinancialData(
                    doc_id=doc.id,
                    asset_id=asset.id,
                    metric_name=key,
                    metric_value=float(value) if key not in text_fields and isinstance(value, (int, float)) else None,
                    metric_text=str(value) if key in text_fields else None,
                    period=period_label,
                    period_date=period_dt,
                )
                session.add(fd)

            doc.parse_status = "parsed"
            doc.parsed_at = datetime.now(UTC)

        await session.flush()
    except Exception as exc:
        log.error("doc_parse_loop_failed", asset=asset.symbol, error=str(exc))


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
    fetcher: BaseFetcher
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
            crypto_fetcher = cast(CryptoFetcher, fetcher)
            hourly_start = today - timedelta(days=7)
            hourly_rows = await crypto_fetcher.fetch_hourly(
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

    # Fetch and parse IDX financial docs for stock assets only
    if asset.asset_type == "stock":
        await _fetch_and_parse_docs(session, asset)
