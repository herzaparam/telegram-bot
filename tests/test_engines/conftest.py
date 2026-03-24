"""Shared fixtures for engine tests."""

import numpy as np
import pandas as pd
import pytest


@pytest.fixture()
def sample_price_df_200() -> pd.DataFrame:
    """A pandas DataFrame with 200 rows of synthetic OHLCV data.

    Simulates realistic price movement with a random walk (1-2% daily change).
    Index is business day frequency datetime.
    """
    rng = np.random.default_rng(42)
    n = 200
    dates = pd.bdate_range("2025-06-01", periods=n, freq="B")

    # Random walk for close prices starting at 10000
    returns = rng.normal(0.0005, 0.015, size=n)
    close = 10000.0 * np.cumprod(1 + returns)

    # Derive OHLCV from close
    high = close * (1 + rng.uniform(0.001, 0.02, size=n))
    low = close * (1 - rng.uniform(0.001, 0.02, size=n))
    open_ = low + rng.uniform(0.3, 0.7, size=n) * (high - low)
    volume = rng.uniform(500_000, 5_000_000, size=n)

    return pd.DataFrame(
        {
            "open": open_,
            "high": high,
            "low": low,
            "close": close,
            "volume": volume,
        },
        index=dates,
    )


@pytest.fixture()
def sample_price_df_50() -> pd.DataFrame:
    """A pandas DataFrame with 50 rows of synthetic OHLCV data.

    Sufficient for basic indicators (RSI, MACD) but insufficient for ARIMA/Hurst.
    """
    rng = np.random.default_rng(123)
    n = 50
    dates = pd.bdate_range("2025-12-01", periods=n, freq="B")

    returns = rng.normal(0.0003, 0.012, size=n)
    close = 10000.0 * np.cumprod(1 + returns)

    high = close * (1 + rng.uniform(0.001, 0.015, size=n))
    low = close * (1 - rng.uniform(0.001, 0.015, size=n))
    open_ = low + rng.uniform(0.3, 0.7, size=n) * (high - low)
    volume = rng.uniform(500_000, 3_000_000, size=n)

    return pd.DataFrame(
        {
            "open": open_,
            "high": high,
            "low": low,
            "close": close,
            "volume": volume,
        },
        index=dates,
    )


@pytest.fixture()
def sample_price_df_10() -> pd.DataFrame:
    """A pandas DataFrame with 10 rows of synthetic OHLCV data.

    Insufficient for most technical indicators.
    """
    rng = np.random.default_rng(999)
    n = 10
    dates = pd.bdate_range("2026-03-01", periods=n, freq="B")

    returns = rng.normal(0.0, 0.01, size=n)
    close = 10000.0 * np.cumprod(1 + returns)

    high = close * (1 + rng.uniform(0.002, 0.01, size=n))
    low = close * (1 - rng.uniform(0.002, 0.01, size=n))
    open_ = low + rng.uniform(0.4, 0.6, size=n) * (high - low)
    volume = rng.uniform(1_000_000, 2_000_000, size=n)

    return pd.DataFrame(
        {
            "open": open_,
            "high": high,
            "low": low,
            "close": close,
            "volume": volume,
        },
        index=dates,
    )


@pytest.fixture()
def empty_price_df() -> pd.DataFrame:
    """An empty DataFrame with correct OHLCV columns."""
    return pd.DataFrame(
        columns=["open", "high", "low", "close", "volume"],
        dtype=float,
    )
