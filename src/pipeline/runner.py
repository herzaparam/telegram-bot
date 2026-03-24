"""Pipeline runner with per-asset-per-stage checkpointing.

Orchestrates pipeline stages, tracks progress in the database, handles failures
according to data source tier, and supports kill/restart with zero wasted work.
"""

import asyncio
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, date, datetime

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.config import settings
from src.db.models import Asset, PipelineAssetRun, PipelineRun
from src.pipeline.tiers import SourceCriticalError

logger = structlog.get_logger(__name__)

# Type alias for stage handler functions.
StageFunc = Callable[[AsyncSession, Asset], Awaitable[None]]


@dataclass(frozen=True)
class StageResult:
    """Result of running a single pipeline stage."""

    stage: str
    status: str  # "completed" | "partial" | "failed"
    assets_completed: int
    assets_failed: int
    assets_skipped: int
    duration_seconds: float


class PipelineRunner:
    """Pipeline runner with per-asset-per-stage checkpointing.

    Creates PipelineRun and PipelineAssetRun records to track progress.
    Completed stages are skipped on re-run (idempotent). Partial stages
    resume from the last incomplete asset. Failed assets do not block others.
    """

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory
        self._log = logger.bind(component="pipeline_runner")

    async def run_pipeline(
        self,
        run_date: date,
        stages: list[str] | None = None,
        stage_funcs: dict[str, StageFunc] | None = None,
        rerun_failed: bool = False,
    ) -> list[StageResult]:
        """Run all pipeline stages for a given date.

        Args:
            run_date: The date to run the pipeline for.
            stages: Optional list of stage names to run. Defaults to all stages.
            stage_funcs: Mapping of stage name to handler function.
            rerun_failed: If True, reprocess assets with status "failed".

        Returns:
            List of StageResult, one per stage executed.
        """
        if stages is None:
            stages = ["evaluate", "fetch", "analyze", "decide", "report"]

        if stage_funcs is None:
            stage_funcs = {}

        results: list[StageResult] = []
        for stage in stages:
            func = stage_funcs.get(stage)
            if func is None:
                self._log.warning("no_stage_func", stage=stage)
                continue
            result = await self.run_stage(run_date, stage, func, rerun_failed=rerun_failed)
            results.append(result)

        return results

    async def run_stage(
        self,
        run_date: date,
        stage: str,
        stage_func: StageFunc,
        rerun_failed: bool = False,
    ) -> StageResult:
        """Run a single pipeline stage with per-asset checkpointing.

        Args:
            run_date: The date to run the stage for.
            stage: Stage name (e.g., "fetch", "analyze").
            stage_func: Async callable that processes one asset.
            rerun_failed: If True, reprocess assets with status "failed".

        Returns:
            StageResult with counts and final status.
        """
        start_time = time.monotonic()
        log = self._log.bind(stage=stage, run_date=str(run_date))

        async with self._session_factory() as session:
            # Check for existing run
            existing = await session.execute(
                select(PipelineRun).where(
                    PipelineRun.run_date == run_date,
                    PipelineRun.stage == stage,
                )
            )
            pipeline_run = existing.scalar_one_or_none()

            if pipeline_run is not None and pipeline_run.status == "completed" and not rerun_failed:
                log.info("stage_already_completed")
                elapsed = time.monotonic() - start_time
                # Count existing asset runs for the result
                asset_runs_result = await session.execute(
                    select(PipelineAssetRun).where(
                        PipelineAssetRun.run_id == pipeline_run.id,
                    )
                )
                asset_runs = asset_runs_result.scalars().all()
                completed = sum(1 for ar in asset_runs if ar.status == "completed")
                failed = sum(1 for ar in asset_runs if ar.status == "failed")
                skipped = sum(1 for ar in asset_runs if ar.status == "skipped")
                return StageResult(
                    stage=stage,
                    status="completed",
                    assets_completed=completed,
                    assets_failed=failed,
                    assets_skipped=skipped,
                    duration_seconds=elapsed,
                )

            # Get active assets
            assets_result = await session.execute(
                select(Asset).where(Asset.is_active.is_(True))
            )
            active_assets = assets_result.scalars().all()

            if pipeline_run is None:
                # Create new run
                pipeline_run = PipelineRun(
                    run_date=run_date,
                    stage=stage,
                    status="running",
                    started_at=datetime.now(UTC),
                )
                session.add(pipeline_run)
                await session.flush()

                # Create asset run records
                for asset in active_assets:
                    asset_run = PipelineAssetRun(
                        run_id=pipeline_run.id,
                        asset_id=asset.id,
                        status="pending",
                    )
                    session.add(asset_run)
                await session.commit()
            else:
                # Existing run (partial/failed) - reuse
                pipeline_run.status = "running"
                pipeline_run.started_at = datetime.now(UTC)
                await session.commit()

            # Determine which assets to process
            asset_runs_result = await session.execute(
                select(PipelineAssetRun).where(
                    PipelineAssetRun.run_id == pipeline_run.id,
                )
            )
            all_asset_runs = asset_runs_result.scalars().all()
            asset_run_map = {ar.asset_id: ar for ar in all_asset_runs}

            assets_to_process: list[Asset] = []
            for asset in active_assets:
                ar = asset_run_map.get(asset.id)
                if ar is None:
                    continue
                if ar.status == "completed":
                    continue
                if ar.status == "failed" and not rerun_failed:
                    continue
                assets_to_process.append(asset)

            log.info("processing_assets", count=len(assets_to_process), total=len(active_assets))

        # Process each asset
        completed_count = 0
        failed_count = 0
        skipped_count = 0

        for asset in assets_to_process:
            async with self._session_factory() as session:
                # Reload asset run within this session
                ar_result = await session.execute(
                    select(PipelineAssetRun).where(
                        PipelineAssetRun.run_id == pipeline_run.id,
                        PipelineAssetRun.asset_id == asset.id,
                    )
                )
                asset_run = ar_result.scalar_one()
                asset_run.status = "running"
                asset_run.started_at = datetime.now(UTC)
                await session.commit()

                try:
                    timeout = self._get_timeout(stage)
                    await asyncio.wait_for(
                        stage_func(session, asset),
                        timeout=timeout,
                    )
                    asset_run.status = "completed"
                    asset_run.completed_at = datetime.now(UTC)
                    completed_count += 1
                    log.info("asset_completed", asset=asset.symbol)
                except SourceCriticalError as exc:
                    asset_run.status = "skipped"
                    asset_run.error_message = str(exc)
                    skipped_count += 1
                    log.warning("asset_skipped_critical", asset=asset.symbol, error=str(exc))
                except TimeoutError:
                    asset_run.status = "failed"
                    asset_run.error_message = f"Timeout after {self._get_timeout(stage)}s"
                    asset_run.retry_count = (asset_run.retry_count or 0) + 1
                    failed_count += 1
                    log.warning("asset_timeout", asset=asset.symbol)
                except Exception as exc:
                    asset_run.status = "failed"
                    asset_run.error_message = str(exc)
                    asset_run.retry_count = (asset_run.retry_count or 0) + 1
                    failed_count += 1
                    log.warning("asset_failed", asset=asset.symbol, error=str(exc))

                await session.commit()

        # Count previously completed assets (not processed this run)
        async with self._session_factory() as session:
            all_ar_result = await session.execute(
                select(PipelineAssetRun).where(
                    PipelineAssetRun.run_id == pipeline_run.id,
                )
            )
            all_runs = all_ar_result.scalars().all()
            total_completed = sum(1 for ar in all_runs if ar.status == "completed")
            total_failed = sum(1 for ar in all_runs if ar.status == "failed")
            total_skipped = sum(1 for ar in all_runs if ar.status == "skipped")

            # Update pipeline run status
            pr_result = await session.execute(
                select(PipelineRun).where(PipelineRun.id == pipeline_run.id)
            )
            pr = pr_result.scalar_one()

            if total_failed == 0 and total_skipped == 0:
                pr.status = "completed"
            elif total_completed == 0 and total_failed == len(all_runs):
                pr.status = "failed"
            else:
                pr.status = "partial" if (total_failed > 0 or total_skipped > 0) else "completed"

            pr.completed_at = datetime.now(UTC)
            await session.commit()

        elapsed = time.monotonic() - start_time
        final_status = "completed" if total_failed == 0 and total_skipped == 0 else "partial"

        result = StageResult(
            stage=stage,
            status=final_status,
            assets_completed=total_completed,
            assets_failed=total_failed,
            assets_skipped=total_skipped,
            duration_seconds=elapsed,
        )
        log.info("stage_complete", **{
            "status": result.status,
            "completed": result.assets_completed,
            "failed": result.assets_failed,
            "skipped": result.assets_skipped,
            "duration": f"{result.duration_seconds:.2f}s",
        })
        return result

    def _get_timeout(self, stage: str) -> int:
        """Return the per-asset timeout for a given stage.

        Args:
            stage: Stage name.

        Returns:
            Timeout in seconds.
        """
        timeouts: dict[str, int] = {
            "evaluate": settings.timeout_evaluate,
            "fetch": settings.timeout_fetch,
            "analyze": settings.timeout_analyze,
            "decide": settings.timeout_llm,
        }
        return timeouts.get(stage, 60)
