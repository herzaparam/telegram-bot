"""Tests for src.risk.metrics module."""

import numpy as np
import pandas as pd

from src.risk.metrics import RiskMetricsResult, compute_risk_metrics


def test_sharpe_is_float(sample_price_series: pd.Series) -> None:
    """Sharpe ratio is a float."""
    result = compute_risk_metrics(sample_price_series)
    assert isinstance(result.sharpe_ratio, float)


def test_sortino_is_float(sample_price_series: pd.Series) -> None:
    """Sortino ratio is a float."""
    result = compute_risk_metrics(sample_price_series)
    assert isinstance(result.sortino_ratio, float)


def test_zero_vol_returns_zero() -> None:
    """Zero volatility returns 0.0 for ratios."""
    flat = pd.Series([0.0] * 100)
    result = compute_risk_metrics(flat)
    assert result.sharpe_ratio == 0.0
    assert result.sortino_ratio == 0.0


def test_annualized_return_positive() -> None:
    """Annualized return computed from positive-drift returns is positive."""
    # Use a deterministic positive-drift series
    returns = pd.Series([0.005] * 252)
    result = compute_risk_metrics(returns)
    assert result.annualized_return > 0


def test_result_fields(sample_price_series: pd.Series) -> None:
    """RiskMetricsResult has all expected fields."""
    result = compute_risk_metrics(sample_price_series)
    assert isinstance(result, RiskMetricsResult)
    assert isinstance(result.annualized_return, float)
    assert isinstance(result.annualized_volatility, float)


def test_empty_returns() -> None:
    """Empty return series returns zeroes."""
    result = compute_risk_metrics(pd.Series([], dtype=float))
    assert result.sharpe_ratio == 0.0
    assert result.sortino_ratio == 0.0
    assert result.annualized_return == 0.0


def test_negative_drift_sharpe() -> None:
    """Negative-drift returns produce negative Sharpe."""
    rng = np.random.default_rng(42)
    returns = pd.Series(rng.normal(-0.005, 0.02, 252))
    result = compute_risk_metrics(returns)
    assert result.sharpe_ratio < 0
