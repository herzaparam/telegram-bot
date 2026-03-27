"""Pipeline CLI entry point.

Usage:
    python -m src.pipeline.main
    python -m src.pipeline.main --stage fetch
    python -m src.pipeline.main --date 2026-03-23 --rerun-failed
"""

import argparse
import asyncio
from datetime import date

import structlog
from sqlalchemy import select

import pandas as pd

from src.config import settings
from src.data.analyze import analyze_stage, set_sentiment_cache
from src.data.decide import decide_stage
from src.data.discovery import run_discovery_scan
from src.data.due_diligence import compute_dd_report
from src.data.evaluate import evaluate_stage
from src.data.fundamental_fetcher import fetch_fundamentals
from src.data.ingest import ingest_stage
from src.data.macro_fetcher import fetch_macro_data
from src.data.news_fetcher import fetch_news
from src.data.reflect import reflect_stage, run_batch_cross_cutting
from src.data.report import send_daily_report, send_pipeline_failure_alert
from src.data.sentiment_fetcher import fetch_sentiment_data
from src.db.database import async_session_factory
from src.db.models import Asset, PortfolioRiskSnapshot, PriceHistory, Watchlist
from src.engines.valuation import IDX_SECTOR_MAP
from src.llm.news_analyzer import score_news_impact
from src.logging import setup_logging
from src.pipeline.runner import PipelineRunner
from src.risk.concentration import compute_concentration
from src.risk.correlation import compute_correlation_matrix
from src.risk.metrics import compute_risk_metrics
from src.risk.var import compute_historical_var

