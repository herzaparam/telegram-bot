"""Tests for staleness detection."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from src.data.staleness import StalenessResult, check_staleness


class TestCheckStaleness:
    """Tests for check_staleness function."""

    def test_idx_stock_stale_when_latest_before_last_trading_day(self) -> None:
        """IDX stock is stale when latest data is before last trading day."""
        # Wednesday check, latest data from Monday
        now = datetime(2026, 3, 18, 10, 0, tzinfo=timezone.utc)  # Wednesday
        latest = datetime(2026, 3, 16, 0, 0, tzinfo=timezone.utc)  # Monday
        result = check_staleness("BBCA.JK", "stock", latest, now=now)
        assert result.is_stale is True
        assert "last trading day" in result.reason

    def test_idx_stock_not_stale_when_latest_is_today(self) -> None:
        """IDX stock is not stale when latest data is from today (weekday)."""
        now = datetime(2026, 3, 18, 10, 0, tzinfo=timezone.utc)  # Wednesday
        latest = datetime(2026, 3, 18, 0, 0, tzinfo=timezone.utc)  # Same day
        result = check_staleness("BBCA.JK", "stock", latest, now=now)
        assert result.is_stale is False

    def test_idx_weekend_uses_friday(self) -> None:
        """On Saturday, last trading day for IDX is Friday."""
        now = datetime(2026, 3, 21, 10, 0, tzinfo=timezone.utc)  # Saturday
        latest = datetime(2026, 3, 20, 0, 0, tzinfo=timezone.utc)  # Friday
        result = check_staleness("BBCA.JK", "stock", latest, now=now)
        assert result.is_stale is False

    def test_idx_weekend_stale_if_no_friday(self) -> None:
        """On Saturday, IDX is stale if latest is before Friday."""
        now = datetime(2026, 3, 21, 10, 0, tzinfo=timezone.utc)  # Saturday
        latest = datetime(2026, 3, 19, 0, 0, tzinfo=timezone.utc)  # Thursday
        result = check_staleness("BBCA.JK", "stock", latest, now=now)
        assert result.is_stale is True

    def test_crypto_stale_when_older_than_24h(self) -> None:
        """Crypto is stale when latest data is more than 24h ago."""
        now = datetime(2026, 3, 18, 12, 0, tzinfo=timezone.utc)
        latest = now - timedelta(hours=25)
        result = check_staleness("BTC", "crypto", latest, now=now)
        assert result.is_stale is True
        assert "24 hours" in result.reason

    def test_crypto_not_stale_when_within_24h(self) -> None:
        """Crypto is not stale when latest data is within 24h."""
        now = datetime(2026, 3, 18, 12, 0, tzinfo=timezone.utc)
        latest = now - timedelta(hours=12)
        result = check_staleness("BTC", "crypto", latest, now=now)
        assert result.is_stale is False

    def test_no_data_at_all_stock(self) -> None:
        """No data at all returns stale=True for stock."""
        now = datetime(2026, 3, 18, 10, 0, tzinfo=timezone.utc)
        result = check_staleness("BBCA.JK", "stock", None, now=now)
        assert result.is_stale is True
        assert "No data at all" in result.reason

    def test_no_data_at_all_crypto(self) -> None:
        """No data at all returns stale=True for crypto."""
        now = datetime(2026, 3, 18, 10, 0, tzinfo=timezone.utc)
        result = check_staleness("BTC", "crypto", None, now=now)
        assert result.is_stale is True
        assert "No data at all" in result.reason
