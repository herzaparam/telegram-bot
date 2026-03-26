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
from src.db.models import Asset, Watchlist
from src.llm.news_analyzer import score_news_impact
from src.logging import setup_logging
from src.pipeline.runner import PipelineRunner

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

    # Post-pipeline: send daily Telegram report (D-15)
    # Report runs after all stages, not as a per-asset StageFunc
    all_failed = all(r.status == "failed" for r in results) if results else True
    if all_failed and results:
        await send_pipeline_failure_alert(run_date)
    else:
        async with async_session_factory() as session:
            await send_daily_report(session, run_date, stage_results=results, discoveries=discovery_results)


def main() -> None:
    """Synchronous entry point."""
    asyncio.run(async_main())


if __name__ == "__main__":
    main()
