"""Shared fixtures for portfolio risk module tests."""

import numpy as np
import pandas as pd
import pytest


@pytest.fixture()
def sample_price_series() -> pd.Series:
    """252 days of daily log returns for VaR / metrics tests."""
    rng = np.random.default_rng(42)
    returns = rng.normal(0.0005, 0.02, 252)
    index = pd.bdate_range("2025-01-02", periods=252, freq="B")
    return pd.Series(returns, index=index, name="returns")


@pytest.fixture()
def sample_assets() -> list[dict]:
    """Mixed stock + crypto asset list for concentration / stress tests."""
    return [
        {"symbol": "BBCA", "asset_type": "stock"},
        {"symbol": "BBRI", "asset_type": "stock"},
        {"symbol": "TLKM", "asset_type": "stock"},
        {"symbol": "BTC", "asset_type": "crypto"},
        {"symbol": "ETH", "asset_type": "crypto"},
    ]


@pytest.fixture()
def sample_price_data() -> dict[str, pd.Series]:
    """Dict of symbol -> pd.Series of 60 daily close prices (random walk from 100)."""
    rng = np.random.default_rng(99)
    symbols = ["BBCA", "BBRI", "TLKM", "BTC", "ETH"]
    index = pd.bdate_range("2025-10-01", periods=60, freq="B")
    data: dict[str, pd.Series] = {}
    for sym in symbols:
        returns = rng.normal(0.001, 0.015, 60)
        prices = 100.0 * np.cumprod(1 + returns)
        data[sym] = pd.Series(prices, index=index, name=sym)
    return data
