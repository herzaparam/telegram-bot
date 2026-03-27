"""Preset scenario stress testing for portfolios.

Pure computation module -- no DB or pipeline imports.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class StressResult:
    """Result of a single stress scenario applied to portfolio."""

    scenario_id: str
    scenario_name: str
    stock_drawdown: float
    crypto_drawdown: float
    portfolio_impact: float
    duration_days: int


# Preset stress scenarios based on historical events
STRESS_SCENARIOS: dict[str, dict] = {
    "covid_2020": {
        "name": "COVID-19 Crash (Mar 2020)",
        "stock_drawdown": -0.37,
        "crypto_drawdown": -0.50,
        "duration_days": 30,
    },
    "crypto_winter_2022": {
        "name": "Crypto Winter (2022)",
        "stock_drawdown": -0.10,
        "crypto_drawdown": -0.77,
        "duration_days": 365,
    },
    "taper_tantrum_2013": {
        "name": "Taper Tantrum (2013)",
        "stock_drawdown": -0.15,
        "crypto_drawdown": -0.05,
        "duration_days": 90,
    },
    "gfc_2008": {
        "name": "Global Financial Crisis (2008)",
        "stock_drawdown": -0.60,
        "crypto_drawdown": 0.0,
        "duration_days": 365,
    },
}


def run_stress_test(assets: list[dict]) -> list[StressResult]:
    """Apply preset stress scenarios to a portfolio of assets.

    Each asset is equal-weighted. Stock assets receive the stock drawdown,
    crypto assets receive the crypto drawdown for each scenario.

    Args:
        assets: List of dicts with ``symbol`` and ``asset_type`` keys.

    Returns:
        List of StressResult, one per scenario.
    """
    n = len(assets)
    if n == 0:
        return []

    weight = 1.0 / n

    results: list[StressResult] = []
    for scenario_id, scenario in STRESS_SCENARIOS.items():
        portfolio_impact = 0.0
        for asset in assets:
            asset_type = asset.get("asset_type", "")
            if asset_type == "crypto":
                portfolio_impact += weight * scenario["crypto_drawdown"]
            else:
                portfolio_impact += weight * scenario["stock_drawdown"]

        results.append(
            StressResult(
                scenario_id=scenario_id,
                scenario_name=scenario["name"],
                stock_drawdown=scenario["stock_drawdown"],
                crypto_drawdown=scenario["crypto_drawdown"],
                portfolio_impact=round(portfolio_impact, 6),
                duration_days=scenario["duration_days"],
            )
        )

    return results
