"""Analyze stage: run signal engines on price data and store results."""

from __future__ import annotations

import gc
from datetime import date, datetime, timedelta

import pandas as pd
import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import Asset, FinancialData, MacroData, NewsEvent, PriceHistory, StockFundamental
from src.db.signal_repo import signal_repo
from src.engines.base import BaseEngine, Signal
from src.engines.event import EventEngine
from src.engines.fundamental import FundamentalEngine
from src.engines.macro import MacroEngine
from src.engines.quantitative import QuantitativeEngine
from src.engines.sentiment import SentimentEngine
from src.engines.technical import TechnicalEngine
from src.engines.valuation import IDX_SECTOR_MAP, ValuationEngine
from src.engines.ml_ai import MLAIEngine
from src.engines.onchain import OnChainEngine
from src.engines.options import OptionsEngine
from src.engines.behavioral import BehavioralEngine
from src.engines.alternative import AlternativeDataEngine
from src.engines.network import NetworkEngine
from src.engines.game_theory import GameTheoryEngine
from src.engines.emerging import EmergingMethodsEngine

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
    financial_data: list[dict] | None = None,  # type: ignore[type-arg]
    peer_data: list[dict] | None = None,  # type: ignore[type-arg]
    shares_outstanding: float | None = None,
    nvt_data: dict[str, float] | None = None,
    tvl_data: dict[str, float] | None = None,
    # Phase 10 engine data:
    onchain_data: dict[str, float] | None = None,
    github_data: dict[str, int | float] | None = None,
    correlation_data: dict[str, float] | None = None,
) -> list[BaseEngine]:
    """Return engines applicable to this asset type."""
    all_engines: list[BaseEngine] = [
        # Phase 3 engines
        TechnicalEngine(),
        QuantitativeEngine(),
        # Phase 8 engines
        FundamentalEngine(fundamentals=fundamentals),
        MacroEngine(macro_data=macro_data),
        SentimentEngine(sentiment_data=sentiment_data),
        EventEngine(news_events=news_events),
        # Phase 9 engine
        ValuationEngine(
            financial_data=financial_data,
            peer_data=peer_data,
            macro_rates=macro_data,
            shares_outstanding=shares_outstanding,
            nvt_data=nvt_data,
            tvl_data=tvl_data,
        ),
        # Phase 10 engines
        MLAIEngine(asset_type=asset.asset_type),
        OnChainEngine(onchain_data=onchain_data),
        OptionsEngine(),
        BehavioralEngine(),
        AlternativeDataEngine(github_data=github_data),
        NetworkEngine(correlation_data=correlation_data),
        GameTheoryEngine(),
        EmergingMethodsEngine(),
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


async def _load_financial_data(
    session: AsyncSession, asset: Asset,
) -> list[dict] | None:  # type: ignore[type-arg]
    """Load parsed financial data for an asset from the financial_data table.

    Groups metrics by period into a list of dicts ordered by period_date DESC.

    Args:
        session: Async SQLAlchemy session.
        asset: Asset to load data for.

    Returns:
        List of period dicts like [{"period": "Q3-2025", "revenue": 1e12, ...}],
        or None if no data found.
    """
    result = await session.execute(
        select(FinancialData)
        .where(FinancialData.asset_id == asset.id)
        .order_by(FinancialData.period_date.desc())
        .limit(20)
    )
    rows = result.scalars().all()

    if not rows:
        return None

    # Group by period
    periods: dict[str, dict] = {}  # type: ignore[type-arg]
    for row in rows:
        if row.period not in periods:
            periods[row.period] = {"period": row.period}
        if row.metric_value is not None:
            periods[row.period][row.metric_name] = row.metric_value
        elif row.metric_text is not None:
            periods[row.period][row.metric_name] = row.metric_text

    return list(periods.values())


async def _load_peer_data(
    session: AsyncSession, asset: Asset,
) -> list[dict] | None:  # type: ignore[type-arg]
    """Load peer metrics for same-sector stocks from StockFundamental.

    Looks up sector from IDX_SECTOR_MAP, finds peer assets,
    and computes sector averages for P/E and P/B.

    Args:
        session: Async SQLAlchemy session.
        asset: Asset to find peers for.

    Returns:
        List of dicts with sector averages as first entry, or None.
    """
    sector = IDX_SECTOR_MAP.get(asset.symbol)
    if not sector:
        return None

    # Find all symbols in same sector
    peer_symbols = [s for s, sec in IDX_SECTOR_MAP.items() if sec == sector]
    if not peer_symbols:
        return None

    # Query assets matching peer symbols
    result = await session.execute(
        select(Asset).where(Asset.symbol.in_(peer_symbols))
    )
    peer_assets = result.scalars().all()
    peer_ids = [a.id for a in peer_assets]

    if not peer_ids:
        return None

    # Query StockFundamental for peer assets
    fund_result = await session.execute(
        select(StockFundamental).where(StockFundamental.asset_id.in_(peer_ids))
    )
    funds = fund_result.scalars().all()

    if not funds:
        return None

    # Compute sector averages
    pe_vals = [f.trailing_pe for f in funds if f.trailing_pe is not None]
    pb_vals = [f.price_to_book for f in funds if f.price_to_book is not None]

    avg_pe = sum(pe_vals) / len(pe_vals) if pe_vals else None
    avg_pb = sum(pb_vals) / len(pb_vals) if pb_vals else None

    sector_avg: dict[str, float] = {}
    if avg_pe is not None:
        sector_avg["pe"] = avg_pe
    if avg_pb is not None:
        sector_avg["pb"] = avg_pb

    if not sector_avg:
        return None

    return [sector_avg]


async def _load_onchain_data(session: AsyncSession, asset_id: int) -> dict[str, float] | None:
    """Load latest on-chain data for a crypto asset."""
    from src.db.models import OnChainData
    today = date.today()
    result = await session.execute(
        select(OnChainData)
        .where(OnChainData.asset_id == asset_id)
        .where(OnChainData.date >= today - timedelta(days=1))
    )
    rows = result.scalars().all()
    if not rows:
        return None
    data: dict[str, float] = {}
    for row in rows:
        data[row.metric] = row.value
        data[f"{row.metric}_source"] = row.source  # type: ignore[assignment]
    return data


async def _load_github_data(session: AsyncSession, asset_id: int) -> dict[str, int | float] | None:
    """Load latest GitHub activity for a crypto asset."""
    from src.db.models import GitHubActivity
    today = date.today()
    result = await session.execute(
        select(GitHubActivity)
        .where(GitHubActivity.asset_id == asset_id)
        .where(GitHubActivity.date >= today - timedelta(days=1))
    )
    row = result.scalars().first()
    if not row:
        return None
    return {"stars": row.stars, "forks": row.forks, "weekly_commits": row.weekly_commits, "contributors": row.contributors}


async def _compute_correlation_data(
    session: AsyncSession, current_asset_id: int, current_prices: pd.DataFrame
) -> dict[str, float] | None:
    """Compute rolling 30-day correlation between current asset and all watchlist assets.

    Args:
        session: DB session
        current_asset_id: ID of the asset being analyzed
        current_prices: Already-loaded price DataFrame for the current asset (must have 'close' column)

    Returns:
        Dict with avg_correlation, max_correlation, min_correlation, num_assets or None if insufficient data.
    """
    from src.db.models import Asset as AssetModel, Watchlist
    import numpy as np

    # Get all watchlisted asset IDs
    result = await session.execute(
        select(Watchlist.asset_id).where(Watchlist.asset_id != current_asset_id).distinct()
    )
    other_asset_ids = [r[0] for r in result.all()]
    if not other_asset_ids:
        return None

    current_close = current_prices["close"].tail(30).values
    if len(current_close) < 20:
        return None

    # Load 30-day close prices for each other watchlisted asset
    correlations: list[float] = []
    for aid in other_asset_ids:
        # Query the asset to get a proper object for _load_price_dataframe
        asset_result = await session.execute(select(AssetModel).where(AssetModel.id == aid))
        other_asset = asset_result.scalar_one_or_none()
        if other_asset is None:
            continue
        other_df = await _load_price_dataframe(session, other_asset, limit=30)
        if other_df.empty or len(other_df) < 20:
            continue
        other_close = other_df["close"].tail(30).values

        # Align lengths
        min_len = min(len(current_close), len(other_close))
        if min_len < 10:
            continue
        c = current_close[-min_len:]
        o = other_close[-min_len:]

        # Skip if constant (no variance)
        if np.std(c) == 0 or np.std(o) == 0:
            continue

        corr = float(np.corrcoef(c, o)[0, 1])
        if not np.isnan(corr):
            correlations.append(corr)

    if not correlations:
        return None

    return {
        "avg_correlation": float(np.mean(correlations)),
        "max_correlation": float(np.max(np.abs(correlations))),
        "min_correlation": float(np.min(correlations)),
        "num_assets": len(correlations),
    }


def _cross_validate(
    financial_data: list[dict],  # type: ignore[type-arg]
    yf_fundamentals: dict,  # type: ignore[type-arg]
) -> list[str]:
    """Cross-validate PDF-extracted financials against yfinance market data.

    Flags discrepancies >10% between extracted values and yfinance values.

    Args:
        financial_data: List of period dicts (latest first).
        yf_fundamentals: Dict from yfinance info with totalRevenue, netIncome.

    Returns:
        List of warning strings for values differing >10%.
    """
    if not financial_data or not yf_fundamentals:
        return []

    latest = financial_data[0]
    warnings: list[str] = []

    comparisons = [
        ("revenue", "totalRevenue", "Revenue"),
        ("net_profit", "netIncome", "Net profit"),
    ]

    for pdf_key, yf_key, label in comparisons:
        pdf_val = latest.get(pdf_key)
        yf_val = yf_fundamentals.get(yf_key)

        if pdf_val is None or yf_val is None:
            continue
        if not isinstance(pdf_val, (int, float)) or not isinstance(yf_val, (int, float)):
            continue
        if pdf_val == 0:
            continue

        diff_pct = abs(pdf_val - yf_val) / abs(pdf_val) * 100
        if diff_pct > 10.0:
            warnings.append(
                f"{label} differs from market data by {diff_pct:.1f}%"
            )

    return warnings


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

    # Load valuation data
    financial_data = None
    peer_data = None
    nvt_data = None
    tvl_data = None

    if asset.asset_type == "stock":
        financial_data = await _load_financial_data(session, asset)
        peer_data = await _load_peer_data(session, asset)
    else:
        # Crypto: NVT proxy data from price data if available
        if not df.empty and "close" in df.columns and "volume" in df.columns:
            close = float(df["close"].iloc[-1])
            vol = float(df["volume"].iloc[-1])
            if close > 0 and vol > 0:
                nvt_data = {"market_cap": close * vol, "volume_24h": vol}
        # DeFi crypto: tvl_data (per D-13) -- passed as None, ValuationEngine handles gracefully

    # Load Phase 10 engine data
    onchain_data = None
    github_data = None
    correlation_data = None

    if asset.asset_type == "crypto":
        onchain_data = await _load_onchain_data(session, asset.id)
        github_data = await _load_github_data(session, asset.id)

    correlation_data = await _compute_correlation_data(session, asset.id, df)

    # 3. Run engines sequentially (CPU-bound)
    engines = _get_engines_for_asset(
        asset,
        fundamentals=fundamentals,
        macro_data=macro_data,
        sentiment_data=_sentiment_cache,
        news_events=news_events,
        financial_data=financial_data,
        peer_data=peer_data,
        nvt_data=nvt_data,
        tvl_data=tvl_data,
        onchain_data=onchain_data,
        github_data=github_data,
        correlation_data=correlation_data,
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
