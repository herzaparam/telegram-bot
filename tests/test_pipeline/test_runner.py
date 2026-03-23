"""Tests for pipeline runner with per-asset-per-stage checkpointing."""

import asyncio
import uuid
from datetime import date, datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.db.models import Asset, Base, PipelineAssetRun, PipelineRun
from src.pipeline.runner import PipelineRunner, StageResult
from src.pipeline.tiers import SourceCriticalError


@pytest.fixture()
async def async_engine():
    """Create an async in-memory SQLite engine for tests."""
    engine = create_async_engine("sqlite+aiosqlite://", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture()
async def session_factory(async_engine):
    """Create an async session factory bound to the test engine."""
    factory = async_sessionmaker(async_engine, expire_on_commit=False)
    return factory


@pytest.fixture()
async def seeded_session_factory(session_factory):
    """Seed the database with test assets."""
    async with session_factory() as session:
        assets = [
            Asset(
                id=1,
                symbol="BTC",
                name="Bitcoin",
                asset_type="crypto",
                is_active=True,
            ),
            Asset(
                id=2,
                symbol="ETH",
                name="Ethereum",
                asset_type="crypto",
                is_active=True,
            ),
            Asset(
                id=3,
                symbol="BBCA",
                name="Bank Central Asia",
                asset_type="stock",
                is_active=True,
            ),
        ]
        session.add_all(assets)
        await session.commit()
    return session_factory


@pytest.fixture()
def runner(seeded_session_factory):
    """Create a PipelineRunner with the test session factory."""
    return PipelineRunner(seeded_session_factory)


@pytest.fixture()
def run_date():
    return date(2026, 3, 23)


@pytest.fixture()
def success_stage_func():
    """A stage function that always succeeds."""

    async def _func(session: AsyncSession, asset: Asset) -> None:
        pass

    return _func


@pytest.fixture()
def failing_stage_func():
    """A stage function that fails for asset_id=2."""

    async def _func(session: AsyncSession, asset: Asset) -> None:
        if asset.id == 2:
            raise RuntimeError("API unavailable")

    return _func


class TestRunStageCreatesRecords:
    """run_stage creates PipelineRun and PipelineAssetRun records."""

    async def test_creates_pipeline_run_with_running_status(
        self, runner, run_date, success_stage_func, seeded_session_factory
    ):
        await runner.run_stage(run_date, "fetch", success_stage_func)

        async with seeded_session_factory() as session:
            result = await session.execute(
                select(PipelineRun).where(
                    PipelineRun.run_date == run_date,
                    PipelineRun.stage == "fetch",
                )
            )
            run = result.scalar_one()
            assert run.status == "completed"
            assert run.started_at is not None

    async def test_creates_asset_run_records(
        self, runner, run_date, success_stage_func, seeded_session_factory
    ):
        await runner.run_stage(run_date, "fetch", success_stage_func)

        async with seeded_session_factory() as session:
            result = await session.execute(select(PipelineAssetRun))
            asset_runs = result.scalars().all()
            assert len(asset_runs) == 3
            assert all(ar.status == "completed" for ar in asset_runs)


class TestRunStageCompletion:
    """PipelineRun status reflects actual outcome."""

    async def test_all_success_means_completed(
        self, runner, run_date, success_stage_func, seeded_session_factory
    ):
        result = await runner.run_stage(run_date, "fetch", success_stage_func)
        assert result.status == "completed"
        assert result.assets_completed == 3
        assert result.assets_failed == 0

    async def test_some_failures_means_partial(
        self, runner, run_date, failing_stage_func, seeded_session_factory
    ):
        result = await runner.run_stage(run_date, "fetch", failing_stage_func)
        assert result.status == "partial"
        assert result.assets_completed == 2
        assert result.assets_failed == 1


class TestIdempotency:
    """Re-running a completed stage is a no-op."""

    async def test_completed_stage_is_noop(
        self, runner, run_date, success_stage_func, seeded_session_factory
    ):
        result1 = await runner.run_stage(run_date, "fetch", success_stage_func)
        assert result1.status == "completed"

        # Second run should be a no-op
        call_count = 0
        original_func = success_stage_func

        async def counting_func(session, asset):
            nonlocal call_count
            call_count += 1
            await original_func(session, asset)

        result2 = await runner.run_stage(run_date, "fetch", counting_func)
        assert result2.status == "completed"
        assert call_count == 0  # Stage func was NOT called


class TestPartialResume:
    """Partial stage resumes only incomplete assets."""

    async def test_resumes_only_incomplete_assets(
        self, runner, run_date, seeded_session_factory
    ):
        # First run: one asset fails
        async def fail_asset_2(session: AsyncSession, asset: Asset) -> None:
            if asset.id == 2:
                raise RuntimeError("temporary failure")

        result1 = await runner.run_stage(run_date, "fetch", fail_asset_2)
        assert result1.status == "partial"

        # Second run with rerun_failed: only failed asset is reprocessed
        processed_ids: list[int] = []

        async def track_func(session: AsyncSession, asset: Asset) -> None:
            processed_ids.append(asset.id)

        result2 = await runner.run_stage(
            run_date, "fetch", track_func, rerun_failed=True
        )
        assert result2.status == "completed"
        assert processed_ids == [2]  # Only the previously failed asset


class TestFailureIsolation:
    """One asset failing does not block others."""

    async def test_other_assets_still_complete(
        self, runner, run_date, failing_stage_func, seeded_session_factory
    ):
        result = await runner.run_stage(run_date, "fetch", failing_stage_func)
        assert result.assets_completed == 2
        assert result.assets_failed == 1

        async with seeded_session_factory() as session:
            # Check that the failed asset has error_message
            failed = await session.execute(
                select(PipelineAssetRun).where(
                    PipelineAssetRun.asset_id == 2,
                )
            )
            failed_run = failed.scalar_one()
            assert failed_run.status == "failed"
            assert "API unavailable" in failed_run.error_message


class TestPerAssetTimeout:
    """Per-asset timeout prevents hangs."""

    async def test_timeout_marks_asset_failed(
        self, runner, run_date, seeded_session_factory
    ):
        async def slow_func(session: AsyncSession, asset: Asset) -> None:
            if asset.id == 1:
                await asyncio.sleep(10)  # Will exceed timeout

        # Override timeout to 0.1s for fast test
        with patch.object(runner, "_get_timeout", return_value=0.1):
            result = await runner.run_stage(run_date, "fetch", slow_func)

        assert result.assets_failed >= 1

        async with seeded_session_factory() as session:
            timed_out = await session.execute(
                select(PipelineAssetRun).where(
                    PipelineAssetRun.asset_id == 1,
                )
            )
            ar = timed_out.scalar_one()
            assert ar.status == "failed"
            assert "timeout" in ar.error_message.lower()


class TestSourceCriticalErrorHandling:
    """SourceCriticalError marks asset as skipped."""

    async def test_critical_error_skips_asset(
        self, runner, run_date, seeded_session_factory
    ):
        async def critical_fail(session: AsyncSession, asset: Asset) -> None:
            if asset.id == 1:
                raise SourceCriticalError("Critical source price_ohlcv failed")

        result = await runner.run_stage(run_date, "fetch", critical_fail)
        assert result.assets_skipped == 1

        async with seeded_session_factory() as session:
            skipped = await session.execute(
                select(PipelineAssetRun).where(
                    PipelineAssetRun.asset_id == 1,
                )
            )
            ar = skipped.scalar_one()
            assert ar.status == "skipped"


class TestRerunFailed:
    """--rerun-failed reprocesses failed assets."""

    async def test_rerun_failed_reprocesses(
        self, runner, run_date, seeded_session_factory
    ):
        # First run: asset 2 fails
        async def fail_once(session: AsyncSession, asset: Asset) -> None:
            if asset.id == 2:
                raise RuntimeError("transient")

        await runner.run_stage(run_date, "fetch", fail_once)

        # Rerun with rerun_failed flag
        async def succeed(session: AsyncSession, asset: Asset) -> None:
            pass

        result = await runner.run_stage(
            run_date, "fetch", succeed, rerun_failed=True
        )
        assert result.status == "completed"
        assert result.assets_completed == 3


class TestCLIArgParsing:
    """CLI argument parsing tests."""

    def test_stage_flag_parsed(self):
        from src.pipeline.main import build_parser

        parser = build_parser()
        args = parser.parse_args(["--stage", "fetch"])
        assert args.stage == "fetch"

    def test_rerun_failed_flag_parsed(self):
        from src.pipeline.main import build_parser

        parser = build_parser()
        args = parser.parse_args(["--rerun-failed"])
        assert args.rerun_failed is True

    def test_date_flag_parsed(self):
        from src.pipeline.main import build_parser

        parser = build_parser()
        args = parser.parse_args(["--date", "2026-03-23"])
        assert args.date == "2026-03-23"

    def test_default_date_is_none(self):
        from src.pipeline.main import build_parser

        parser = build_parser()
        args = parser.parse_args([])
        assert args.date is None
