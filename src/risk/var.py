"""Historical simulation Value-at-Risk and max drawdown computation.

Pure computation module -- no DB or pipeline imports.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class VaRResult:
    """Result of historical VaR computation."""

    daily_var_95: float
    daily_var_99: float
    weekly_var_95: float
    weekly_var_99: float
    max_drawdown: float
    max_drawdown_start: str
    max_drawdown_end: str


def compute_historical_var(
    returns: pd.Series,
    lookback: int = 252,
) -> VaRResult:
    """Compute historical simulation VaR and max drawdown.

    Args:
        returns: Daily return series.
        lookback: Number of trailing periods to use.

    Returns:
        VaRResult with daily/weekly VaR at 95% and 99%, plus max drawdown info.

    Raises:
        ValueError: If fewer than 60 data points available.
    """
    r = returns.tail(lookback).dropna()
    if len(r) < 60:
        msg = f"Insufficient data for VaR: {len(r)} points (minimum 60)"
        raise ValueError(msg)

    # Daily VaR (5th and 1st percentile of returns)
    daily_95 = float(np.percentile(r, 5))
    daily_99 = float(np.percentile(r, 1))

    # Weekly VaR: 5-day rolling sum if enough points, else scale daily
    if len(r) > 20:
        weekly_returns = r.rolling(5).sum().dropna()
        weekly_95 = float(np.percentile(weekly_returns, 5))
        weekly_99 = float(np.percentile(weekly_returns, 1))
    else:
        weekly_95 = daily_95 * np.sqrt(5)
        weekly_99 = daily_99 * np.sqrt(5)

    # Max drawdown
    cumulative = (1 + r).cumprod()
    running_max = cumulative.cummax()
    drawdown = (cumulative - running_max) / running_max
    min_idx = drawdown.idxmin()
    max_dd = float(drawdown.loc[min_idx])

    # Find drawdown start (peak before trough)
    peak_idx = cumulative.loc[:min_idx].idxmax()

    return VaRResult(
        daily_var_95=round(daily_95, 6),
        daily_var_99=round(daily_99, 6),
        weekly_var_95=round(weekly_95, 6),
        weekly_var_99=round(weekly_99, 6),
        max_drawdown=round(max_dd, 6),
        max_drawdown_start=str(peak_idx.date()) if hasattr(peak_idx, "date") else str(peak_idx),
        max_drawdown_end=str(min_idx.date()) if hasattr(min_idx, "date") else str(min_idx),
    )
