"""Tests for src.risk.var module."""

import pandas as pd


def test_var_values_negative(sample_price_series: pd.Series) -> None:
    """VaR values should be negative (losses)."""
    pass


def test_var_99_worse_than_95(sample_price_series: pd.Series) -> None:
    """99% VaR should be more negative than 95% VaR."""
    pass


def test_max_drawdown_negative(sample_price_series: pd.Series) -> None:
    """Max drawdown should be negative."""
    pass


def test_insufficient_data_raises() -> None:
    """Less than 60 data points raises ValueError."""
    pass


def test_var_result_fields(sample_price_series: pd.Series) -> None:
    """VaRResult has all expected fields."""
    pass
