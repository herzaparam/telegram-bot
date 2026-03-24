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

from src.config import settings
from src.data.analyze import analyze_stage
from src.data.decide import decide_stage
from src.data.evaluate import evaluate_stage
from src.data.ingest import ingest_stage
from src.data.reflect import reflect_stage, run_batch_cross_cutting
from src.data.report import send_daily_report, send_pipeline_failure_alert
from src.db.database import async_session_factory
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


async def async_main() -> None:
    """Async entry point for the pipeline."""
    setup_logging(settings.log_level, settings.log_format)

    parser = build_parser()
    args = parser.parse_args()

    run_date = date.fromisoformat(args.date) if args.date else date.today()
    stages = [args.stage] if args.stage else None

    runner = PipelineRunner(async_session_factory)
    stage_funcs = {
        "evaluate": evaluate_stage,  # Runs first: evaluate prior decisions (D-11)
        "reflect": reflect_stage,    # After evaluate: extract lessons from past decisions
        "fetch": ingest_stage,
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

    # Post-pipeline: send daily Telegram report (D-15)
    # Report runs after all stages, not as a per-asset StageFunc
    all_failed = all(r.status == "failed" for r in results) if results else True
    if all_failed and results:
        await send_pipeline_failure_alert(run_date)
    else:
        async with async_session_factory() as session:
            await send_daily_report(session, run_date, stage_results=results)


def main() -> None:
    """Synchronous entry point."""
    asyncio.run(async_main())


if __name__ == "__main__":
    main()
