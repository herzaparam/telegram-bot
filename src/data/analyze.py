"""Analyze stage: run signal engines on price data and store results."""

from __future__ import annotations

import gc
from datetime import date, datetime

import pandas as pd
import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import Asset, MacroData, NewsEvent, PriceHistory, StockFundamental
from src.db.signal_repo import signal_repo
from src.engines.base import BaseEngine, Signal
from src.engines.event import EventEngine
from src.engines.fundamental import FundamentalEngine
from src.engines.macro import MacroEngine
from src.engines.quantitative import QuantitativeEngine
from src.engines.sentiment import SentimentEngine
from src.engines.technical import TechnicalEngine

logger = structlog.get_logger(__name__)

# Module-level sentiment cache -- set once per pipeline run by fetch_global_data
_sentiment_cache: object | None = None


def set_sentiment_cache(data: object | None) -> None:
    """Set the module-level sentiment cache for the current pipeline run."""
    global _sentiment_cache
    _sentiment_cache = data


def _get_engines_for_asset(
    asset: Asset,
    fundamentals: dict[str, float | None] | None = None,
    macro_data: dict[str, float] | None = None,
    sentiment_data: object | None = None,
    news_events: list[dict[str, object]] | None = None,
) -> list[BaseEngine]:
    """Return engines applicable to this asset type."""
    all_engines: list[BaseEngine] = [
        TechnicalEngine(),
        QuantitativeEngine(),
        FundamentalEngine(fundamentals=fundamentals),
        MacroEngine(macro_data=macro_data),
        SentimentEngine(sentiment_data=sentiment_data),
        EventEngine(news_events=news_events),
    ]
    return [
        e for e in all_engines
        if (asset.asset_type == "stock" and e.supports_stocks)
        or (asset.asset_type == "crypto" and e.supports_crypto)
    ]


def _failed_signal(category: str, error: str) -> Signal:
    """Return a zero-score signal for a failed engine."""
    return Signal(
        category=category,
        score=0.0,
        confidence=0.0,
        reasoning=f"Engine failed: {error}",
        indicators={},
        data_quality={"error": error},
    )


async def _load_price_dataframe(
    session: AsyncSession, asset: Asset, limit: int = 300,
) -> pd.DataFrame:
    """Load price history into a pandas DataFrame.

    Loads the most recent `limit` rows ordered by time descending,
    then reverses to chronological order.

    Args:
        session: Async SQLAlchemy session.
        asset: Asset to load prices for.
        limit: Maximum number of rows to load (default 300, covers 200 trading days + buffer).

    Returns:
        DataFrame with columns: open, high, low, close, volume, indexed by time.
    """
    result = await session.execute(
        select(PriceHistory)
        .where(PriceHistory.asset_id == asset.id)
        .order_by(PriceHistory.time.desc())
        .limit(limit)
    )
    rows = result.scalars().all()

    if not rows:
        return pd.DataFrame(columns=["open", "high", "low", "close", "volume"])

    data = [
        {
            "time": r.time,
            "open": r.open,
            "high": r.high,
            "low": r.low,
            "close": r.close,
            "volume": r.volume,
        }
        for r in reversed(rows)  # Chronological order
    ]
    df = pd.DataFrame(data)
    df.set_index("time", inplace=True)
    return df


async def _load_fundamentals(
    session: AsyncSession, asset_id: int
) -> dict[str, float | None] | None:
    """Load cached fundamental data for an asset.

    Args:
        session: Async SQLAlchemy session.
        asset_id: Asset primary key.

    Returns:
        Dict of fundamental ratios or None if no data cached.
    """
    result = await session.execute(
        select(StockFundamental).where(StockFundamental.asset_id == asset_id)
    )
    row = result.scalar_one_or_none()
    if row is None:
        return None
    return {
        "trailing_pe": row.trailing_pe,
        "price_to_book": row.price_to_book,
        "return_on_equity": row.return_on_equity,
        "revenue_growth": row.revenue_growth,
        "dividend_yield": row.dividend_yield,
        "debt_to_equity": row.debt_to_equity,
    }


