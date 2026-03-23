"""Shared fixtures for data layer tests."""

from datetime import datetime, timezone

import pandas as pd
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


@pytest.fixture()
def mock_yfinance_df() -> pd.DataFrame:
    """A pandas DataFrame mimicking yfinance daily download output (5 rows)."""
    dates = pd.date_range("2026-03-16", periods=5, freq="B", tz="UTC")
    data = {
        "Open": [9500.0, 9550.0, 9650.0, 9750.0, 9800.0],
        "High": [9600.0, 9700.0, 9800.0, 9850.0, 9900.0],
        "Low": [9400.0, 9500.0, 9600.0, 9700.0, 9750.0],
        "Close": [9550.0, 9650.0, 9750.0, 9800.0, 9870.0],
        "Volume": [1_200_000, 1_500_000, 1_300_000, 1_100_000, 1_400_000],
    }
    return pd.DataFrame(data, index=dates)


@pytest.fixture()
def mock_ccxt_ohlcv() -> list[list[float]]:
    """List of 5 OHLCV candles as returned by ccxt fetch_ohlcv."""
    base_ts = int(datetime(2026, 3, 16, 0, 0, tzinfo=timezone.utc).timestamp() * 1000)
    day_ms = 86_400_000
    return [
        [base_ts + i * day_ms, 50000.0 + i * 100, 50500.0 + i * 100, 49500.0 + i * 100, 50200.0 + i * 100, 1000.0 + i * 10]
        for i in range(5)
    ]


@pytest.fixture()
def mock_coingecko_ohlc_response() -> list[list[float]]:
    """CoinGecko /coins/{id}/ohlc response: [[ts, open, high, low, close], ...]."""
    base_ts = int(datetime(2026, 3, 16, 0, 0, tzinfo=timezone.utc).timestamp() * 1000)
    day_ms = 86_400_000
    return [
        [base_ts + i * day_ms, 50000.0 + i * 100, 50500.0 + i * 100, 49500.0 + i * 100, 50200.0 + i * 100]
        for i in range(5)
    ]
