"""Macro data fetcher using the FRED API via fredapi.

Retrieves Federal Funds Rate, CPI, DXY, and USD/IDR from FRED and
stores the latest observations in the macro_data table.

Skips all fetching when FRED_API_KEY is not configured.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, date, datetime
from typing import Any

import structlog
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import settings
from src.db.models import MacroData

logger = structlog.get_logger(__name__)

# FRED series IDs to fetch (human_name -> FRED series ID)
FRED_SERIES: dict[str, str] = {
    "fed_funds_rate": "DFF",
    "cpi": "CPIAUCSL",
    "dxy": "DTWEXBGS",
    "usd_idr": "CCUSMA02IDM618N",
}


def _fetch_fred_series(fred: Any, series_id: str) -> tuple[date, float] | None:
    """Synchronous FRED series fetch returning the latest observation.

    Args:
        fred: fredapi.Fred client instance.
        series_id: FRED series identifier (e.g. "DFF").

    Returns:
        Tuple of (observation_date, value) for the latest non-NaN observation,
        or None if the fetch failed.
    """
    try:
        series = fred.get_series(series_id)
        series = series.dropna()
        if series.empty:
            return None
        last_value = float(series.iloc[-1])
        last_date: date = series.index[-1].date()
        return (last_date, last_value)
    except Exception as exc:  # noqa: BLE001
        log = logger.bind(component="macro_fetcher")
        log.warning("fred_series_failed", series_id=series_id, error=str(exc))
        return None


async def fetch_macro_data(session: AsyncSession) -> None:
    """Fetch latest macro indicators from FRED and upsert into macro_data table.

    Fetches each series independently so a single failure does not block
    the others (partial success). Skips entirely when FRED_API_KEY is empty.

    Args:
        session: Active SQLAlchemy async session.
    """
    log = logger.bind(component="macro_fetcher")

    if settings.fred_api_key == "":
        log.info("fred_api_key_missing", note="FRED_API_KEY not configured, skipping macro fetch")
        return

    from fredapi import Fred  # noqa: PLC0415

    fred = Fred(api_key=settings.fred_api_key)

    loop = asyncio.get_event_loop()
    upserted = 0

    for human_name, series_id in FRED_SERIES.items():
        try:
            result = await loop.run_in_executor(None, _fetch_fred_series, fred, series_id)
        except Exception as exc:  # noqa: BLE001
            log.warning(
                "fred_series_executor_failed",
                series_id=series_id,
                human_name=human_name,
                error=str(exc),
            )
            continue

        if result is None:
            log.warning("fred_series_no_data", series_id=series_id, human_name=human_name)
            continue

        obs_date, value = result

        stmt = pg_insert(MacroData).values(
            series_id=series_id,
            observation_date=obs_date,
            value=value,
            fetched_at=datetime.now(UTC),
        ).on_conflict_do_update(
            constraint="uq_macro_data_series_date",
            set_={
                "value": value,
                "fetched_at": datetime.now(UTC),
            },
        )

        await session.execute(stmt)
        upserted += 1

    await session.commit()

    log.info(
        "macro_data_fetched",
        series_attempted=len(FRED_SERIES),
        series_upserted=upserted,
    )
