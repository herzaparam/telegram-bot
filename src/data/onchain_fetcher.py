"""On-chain data fetcher using DeFiLlama API for TVL metrics.

Fetches historical TVL data for crypto chains and computes trend metrics.
Graceful degradation: returns empty dict on any failure (D-09).
"""

from __future__ import annotations

import asyncio
from datetime import UTC, date, datetime

import httpx
import structlog
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession
from tenacity import retry, stop_after_attempt, wait_exponential

from src.db.models import OnChainData

logger = structlog.get_logger(__name__)

DEFILLAMA_BASE = "https://api.llama.fi"

CHAIN_MAP: dict[str, str] = {
    "BTC": "Bitcoin",
    "ETH": "Ethereum",
    "SOL": "Solana",
}


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=2, min=2, max=30))
async def _get_tvl_raw(client: httpx.AsyncClient, chain: str) -> list[dict]:
    """GET historical TVL from DeFiLlama with retry."""
    url = f"{DEFILLAMA_BASE}/v2/historicalChainTvl/{chain}"
    resp = await client.get(url)
    resp.raise_for_status()
    return resp.json()  # type: ignore[no-any-return]


async def fetch_tvl_history(symbol: str, days: int = 30) -> list[dict]:
    """Fetch historical TVL data from DeFiLlama for a crypto chain.

    Args:
        symbol: Crypto symbol (BTC, ETH, SOL).
        days: Number of days of history (unused for API call, full history returned).

    Returns:
        List of {"date": unix_ts, "tvl": float}. Empty list if symbol not in CHAIN_MAP.
    """
    chain = CHAIN_MAP.get(symbol)
    if chain is None:
        return []

    async with httpx.AsyncClient(timeout=30.0) as client:
        data = await _get_tvl_raw(client, chain)

    # Rate limit: 0.5s sleep between chain requests
    await asyncio.sleep(0.5)

    return data  # type: ignore[no-any-return]


async def fetch_onchain_data(
    symbol: str,
    asset_id: int,
    session: AsyncSession,
) -> dict:
    """Fetch on-chain TVL data and compute trend metrics.

    Args:
        symbol: Crypto symbol (BTC, ETH, SOL). Returns {} for stocks.
        asset_id: Database asset ID for storing OnChainData rows.
        session: SQLAlchemy async session.

    Returns:
        Dict with tvl_current, tvl_7d_change, tvl_30d_change, source.
        Empty dict on failure or for non-crypto symbols.
    """
    try:
        history = await fetch_tvl_history(symbol)
        if not history:
            return {}

        # Sort by date ascending
        history.sort(key=lambda x: x.get("date", 0))

        tvl_current = history[-1].get("tvl", 0.0)

        # Find 7d and 30d ago entries
        now_ts = history[-1].get("date", 0)
        target_7d = now_ts - 86400 * 7
        target_30d = now_ts - 86400 * 30

        tvl_7d_ago = _find_closest_tvl(history, target_7d)
        tvl_30d_ago = _find_closest_tvl(history, target_30d)

        # Compute changes
        tvl_7d_change = (tvl_current - tvl_7d_ago) / tvl_7d_ago if tvl_7d_ago else 0.0
        tvl_30d_change = (tvl_current - tvl_30d_ago) / tvl_30d_ago if tvl_30d_ago else 0.0

        # Store OnChainData rows via UPSERT
        today = date.today()
        metrics = [
            ("tvl", tvl_current),
            ("tvl_7d_change", tvl_7d_change),
            ("tvl_30d_change", tvl_30d_change),
        ]
        for metric_name, value in metrics:
            stmt = pg_insert(OnChainData).values(
                asset_id=asset_id,
                date=today,
                metric=metric_name,
                value=value,
                source="defillama",
                fetched_at=datetime.now(UTC),
            )
            stmt = stmt.on_conflict_do_update(
                constraint="uq_onchain_asset_date_metric",
                set_={"value": value, "fetched_at": datetime.now(UTC)},
            )
            await session.execute(stmt)

        return {
            "tvl_current": tvl_current,
            "tvl_7d_change": tvl_7d_change,
            "tvl_30d_change": tvl_30d_change,
            "source": "defillama",
        }

    except Exception as exc:
        logger.warning("onchain_fetch_failed", symbol=symbol, error=str(exc))
        return {}


def _find_closest_tvl(history: list[dict], target_ts: int) -> float:
    """Find the TVL value closest to a target timestamp."""
    if not history:
        return 0.0
    closest = min(history, key=lambda x: abs(x.get("date", 0) - target_ts))
    return closest.get("tvl", 0.0)