async def _load_latest_macro(
    session: AsyncSession,
) -> dict[str, float] | None:
    """Load the latest value for each macro series.

    Args:
        session: Async SQLAlchemy session.

    Returns:
        Dict mapping friendly names to latest values, or None if no data.
    """
    from sqlalchemy import func as sqlfunc

    # Subquery: latest observation_date per series_id
    subq = (
        select(MacroData.series_id, sqlfunc.max(MacroData.observation_date).label("max_date"))
        .group_by(MacroData.series_id)
        .subquery()
    )
    result = await session.execute(
        select(MacroData).join(
            subq,
            (MacroData.series_id == subq.c.series_id)
            & (MacroData.observation_date == subq.c.max_date),
        )
    )
    rows = result.scalars().all()
    if not rows:
        return None
    # Map series_id back to friendly names
    series_to_name = {
        "DFF": "fed_funds_rate",
        "CPIAUCSL": "cpi",
        "DTWEXBGS": "dxy",
        "CCUSMA02IDM618N": "usd_idr",
    }
    return {series_to_name.get(r.series_id, r.series_id): r.value for r in rows}


async def _load_recent_news(session: AsyncSession) -> list[dict[str, object]]:
    """Load today's scored news events.

    Args:
        session: Async SQLAlchemy session.

    Returns:
        List of news event dicts with headline, source, category, impact_score, affected_assets.
    """
    today = date.today()
    result = await session.execute(
        select(NewsEvent)
        .where(NewsEvent.fetched_at >= datetime.combine(today, datetime.min.time()))
        .where(NewsEvent.impact_score.isnot(None))
    )
    rows = result.scalars().all()
    return [
        {
            "headline": r.headline,
            "source": r.source,
            "category": r.category,
            "impact_score": r.impact_score,
            "affected_assets": r.affected_assets or {},
        }
        for r in rows
    ]


async def analyze_stage(session: AsyncSession, asset: Asset) -> None:
    """Analyze stage matching StageFunc signature.

    Loads price data and store-backed context, runs all applicable engines,
    stores signals.

    Per D-05/D-13: loads fundamentals (stocks only), macro data, and
    today's scored news events from the DB before running engines.

    Args:
        session: Async SQLAlchemy session.
        asset: Asset to analyze.
    """
    log = logger.bind(asset=asset.symbol, asset_type=asset.asset_type)

    # 1. Load price data
    df = await _load_price_dataframe(session, asset)
    if df.empty:
        log.warning("no_price_data_for_analysis")
        return

    # 2. Load store-backed engine data
    fundamentals = (
        await _load_fundamentals(session, asset.id)
        if asset.asset_type == "stock"
        else None
    )
    macro_data = await _load_latest_macro(session)
    news_events = await _load_recent_news(session)

    # 3. Run engines sequentially (CPU-bound)
    engines = _get_engines_for_asset(
        asset,
        fundamentals=fundamentals,
        macro_data=macro_data,
        sentiment_data=_sentiment_cache,
        news_events=news_events,
    )
    signals: list[Signal] = []

    for engine in engines:
        try:
            signal = engine.analyze(asset.id, asset.symbol, df)
            signals.append(signal)
            log.info(
                "engine_completed",
                engine=engine.category,
                score=signal.score,
                confidence=signal.confidence,
            )
        except Exception as exc:
            log.warning("engine_failed", engine=engine.category, error=str(exc))
            signals.append(_failed_signal(engine.category, str(exc)))

    # 4. Store signals in one transaction
    if signals:
        price_at_signal = float(df["close"].iloc[-1])
        await signal_repo.upsert_signals(
            session, asset.id, date.today(), signals, price_at_signal,
        )
        log.info("signals_stored", count=len(signals))

    # 5. Release DataFrame memory
    del df
    gc.collect()
