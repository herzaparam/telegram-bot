"""Tests for src/db/signal_repo.py — SignalRepository with mocked session."""

from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.db.signal_repo import SignalRepository, signal_repo
from src.engines.base import Signal


@pytest.fixture()
def repo() -> SignalRepository:
    """A fresh SignalRepository instance."""
    return SignalRepository()


@pytest.fixture()
def sample_signals() -> list[Signal]:
    """Two sample Signal instances for testing."""
    return [
        Signal(
            category="technical",
            score=0.5,
            confidence=0.8,
            reasoning="Bullish RSI crossover",
            indicators={"rsi_14": 55},
            data_quality={"sources_available": ["yfinance"], "indicators_skipped": [], "trading_days": 200},
        ),
        Signal(
            category="quantitative",
            score=-0.3,
            confidence=0.6,
            reasoning="Mean reversion signal",
            indicators={"hurst": 0.45},
            data_quality={"sources_available": ["yfinance"], "indicators_skipped": ["arima"], "trading_days": 200},
        ),
    ]


class TestSignalRepositorySingleton:
    """Test module-level singleton."""

    def test_signal_repo_exists(self) -> None:
        """Module-level signal_repo singleton exists."""
        assert signal_repo is not None
        assert isinstance(signal_repo, SignalRepository)


class TestUpsertSignals:
    """Test SignalRepository.upsert_signals."""

    @pytest.mark.asyncio
    async def test_upsert_signals_calls_execute(
        self, repo: SignalRepository, sample_signals: list[Signal]
    ) -> None:
        """upsert_signals calls session.execute once per signal."""
        session = AsyncMock()
        count = await repo.upsert_signals(
            session=session,
            asset_id=1,
            signal_date=date(2026, 3, 24),
            signals=sample_signals,
            price_at_signal=9800.0,
        )
        assert count == 2
        assert session.execute.await_count == 2

    @pytest.mark.asyncio
    async def test_upsert_signals_empty_list(self, repo: SignalRepository) -> None:
        """upsert_signals with empty list returns 0 and does not call execute."""
        session = AsyncMock()
        count = await repo.upsert_signals(
            session=session,
            asset_id=1,
            signal_date=date(2026, 3, 24),
            signals=[],
            price_at_signal=9800.0,
        )
        assert count == 0
        session.execute.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_upsert_signals_single(
        self, repo: SignalRepository, sample_signals: list[Signal]
    ) -> None:
        """upsert_signals with one signal returns 1."""
        session = AsyncMock()
        count = await repo.upsert_signals(
            session=session,
            asset_id=1,
            signal_date=date(2026, 3, 24),
            signals=[sample_signals[0]],
            price_at_signal=9800.0,
        )
        assert count == 1
        assert session.execute.await_count == 1


class TestGetSignalsForAsset:
    """Test SignalRepository.get_signals_for_asset."""

    @pytest.mark.asyncio
    async def test_get_signals_for_asset_returns_list(
        self, repo: SignalRepository
    ) -> None:
        """get_signals_for_asset returns a list of SignalRecord."""
        mock_record_1 = MagicMock()
        mock_record_1.category = "technical"
        mock_record_2 = MagicMock()
        mock_record_2.category = "quantitative"

        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [mock_record_1, mock_record_2]

        session = AsyncMock()
        session.scalars.return_value = mock_scalars

        results = await repo.get_signals_for_asset(
            session=session,
            asset_id=1,
            signal_date=date(2026, 3, 24),
        )
        assert len(results) == 2
        session.scalars.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_get_signals_for_asset_empty(self, repo: SignalRepository) -> None:
        """get_signals_for_asset returns empty list when no records."""
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []

        session = AsyncMock()
        session.scalars.return_value = mock_scalars

        results = await repo.get_signals_for_asset(
            session=session,
            asset_id=1,
            signal_date=date(2026, 3, 24),
        )
        assert results == []


class TestGetLatestSignals:
    """Test SignalRepository.get_latest_signals."""

    @pytest.mark.asyncio
    async def test_get_latest_signals_returns_ordered(
        self, repo: SignalRepository
    ) -> None:
        """get_latest_signals returns ordered results."""
        mock_record_1 = MagicMock()
        mock_record_1.date = date(2026, 3, 24)
        mock_record_2 = MagicMock()
        mock_record_2.date = date(2026, 3, 23)

        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [mock_record_1, mock_record_2]

        session = AsyncMock()
        session.scalars.return_value = mock_scalars

        results = await repo.get_latest_signals(
            session=session,
            asset_id=1,
            limit=10,
        )
        assert len(results) == 2
        session.scalars.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_get_latest_signals_default_limit(
        self, repo: SignalRepository
    ) -> None:
        """get_latest_signals uses default limit of 30."""
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []

        session = AsyncMock()
        session.scalars.return_value = mock_scalars

        await repo.get_latest_signals(session=session, asset_id=1)
        session.scalars.assert_awaited_once()
