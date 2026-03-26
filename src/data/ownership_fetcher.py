"""IDX ownership/disclosure filing scraper.

Fetches shareholder composition from idx.co.id disclosure filings.
Reuses httpx patterns from idx_doc_fetcher.py. Weekly refresh cycle (D-12).
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from typing import TYPE_CHECKING

import httpx
import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import Asset, OwnershipSnapshot

if TYPE_CHECKING:
    pass

logger = structlog.get_logger(__name__)

_IDX_SHAREHOLDER_URL = (
    "https://www.idx.co.id/primary/ListedCompany/GetShareHolder"
)
_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
}
_REFRESH_INTERVAL_DAYS = 7


async def fetch_ownership_data(
    session: AsyncSession, asset: Asset
) -> dict | None:
    """Fetch shareholder composition for an IDX stock asset.

    Checks if an :class:`OwnershipSnapshot` exists for this week already
    (weekly refresh D-12).  If yes, returns the existing data.  If no,
    scrapes the IDX shareholder endpoint.

    Returns a dict with ``shareholders``, ``public_float_pct``, and
    ``total_shares`` keys, or ``None`` on failure.
    """
    log = logger.bind(component="ownership_fetcher", asset=asset.symbol)

    # Check cache freshness
    cutoff = date.today() - timedelta(days=_REFRESH_INTERVAL_DAYS)
    result = await session.execute(
        select(OwnershipSnapshot)
        .where(OwnershipSnapshot.asset_id == asset.id)
        .where(OwnershipSnapshot.snapshot_date >= cutoff)
        .order_by(OwnershipSnapshot.snapshot_date.desc())
        .limit(1)
    )
    cached: OwnershipSnapshot | None = result.scalar_one_or_none()

    if cached is not None:
        log.debug("ownership_cache_hit", snapshot_date=str(cached.snapshot_date))
        return {
            "shareholders": cached.shareholders,
            "public_float_pct": cached.public_float_pct,
            "total_shares": cached.total_shares,
        }

    # Resolve IDX emiten code
    yf_symbol = asset.yfinance_symbol or f"{asset.symbol}.JK"
    code = yf_symbol.replace(".JK", "")

    log.info("fetching_ownership", code=code)

    try:
        async with httpx.AsyncClient(timeout=30.0, headers=_HEADERS) as client:
            resp = await client.get(
                _IDX_SHAREHOLDER_URL,
                params={
                    "KodeEmiten": code,
                    "start": "0",
                    "length": "100",
                },
            )
            resp.raise_for_status()
            data = resp.json()
    except Exception as exc:  # noqa: BLE001
        log.warning("ownership_fetch_failed", code=code, error=str(exc))
        return None

    parsed = _parse_shareholder_response(data)
    if not parsed["shareholders"]:
        log.warning("no_shareholders_parsed", code=code)
        return None

    # Store snapshot
    snapshot = OwnershipSnapshot(
        asset_id=asset.id,
        snapshot_date=date.today(),
        shareholders=parsed["shareholders"],
        total_shares=parsed.get("total_shares"),
        public_float_pct=parsed.get("public_float_pct"),
    )
    session.add(snapshot)

    log.info(
        "ownership_stored",
        code=code,
        shareholder_count=len(parsed["shareholders"]),
    )

    return parsed


def _parse_shareholder_response(data: dict) -> dict:
    """Extract shareholder list from IDX API response.

    Returns::

        {
            "shareholders": [{"name": str, "pct": float}, ...],
            "public_float_pct": float | None,
            "total_shares": float | None,
        }
    """
    shareholders: list[dict] = []
    public_float_pct: float | None = None

    entries = data.get("data", [])
    for entry in entries:
        name = entry.get("ShareHolderName", "").strip()
        pct_str = entry.get("Percentage", "0")
        try:
            pct = float(pct_str)
        except (ValueError, TypeError):
            pct = 0.0

        if not name:
            continue

        shareholders.append({"name": name, "pct": pct})

        # Detect public float entry
        if "public" in name.lower() or "masyarakat" in name.lower():
            public_float_pct = pct

    return {
        "shareholders": shareholders,
        "public_float_pct": public_float_pct,
        "total_shares": None,  # IDX API doesn't always provide total
    }


def _compute_ownership_changes(
    current: dict, previous: dict | None
) -> dict | None:
    """Compare current vs previous snapshot for significant changes.

    Flags changes where a holder's percentage changed by >2 percentage
    points.  Returns ``None`` when there is no previous snapshot.
    """
    if previous is None:
        return None

    current_map: dict[str, float] = {
        s["name"]: s["pct"] for s in current.get("shareholders", [])
    }
    previous_map: dict[str, float] = {
        s["name"]: s["pct"] for s in previous.get("shareholders", [])
    }

    major_changes: list[dict] = []
    all_names = set(current_map) | set(previous_map)

    for name in all_names:
        old_pct = previous_map.get(name, 0.0)
        new_pct = current_map.get(name, 0.0)
        diff = new_pct - old_pct

        if abs(diff) > 2.0:
            direction = "increase" if diff > 0 else "decrease"
            major_changes.append(
                {
                    "name": name,
                    "old_pct": old_pct,
                    "new_pct": new_pct,
                    "direction": direction,
                }
            )

    # Public float change
    cur_float = 0.0
    prev_float = 0.0
    for s in current.get("shareholders", []):
        if "public" in s.get("name", "").lower():
            cur_float = s["pct"]
    for s in previous.get("shareholders", []):
        if "public" in s.get("name", "").lower():
            prev_float = s["pct"]

    return {
        "major_changes": major_changes,
        "public_float_change": cur_float - prev_float,
    }
