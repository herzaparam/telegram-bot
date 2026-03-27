"""Portfolio concentration analysis (sector, single-asset, currency exposure).

Pure computation module -- no DB or pipeline imports.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ConcentrationResult:
    """Result of concentration analysis."""

    sector_pct: dict[str, float]
    max_single_pct: float
    idr_pct: float
    usd_pct: float
    asset_count: int


def compute_concentration(
    assets: list[dict],
    sector_map: dict[str, str],
) -> ConcentrationResult:
    """Compute portfolio concentration metrics assuming equal weight.

    Args:
        assets: List of dicts with ``symbol`` and ``asset_type`` keys.
        sector_map: Mapping of stock ticker -> sector name.

    Returns:
        ConcentrationResult with sector breakdown, max single-asset pct, and currency split.
    """
    n = len(assets)
    if n == 0:
        return ConcentrationResult(
            sector_pct={},
            max_single_pct=0.0,
            idr_pct=0.0,
            usd_pct=0.0,
            asset_count=0,
        )

    weight = 100.0 / n

    # Sector grouping
    sector_counts: dict[str, float] = {}
    stock_count = 0
    crypto_count = 0

    for asset in assets:
        asset_type = asset.get("asset_type", "")
        symbol = asset.get("symbol", "")

        if asset_type == "crypto":
            sector = "crypto"
            crypto_count += 1
        else:
            sector = sector_map.get(symbol, "unknown")
            stock_count += 1

        sector_counts[sector] = sector_counts.get(sector, 0.0) + weight

    # Round sector percentages
    sector_pct = {k: round(v, 4) for k, v in sector_counts.items()}

    # Currency exposure: stocks = IDR, crypto = USD
    idr_pct = round(stock_count / n * 100, 4)
    usd_pct = round(crypto_count / n * 100, 4)

    return ConcentrationResult(
        sector_pct=sector_pct,
        max_single_pct=round(weight, 4),
        idr_pct=idr_pct,
        usd_pct=usd_pct,
        asset_count=n,
    )