logger = structlog.get_logger(__name__)


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser."""
    parser = argparse.ArgumentParser(
        description="Run the trade-agent data pipeline.",
    )
    parser.add_argument(
        "--date",
        type=str,
        default=None,
        help="Run date in YYYY-MM-DD format (default: today).",
    )
    parser.add_argument(
        "--stage",
        type=str,
        default=None,
        help="Run only the specified stage (evaluate, reflect, fetch, analyze, decide, report).",
    )
    parser.add_argument(
        "--rerun-failed",
        action="store_true",
        default=False,
        help="Reprocess assets with status 'failed'.",
    )
    return parser


async def fetch_global_data(session: "AsyncSession") -> None:  # type: ignore[name-defined]
    """Fetch global data once per pipeline run (macro, news, sentiment).

    Runs before per-asset processing. Per D-05, D-13.
    Each fetcher is independently wrapped in try/except -- partial success
    is always preferred over total failure.

    Args:
        session: Async SQLAlchemy session.
    """
    from sqlalchemy.ext.asyncio import AsyncSession  # noqa: F401 (inline to avoid circular)

    log = logger.bind(component="global_fetch")

    try:
        await fetch_macro_data(session)
        log.info("macro_data_fetched")
    except Exception:
        log.exception("macro_fetch_error")

    try:
        await fetch_news(session)
        log.info("news_fetched")
    except Exception:
        log.exception("news_fetch_error")

    try:
        sentiment = await fetch_sentiment_data(session)
        set_sentiment_cache(sentiment)
        log.info("sentiment_data_fetched")
    except Exception:
        log.exception("sentiment_fetch_error")

    # Score news headlines via LLM (per D-14)
    try:
        result = await session.execute(
            select(Asset.symbol).join(Watchlist, Watchlist.asset_id == Asset.id)
        )
        symbols = [row[0] for row in result.all()]
        if symbols:
            await score_news_impact(session, symbols)
            log.info("news_impact_scored", symbols=len(symbols))
    except Exception:
        log.exception("news_scoring_error")


async def _enhanced_ingest_stage(
    session: "AsyncSession",  # type: ignore[name-defined]
    asset: Asset,
) -> None:
    """Enhanced ingest: price data + per-asset fundamental data.

    Wraps the standard ingest_stage with an additional call to fetch_fundamentals
    for stock assets. Errors in fetch_fundamentals are caught individually to
    not block price data ingestion.

    Args:
        session: Async SQLAlchemy session.
        asset: Asset to process.
    """
    await ingest_stage(session, asset)
    try:
        await fetch_fundamentals(session, asset)
    except Exception:
        logger.exception("fundamental_fetch_error", asset=asset.symbol)
    if asset.asset_type == "stock":
        try:
            await compute_dd_report(session, asset, date.today())
        except Exception:
            logger.exception("dd_computation_error", asset=asset.symbol)


async def _compute_daily_risk_snapshot(run_date: date) -> dict | None:
    """Compute and store the daily portfolio risk snapshot.

    Queries watchlist assets and their price history, computes correlation,
    VaR, concentration, and risk metrics. Stores a PortfolioRiskSnapshot
    row (upsert by snapshot_date) and returns a dict for the report.
    """
    from datetime import datetime, timedelta

    from sqlalchemy import select
    from sqlalchemy.dialects.postgresql import insert as pg_insert

    async with async_session_factory() as session:
        # Query watchlist assets
        stmt = (
            select(Asset)
            .join(Watchlist, Watchlist.asset_id == Asset.id)
            .order_by(Asset.symbol)
        )
        result = await session.execute(stmt)
        assets_list = result.scalars().all()

        if not assets_list:
            return None

        # Fetch price history (last 365 days)
        cutoff = datetime.now() - timedelta(days=365)
        asset_ids = [a.id for a in assets_list]

        price_stmt = (
            select(PriceHistory)
            .where(
                PriceHistory.asset_id.in_(asset_ids),
                PriceHistory.time >= cutoff,
            )
            .order_by(PriceHistory.asset_id, PriceHistory.time)
        )
        price_result = await session.execute(price_stmt)
        price_rows = price_result.scalars().all()

        if not price_rows:
            return None

        # Build price_data dict
        asset_map = {a.id: a for a in assets_list}
        price_data: dict[str, pd.Series] = {}
        for row in price_rows:
            sym = asset_map[row.asset_id].symbol
            if sym not in price_data:
                price_data[sym] = pd.Series(dtype=float)
            price_data[sym] = pd.concat([
                price_data[sym],
                pd.Series([row.close], index=[pd.Timestamp(row.time)]),
            ])

        assets_dicts = [
            {"symbol": a.symbol, "asset_type": a.asset_type}
            for a in assets_list
        ]

        # Compute correlation
        corr_result = compute_correlation_matrix(price_data)
        correlation_alerts = list(corr_result.high_pairs)

        # Compute portfolio returns (equal-weight)
        returns_list = []
        for sym, series in price_data.items():
            if len(series) > 1:
                ret = series.sort_index().pct_change().dropna()
                returns_list.append(ret)

        var_summary: dict = {}
        sharpe: float | None = None
        sortino: float | None = None

        if returns_list:
            returns_df = pd.concat(returns_list, axis=1).dropna()
            if not returns_df.empty:
                portfolio_returns = returns_df.mean(axis=1)

                try:
                    var_result = compute_historical_var(portfolio_returns)
                    var_summary = {
                        "daily_var_95": var_result.daily_var_95,
                        "daily_var_99": var_result.daily_var_99,
                        "weekly_var_95": var_result.weekly_var_95,
                        "weekly_var_99": var_result.weekly_var_99,
                        "max_drawdown": var_result.max_drawdown,
                    }
                except ValueError:
                    pass

                metrics_result = compute_risk_metrics(portfolio_returns)
                sharpe = metrics_result.sharpe_ratio
                sortino = metrics_result.sortino_ratio

        # Compute concentration
        conc_result = compute_concentration(assets_dicts, IDX_SECTOR_MAP)

        # Build snapshot dict for report
        snapshot = {
            "concentration": {
                "sector_pct": conc_result.sector_pct,
                "max_single_pct": conc_result.max_single_pct,
                "idr_pct": conc_result.idr_pct,
                "usd_pct": conc_result.usd_pct,
            },
            "correlation_alerts": correlation_alerts,
            "var_summary": var_summary,
            "sharpe_ratio": sharpe,
            "sortino_ratio": sortino,
        }

        # Store in DB (upsert by snapshot_date)
        try:
            insert_stmt = pg_insert(PortfolioRiskSnapshot).values(
                snapshot_date=run_date,
                concentration=snapshot["concentration"],
                correlation_alerts=[list(a) for a in correlation_alerts],
                var_summary=var_summary,
                sharpe_ratio=sharpe,
                sortino_ratio=sortino,
            )
            upsert_stmt = insert_stmt.on_conflict_do_update(
                constraint="uq_risk_snapshot_date",
                set_={
                    "concentration": insert_stmt.excluded.concentration,
                    "correlation_alerts": insert_stmt.excluded.correlation_alerts,
                    "var_summary": insert_stmt.excluded.var_summary,
                    "sharpe_ratio": insert_stmt.excluded.sharpe_ratio,
                    "sortino_ratio": insert_stmt.excluded.sortino_ratio,
                },
            )
            await session.execute(upsert_stmt)
            await session.commit()
        except Exception:
            logger.exception("risk_snapshot_db_store_error")

        return snapshot


async def async_main() -> None:
    """Async entry point for the pipeline."""
    setup_logging(settings.log_level, settings.log_format)

    parser = build_parser()
    args = parser.parse_args()

    run_date = date.fromisoformat(args.date) if args.date else date.today()
    stages = [args.stage] if args.stage else None

    # Fetch global data (macro, news, sentiment) once before per-asset processing
    async with async_session_factory() as global_session:
        await fetch_global_data(global_session)

    runner = PipelineRunner(async_session_factory)
    stage_funcs = {
        "evaluate": evaluate_stage,  # Runs first: evaluate prior decisions (D-11)
        "reflect": reflect_stage,    # After evaluate: extract lessons from past decisions
        "fetch": _enhanced_ingest_stage,  # Price + fundamentals per asset
        "analyze": analyze_stage,
        "decide": decide_stage,
    }
    results = await runner.run_pipeline(
        run_date=run_date,
        stages=stages,
        stage_funcs=stage_funcs,
        rerun_failed=args.rerun_failed,
    )

    for result in results:
        logger.info(
            "stage_result",
            stage=result.stage,
            status=result.status,
            completed=result.assets_completed,
            failed=result.assets_failed,
            skipped=result.assets_skipped,
            duration=f"{result.duration_seconds:.2f}s",
        )

    # Post-reflect: run batch cross-cutting analysis (D-06)
    try:
        async with async_session_factory() as session:
            await run_batch_cross_cutting(session)
    except Exception:
        logger.exception("batch_cross_cutting_error")

    # Post-pipeline: discovery scan (DISC-01/02/03/04)
    discovery_results: list[dict] = []
    try:
        async with async_session_factory() as session:
            discovery_results = await run_discovery_scan(session, run_date)
    except Exception:
        logger.exception("discovery_scan_error")

    # Post-pipeline: compute daily risk snapshot (REPT-06)
    risk_snapshot: dict | None = None
    try:
        risk_snapshot = await _compute_daily_risk_snapshot(run_date)
    except Exception:
        logger.exception("risk_snapshot_error")

    # Post-pipeline: send daily Telegram report (D-15)
    # Report runs after all stages, not as a per-asset StageFunc
    all_failed = all(r.status == "failed" for r in results) if results else True
    if all_failed and results:
        await send_pipeline_failure_alert(run_date)
    else:
        async with async_session_factory() as session:
            await send_daily_report(
                session, run_date,
                stage_results=results,
                discoveries=discovery_results,
                risk_snapshot=risk_snapshot,
            )


def main() -> None:
    """Synchronous entry point."""
    asyncio.run(async_main())


if __name__ == "__main__":
    main()
