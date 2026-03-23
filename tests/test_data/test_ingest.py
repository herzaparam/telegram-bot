"""Tests for ingest stage function."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.data.base import OHLCVRow
from src.data.validation import ValidationResult


def _make_asset(asset_type: str = "stock", asset_id: int = 1) -> MagicMock:
    """Create a mock Asset object."""
    asset = MagicMock()
    asset.id = asset_id
    asset.asset_type = asset_type
    asset.symbol = "BBCA.JK" if asset_type == "stock" else "BTC"
    asset.yfinance_symbol = "BBCA.JK" if asset_type == "stock" else None
    asset.ccxt_symbol = "BTC/USDT" if asset_type == "crypto" else None
    return asset


def _make_rows(n: int = 3, source: str = "yfinance", asset_id: int = 1) -> list[OHLCVRow]:
    """Create n mock OHLCVRow objects."""
    base = datetime(2026, 3, 20, 0, 0, tzinfo=timezone.utc)
    return [
        OHLCVRow(
            time=base + timedelta(days=i),
            asset_id=asset_id,
            open=9500.0 + i * 50,
            high=9600.0 + i * 50,
            low=9400.0 + i * 50,
            close=9550.0 + i * 50,
            volume=1_000_000.0,
            source=source,
        )
        for i in range(n)
    ]


class TestIngestStage:
    """Tests for ingest_stage function."""

    @pytest.mark.asyncio
    async def test_ingest_stock_asset(self) -> None:
        """ingest_stage fetches, validates, upserts for stock asset."""
        asset = _make_asset("stock")
        rows = _make_rows(3)
        mock_session = AsyncMock()
        mock_conn = AsyncMock()

        with (
            patch("src.data.ingest.IDXStockFetcher") as MockFetcher,
            patch("src.data.ingest.asyncpg.connect", return_value=mock_conn),
            patch("src.data.ingest.get_latest_date", return_value=datetime(2026, 3, 19, 0, 0, tzinfo=timezone.utc)),
            patch("src.data.ingest.validate_rows", return_value=ValidationResult(valid=rows, rejected=[])),
            patch("src.data.ingest.upsert_prices", return_value=3),
            patch("src.data.ingest.check_staleness"),
            patch("src.data.ingest._read_backoff_state", return_value=(1.0, 0)),
            patch("src.data.ingest._update_backoff_success"),
            patch("src.data.ingest._should_weekly_refresh", return_value=False),
            patch("src.data.ingest.settings") as mock_settings,
        ):
            mock_settings.database_url = "postgresql+asyncpg://test:test@localhost/test"
            fetcher_instance = AsyncMock()
            fetcher_instance.fetch = AsyncMock(return_value=rows)
            fetcher_instance.source_name = "yfinance"
            MockFetcher.return_value = fetcher_instance

            from src.data.ingest import ingest_stage

            await ingest_stage(mock_session, asset)

            fetcher_instance.fetch.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_ingest_crypto_asset(self) -> None:
        """ingest_stage for crypto calls CryptoFetcher and also fetches hourly."""
        asset = _make_asset("crypto", asset_id=10)
        rows = _make_rows(3, source="ccxt", asset_id=10)
        hourly_rows = _make_rows(3, source="ccxt", asset_id=10)
        mock_session = AsyncMock()
        mock_conn = AsyncMock()

        with (
            patch("src.data.ingest.CryptoFetcher") as MockFetcher,
            patch("src.data.ingest.asyncpg.connect", return_value=mock_conn),
            patch("src.data.ingest.get_latest_date", return_value=datetime(2026, 3, 19, 0, 0, tzinfo=timezone.utc)),
            patch("src.data.ingest.validate_rows", return_value=ValidationResult(valid=rows, rejected=[])),
            patch("src.data.ingest.upsert_prices", return_value=3),
            patch("src.data.ingest.check_staleness"),
            patch("src.data.ingest._read_backoff_state", return_value=(1.0, 0)),
            patch("src.data.ingest._update_backoff_success"),
            patch("src.data.ingest._should_weekly_refresh", return_value=False),
            patch("src.data.ingest.settings") as mock_settings,
        ):
            mock_settings.database_url = "postgresql+asyncpg://test:test@localhost/test"
            fetcher_instance = AsyncMock()
            fetcher_instance.fetch = AsyncMock(return_value=rows)
            fetcher_instance.fetch_hourly = AsyncMock(return_value=hourly_rows)
            fetcher_instance.source_name = "ccxt"
            MockFetcher.return_value = fetcher_instance

            from src.data.ingest import ingest_stage

            await ingest_stage(mock_session, asset)

            fetcher_instance.fetch.assert_awaited_once()
            fetcher_instance.fetch_hourly.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_ingest_delta_fetch(self) -> None:
        """When get_latest_date returns a date, fetch starts from next day."""
        asset = _make_asset("stock")
        rows = _make_rows(1)
        mock_session = AsyncMock()
        mock_conn = AsyncMock()

        with (
            patch("src.data.ingest.IDXStockFetcher") as MockFetcher,
            patch("src.data.ingest.asyncpg.connect", return_value=mock_conn),
            patch("src.data.ingest.get_latest_date", return_value=datetime(2026, 3, 20, 0, 0, tzinfo=timezone.utc)),
            patch("src.data.ingest.validate_rows", return_value=ValidationResult(valid=rows, rejected=[])),
            patch("src.data.ingest.upsert_prices", return_value=1),
            patch("src.data.ingest.check_staleness"),
            patch("src.data.ingest._read_backoff_state", return_value=(1.0, 0)),
            patch("src.data.ingest._update_backoff_success"),
            patch("src.data.ingest._should_weekly_refresh", return_value=False),
            patch("src.data.ingest.settings") as mock_settings,
        ):
            mock_settings.database_url = "postgresql+asyncpg://test:test@localhost/test"
            fetcher_instance = AsyncMock()
            fetcher_instance.fetch = AsyncMock(return_value=rows)
            fetcher_instance.source_name = "yfinance"
            MockFetcher.return_value = fetcher_instance

            from src.data.ingest import ingest_stage

            await ingest_stage(mock_session, asset)

            # Verify start date is latest + 1 day
            call_args = fetcher_instance.fetch.call_args
            assert call_args[1]["start"] == date(2026, 3, 21) or call_args[0][2] == date(2026, 3, 21)

    @pytest.mark.asyncio
    async def test_ingest_auto_backfill_when_no_data(self) -> None:
        """When get_latest_date returns None, fetch starts from 2 years ago."""
        asset = _make_asset("stock")
        rows = _make_rows(1)
        mock_session = AsyncMock()
        mock_conn = AsyncMock()

        with (
            patch("src.data.ingest.IDXStockFetcher") as MockFetcher,
            patch("src.data.ingest.asyncpg.connect", return_value=mock_conn),
            patch("src.data.ingest.get_latest_date", return_value=None),
            patch("src.data.ingest.validate_rows", return_value=ValidationResult(valid=rows, rejected=[])),
            patch("src.data.ingest.upsert_prices", return_value=1),
            patch("src.data.ingest.check_staleness"),
            patch("src.data.ingest._read_backoff_state", return_value=(1.0, 0)),
            patch("src.data.ingest._update_backoff_success"),
            patch("src.data.ingest._should_weekly_refresh", return_value=False),
            patch("src.data.ingest.settings") as mock_settings,
        ):
            mock_settings.database_url = "postgresql+asyncpg://test:test@localhost/test"
            fetcher_instance = AsyncMock()
            fetcher_instance.fetch = AsyncMock(return_value=rows)
            fetcher_instance.source_name = "yfinance"
            MockFetcher.return_value = fetcher_instance

            from src.data.ingest import ingest_stage

            await ingest_stage(mock_session, asset)

            # Verify start date is approximately 2 years ago
            call_args = fetcher_instance.fetch.call_args
            start_arg = call_args[1].get("start") or call_args[0][2]
            today = date.today()
            expected_approx = today - timedelta(days=730)
            assert abs((start_arg - expected_approx).days) <= 2

    @pytest.mark.asyncio
    async def test_ingest_raises_source_critical_on_failure(self) -> None:
        """ingest_stage raises SourceCriticalError when fetcher fails."""
        from src.pipeline.tiers import SourceCriticalError

        asset = _make_asset("stock")
        mock_session = AsyncMock()
        mock_conn = AsyncMock()

        with (
            patch("src.data.ingest.IDXStockFetcher") as MockFetcher,
            patch("src.data.ingest.asyncpg.connect", return_value=mock_conn),
            patch("src.data.ingest.get_latest_date", return_value=datetime(2026, 3, 19, 0, 0, tzinfo=timezone.utc)),
            patch("src.data.ingest._read_backoff_state", return_value=(1.0, 0)),
            patch("src.data.ingest._update_backoff_failure"),
            patch("src.data.ingest._should_weekly_refresh", return_value=False),
            patch("src.data.ingest.settings") as mock_settings,
        ):
            mock_settings.database_url = "postgresql+asyncpg://test:test@localhost/test"
            fetcher_instance = AsyncMock()
            fetcher_instance.fetch = AsyncMock(side_effect=Exception("API down"))
            fetcher_instance.source_name = "yfinance"
            MockFetcher.return_value = fetcher_instance

            from src.data.ingest import ingest_stage

            with pytest.raises(SourceCriticalError):
                await ingest_stage(mock_session, asset)

    @pytest.mark.asyncio
    async def test_ingest_skips_when_up_to_date(self) -> None:
        """ingest_stage skips when start > end (all data up to date)."""
        asset = _make_asset("stock")
        mock_session = AsyncMock()
        mock_conn = AsyncMock()

        with (
            patch("src.data.ingest.IDXStockFetcher") as MockFetcher,
            patch("src.data.ingest.asyncpg.connect", return_value=mock_conn),
            patch("src.data.ingest.get_latest_date", return_value=datetime(2030, 1, 1, 0, 0, tzinfo=timezone.utc)),
            patch("src.data.ingest._read_backoff_state", return_value=(1.0, 0)),
            patch("src.data.ingest._should_weekly_refresh", return_value=False),
            patch("src.data.ingest.settings") as mock_settings,
        ):
            mock_settings.database_url = "postgresql+asyncpg://test:test@localhost/test"
            fetcher_instance = AsyncMock()
            fetcher_instance.source_name = "yfinance"
            MockFetcher.return_value = fetcher_instance

            from src.data.ingest import ingest_stage

            await ingest_stage(mock_session, asset)

            # Fetcher should NOT have been called
            fetcher_instance.fetch.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_weekly_refetch_uses_30_day_window(self) -> None:
        """When weekly refresh is True, fetch starts from today - 30 days."""
        asset = _make_asset("stock")
        rows = _make_rows(3)
        mock_session = AsyncMock()
        mock_conn = AsyncMock()

        with (
            patch("src.data.ingest.IDXStockFetcher") as MockFetcher,
            patch("src.data.ingest.asyncpg.connect", return_value=mock_conn),
            patch("src.data.ingest.get_latest_date", return_value=datetime(2026, 3, 22, 0, 0, tzinfo=timezone.utc)),
            patch("src.data.ingest.validate_rows", return_value=ValidationResult(valid=rows, rejected=[])),
            patch("src.data.ingest.upsert_prices", return_value=3),
            patch("src.data.ingest.check_staleness"),
            patch("src.data.ingest._read_backoff_state", return_value=(1.0, 0)),
            patch("src.data.ingest._update_backoff_success"),
            patch("src.data.ingest._should_weekly_refresh", return_value=True),
            patch("src.data.ingest.settings") as mock_settings,
        ):
            mock_settings.database_url = "postgresql+asyncpg://test:test@localhost/test"
            fetcher_instance = AsyncMock()
            fetcher_instance.fetch = AsyncMock(return_value=rows)
            fetcher_instance.source_name = "yfinance"
            MockFetcher.return_value = fetcher_instance

            from src.data.ingest import ingest_stage

            await ingest_stage(mock_session, asset)

            call_args = fetcher_instance.fetch.call_args
            start_arg = call_args[1].get("start") or call_args[0][2]
            today = date.today()
            expected = today - timedelta(days=30)
            assert start_arg == expected

    @pytest.mark.asyncio
    async def test_normal_delta_no_weekly_refetch(self) -> None:
        """When weekly refresh is False, fetch starts from latest + 1 day."""
        asset = _make_asset("stock")
        rows = _make_rows(1)
        mock_session = AsyncMock()
        mock_conn = AsyncMock()

        with (
            patch("src.data.ingest.IDXStockFetcher") as MockFetcher,
            patch("src.data.ingest.asyncpg.connect", return_value=mock_conn),
            patch("src.data.ingest.get_latest_date", return_value=datetime(2026, 3, 20, 0, 0, tzinfo=timezone.utc)),
            patch("src.data.ingest.validate_rows", return_value=ValidationResult(valid=rows, rejected=[])),
            patch("src.data.ingest.upsert_prices", return_value=1),
            patch("src.data.ingest.check_staleness"),
            patch("src.data.ingest._read_backoff_state", return_value=(1.0, 0)),
            patch("src.data.ingest._update_backoff_success"),
            patch("src.data.ingest._should_weekly_refresh", return_value=False),
            patch("src.data.ingest.settings") as mock_settings,
        ):
            mock_settings.database_url = "postgresql+asyncpg://test:test@localhost/test"
            fetcher_instance = AsyncMock()
            fetcher_instance.fetch = AsyncMock(return_value=rows)
            fetcher_instance.source_name = "yfinance"
            MockFetcher.return_value = fetcher_instance

            from src.data.ingest import ingest_stage

            await ingest_stage(mock_session, asset)

            call_args = fetcher_instance.fetch.call_args
            start_arg = call_args[1].get("start") or call_args[0][2]
            assert start_arg == date(2026, 3, 21)

    @pytest.mark.asyncio
    async def test_backoff_state_read_and_sleep(self) -> None:
        """Reads BackoffState before fetch; sleeps if delay > 1.0."""
        asset = _make_asset("stock")
        rows = _make_rows(1)
        mock_session = AsyncMock()
        mock_conn = AsyncMock()

        with (
            patch("src.data.ingest.IDXStockFetcher") as MockFetcher,
            patch("src.data.ingest.asyncpg.connect", return_value=mock_conn),
            patch("src.data.ingest.get_latest_date", return_value=datetime(2026, 3, 19, 0, 0, tzinfo=timezone.utc)),
            patch("src.data.ingest.validate_rows", return_value=ValidationResult(valid=rows, rejected=[])),
            patch("src.data.ingest.upsert_prices", return_value=1),
            patch("src.data.ingest.check_staleness"),
            patch("src.data.ingest._read_backoff_state", return_value=(5.0, 3)),
            patch("src.data.ingest._update_backoff_success"),
            patch("src.data.ingest._should_weekly_refresh", return_value=False),
            patch("src.data.ingest.settings") as mock_settings,
            patch("src.data.ingest.asyncio.sleep") as mock_sleep,
        ):
            mock_settings.database_url = "postgresql+asyncpg://test:test@localhost/test"
            mock_sleep.return_value = None
            fetcher_instance = AsyncMock()
            fetcher_instance.fetch = AsyncMock(return_value=rows)
            fetcher_instance.source_name = "yfinance"
            MockFetcher.return_value = fetcher_instance

            from src.data.ingest import ingest_stage

            await ingest_stage(mock_session, asset)

            mock_sleep.assert_awaited_once_with(5.0)

    @pytest.mark.asyncio
    async def test_backoff_reset_on_success(self) -> None:
        """After successful fetch, _update_backoff_success is called."""
        asset = _make_asset("stock")
        rows = _make_rows(1)
        mock_session = AsyncMock()
        mock_conn = AsyncMock()

        with (
            patch("src.data.ingest.IDXStockFetcher") as MockFetcher,
            patch("src.data.ingest.asyncpg.connect", return_value=mock_conn),
            patch("src.data.ingest.get_latest_date", return_value=datetime(2026, 3, 19, 0, 0, tzinfo=timezone.utc)),
            patch("src.data.ingest.validate_rows", return_value=ValidationResult(valid=rows, rejected=[])),
            patch("src.data.ingest.upsert_prices", return_value=1),
            patch("src.data.ingest.check_staleness"),
            patch("src.data.ingest._read_backoff_state", return_value=(1.0, 0)),
            patch("src.data.ingest._update_backoff_success") as mock_success,
            patch("src.data.ingest._should_weekly_refresh", return_value=False),
            patch("src.data.ingest.settings") as mock_settings,
        ):
            mock_settings.database_url = "postgresql+asyncpg://test:test@localhost/test"
            fetcher_instance = AsyncMock()
            fetcher_instance.fetch = AsyncMock(return_value=rows)
            fetcher_instance.source_name = "yfinance"
            MockFetcher.return_value = fetcher_instance

            from src.data.ingest import ingest_stage

            await ingest_stage(mock_session, asset)

            mock_success.assert_awaited_once_with(mock_session, "yfinance")

    @pytest.mark.asyncio
    async def test_backoff_increment_on_failure(self) -> None:
        """When fetcher fails, _update_backoff_failure is called."""
        asset = _make_asset("stock")
        mock_session = AsyncMock()
        mock_conn = AsyncMock()

        with (
            patch("src.data.ingest.IDXStockFetcher") as MockFetcher,
            patch("src.data.ingest.asyncpg.connect", return_value=mock_conn),
            patch("src.data.ingest.get_latest_date", return_value=datetime(2026, 3, 19, 0, 0, tzinfo=timezone.utc)),
            patch("src.data.ingest._read_backoff_state", return_value=(1.0, 0)),
            patch("src.data.ingest._update_backoff_failure") as mock_failure,
            patch("src.data.ingest._should_weekly_refresh", return_value=False),
            patch("src.data.ingest.settings") as mock_settings,
        ):
            mock_settings.database_url = "postgresql+asyncpg://test:test@localhost/test"
            fetcher_instance = AsyncMock()
            fetcher_instance.fetch = AsyncMock(side_effect=Exception("API down"))
            fetcher_instance.source_name = "yfinance"
            MockFetcher.return_value = fetcher_instance

            from src.data.ingest import ingest_stage
            from src.pipeline.tiers import SourceCriticalError

            with pytest.raises(SourceCriticalError):
                await ingest_stage(mock_session, asset)

            mock_failure.assert_awaited_once_with(mock_session, "yfinance")

    def test_backfill_cli_parses_args(self) -> None:
        """backfill CLI parses --from and --to arguments correctly."""
        from src.data.backfill import parse_args

        args = parse_args(["--from", "2024-01-01", "--to", "2026-03-23"])
        assert args.from_date == date(2024, 1, 1)
        assert args.to_date == date(2026, 3, 23)

    def test_backfill_cli_defaults(self) -> None:
        """backfill CLI defaults to 2 years ago when no --from given."""
        from src.data.backfill import parse_args

        args = parse_args([])
        today = date.today()
        expected = today - timedelta(days=730)
        assert abs((args.from_date - expected).days) <= 1
        assert args.to_date == today
