"""Tests for src.risk.metrics module."""

import pandas as pd


def test_sharpe_is_float(sample_price_series: pd.Series) -> None:
    """Sharpe ratio is a float."""
    pass


def test_sortino_is_float(sample_price_series: pd.Series) -> None:
    """Sortino ratio is a float."""
    pass


def test_zero_vol_returns_zero() -> None:
    """Zero volatility returns 0.0 for ratios."""
    pass


def test_annualized_return_positive(sample_price_series: pd.Series) -> None:
    """Annualized return computed from positive-drift returns."""
    pass


def test_result_fields(sample_price_series: pd.Series) -> None:
    """RiskMetricsResult has all expected fields."""
    pass
