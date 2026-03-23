"""Shared fixtures for data layer tests."""

from datetime import datetime, timezone

import pytest

from src.data.base import OHLCVRow


@pytest.fixture()
def sample_ohlcv_rows() -> list[OHLCVRow]:
    """Three valid OHLCV rows for BBCA.JK (asset_id=1)."""
    base = datetime(2026, 3, 20, 0, 0, tzinfo=timezone.utc)
    return [
        OHLCVRow(
            time=base.replace(day=20),
            asset_id=1,
            open=9500.0,
            high=9600.0,
            low=9400.0,
            close=9550.0,
            volume=1_200_000.0,
            source="yfinance",
        ),
        OHLCVRow(
            time=base.replace(day=21),
            asset_id=1,
            open=9550.0,
            high=9700.0,
            low=9500.0,
            close=9650.0,
            volume=1_500_000.0,
            source="yfinance",
        ),
        OHLCVRow(
            time=base.replace(day=22),
            asset_id=1,
            open=9650.0,
            high=9800.0,
            low=9600.0,
            close=9750.0,
            volume=1_300_000.0,
            source="yfinance",
        ),
    ]


@pytest.fixture()
def five_ohlcv_rows(sample_ohlcv_rows: list[OHLCVRow]) -> list[OHLCVRow]:
    """Five valid OHLCV rows for validation tests."""
    base = datetime(2026, 3, 23, 0, 0, tzinfo=timezone.utc)
    extra = [
        OHLCVRow(
            time=base.replace(day=23),
            asset_id=1,
            open=9750.0,
            high=9850.0,
            low=9700.0,
            close=9800.0,
            volume=1_100_000.0,
            source="yfinance",
        ),
        OHLCVRow(
            time=base.replace(day=24),
            asset_id=1,
            open=9800.0,
            high=9900.0,
            low=9750.0,
            close=9870.0,
            volume=1_400_000.0,
            source="yfinance",
        ),
    ]
    return sample_ohlcv_rows + extra
