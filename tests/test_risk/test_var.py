"""Tests for src.risk.var module."""

import numpy as np
import pandas as pd
import pytest

from src.risk.var import VaRResult, compute_historical_var


def test_var_values_negative(sample_price_series: pd.Series) -> None:
    """VaR values should be negative (losses)."""
    result = compute_historical_var(sample_price_series)
    assert result.daily_var_95 < 0
    assert result.daily_var_99 < 0


def test_var_99_worse_than_95(sample_price_series: pd.Series) -> None:
    """99% VaR should be more negative than 95% VaR."""
    result = compute_historical_var(sample_price_series)
    assert result.daily_var_99 <= result.daily_var_95
    assert result.weekly_var_99 <= result.weekly_var_95


def test_max_drawdown_negative(sample_price_series: pd.Series) -> None:
    """Max drawdown should be negative."""
    result = compute_historical_var(sample_price_series)
    assert result.max_drawdown < 0


def test_insufficient_data_raises() -> None:
    """Less than 60 data points raises ValueError."""
    short = pd.Series(np.random.default_rng(1).normal(0, 0.01, 30))
    with pytest.raises(ValueError, match="Insufficient data"):
        compute_historical_var(short)


def test_var_result_fields(sample_price_series: pd.Series) -> None:
    """VaRResult has all expected fields."""
    result = compute_historical_var(sample_price_series)
    assert isinstance(result, VaRResult)
    assert isinstance(result.daily_var_95, float)
    assert isinstance(result.weekly_var_95, float)
    assert isinstance(result.max_drawdown_start, str)
    assert isinstance(result.max_drawdown_end, str)


def test_weekly_var_worse_than_daily(sample_price_series: pd.Series) -> None:
    """Weekly VaR should be more negative than daily VaR (longer horizon = more risk)."""
    result = compute_historical_var(sample_price_series)
    assert result.weekly_var_95 <= result.daily_var_95
    assert result.weekly_var_99 <= result.daily_var_99


def test_exact_60_points_works() -> None:
    """Exactly 60 data points should not raise."""
    r = pd.Series(np.random.default_rng(7).normal(0, 0.01, 60))
    result = compute_historical_var(r)
    assert isinstance(result, VaRResult)
