"""Sharpe and Sortino ratio computation.

Pure computation module -- no DB or pipeline imports.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class RiskMetricsResult:
    """Result of risk-adjusted metrics computation."""

    sharpe_ratio: float
    sortino_ratio: float
    annualized_return: float
    annualized_volatility: float


def compute_risk_metrics(
    returns: pd.Series,
    risk_free_rate: float = 0.05,
    periods_per_year: int = 252,
) -> RiskMetricsResult:
    """Compute Sharpe and Sortino ratios from a return series.

    Args:
        returns: Daily return series.
        risk_free_rate: Annualized risk-free rate (default 5% for IDR).
        periods_per_year: Trading periods per year (252 for daily).

    Returns:
        RiskMetricsResult with Sharpe, Sortino, annualized return and volatility.
    """
    r = returns.dropna()
    if len(r) == 0:
        return RiskMetricsResult(
            sharpe_ratio=0.0,
            sortino_ratio=0.0,
            annualized_return=0.0,
            annualized_volatility=0.0,
        )

    mean_r = float(r.mean())
    std_r = float(r.std())

    annualized_return = mean_r * periods_per_year
    annualized_vol = std_r * math.sqrt(periods_per_year)

    # Sharpe ratio
    if annualized_vol == 0.0:
        sharpe = 0.0
    else:
        sharpe = (annualized_return - risk_free_rate) / annualized_vol

    # Sortino ratio (downside deviation)
    downside = r[r < 0]
    if len(downside) == 0 or float(downside.std()) == 0.0:
        sortino = 0.0
    else:
        downside_std = float(downside.std()) * math.sqrt(periods_per_year)
        sortino = (annualized_return - risk_free_rate) / downside_std

    return RiskMetricsResult(
        sharpe_ratio=round(sharpe, 6),
        sortino_ratio=round(sortino, 6),
        annualized_return=round(annualized_return, 6),
        annualized_volatility=round(annualized_vol, 6),
    )
