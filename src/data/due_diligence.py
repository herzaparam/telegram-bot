"""Due diligence computation for IDX stocks.

Computes sector benchmarking (DUED-01), management quality (DUED-03),
competitive positioning (DUED-04), and generates DD flags for LLM injection.
All data sourced from existing StockFundamental and FinancialData tables.
"""

from __future__ import annotations

import statistics
from datetime import date, timedelta
from typing import TYPE_CHECKING

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.data.ownership_fetcher import _compute_ownership_changes, fetch_ownership_data
from src.db.models import (
    Asset,
    DueDiligenceReport,
    FinancialData,
    OwnershipSnapshot,
    StockFundamental,
)
from src.engines.valuation import IDX_SECTOR_MAP

if TYPE_CHECKING:
    pass

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Sector benchmarking (DUED-01)
# ---------------------------------------------------------------------------


async def compute_sector_benchmark(
    session: AsyncSession, asset: Asset, sector: str
) -> dict | None:
    """Compare company fundamentals against sector median.

    Queries all :class:`StockFundamental` records for assets in the same
    sector (via :data:`IDX_SECTOR_MAP`) and computes medians for P/E, P/B,
    ROE, revenue_growth, and debt_to_equity.

    Returns ``None`` when the company has no fundamental data.
    """
    log = logger.bind(component="sector_benchmark", asset=asset.symbol, sector=sector)

    # Get company fundamental
    result = await session.execute(
        select(StockFundamental).where(StockFundamental.asset_id == asset.id)
    )
    company: StockFundamental | None = result.scalar_one_or_none()

    if company is None:
        log.debug("no_company_fundamental")
        return None

    # Get all sector peer symbols
    sector_symbols = [sym for sym, sec in IDX_SECTOR_MAP.items() if sec == sector]
    if not sector_symbols:
        log.debug("no_sector_peers", sector=sector)
        return None

    # Query all fundamentals for sector peers (by joining with Asset)
    result = await session.execute(
        select(StockFundamental).where(
            StockFundamental.asset_id.in_(
                select(Asset.id).where(Asset.symbol.in_(sector_symbols))
            )
        )
    )
    peers: list[StockFundamental] = list(result.all())

    if not peers:
        log.debug("no_peer_fundamentals")
        return None

    def _median(values: list[float]) -> float | None:
        clean = [v for v in values if v is not None]
        if not clean:
            return None
        return statistics.median(clean)

    def _compare(value: float | None, median: float | None, invert: bool = False) -> dict | None:
        if value is None or median is None or median == 0:
            return None
        vs_median = ((value - median) / abs(median)) * 100.0
        # Position logic: >10% difference = above/below, else at_median
        # For inverted metrics (D/E), lower is better
        if invert:
            if vs_median < -10:
                position = "below"  # lower D/E is good
            elif vs_median > 10:
                position = "above"
            else:
                position = "at_median"
        else:
            if vs_median > 10:
                position = "above"
            elif vs_median < -10:
                position = "below"
            else:
                position = "at_median"

        return {
            "value": value,
            "median": median,
            "vs_median": round(vs_median, 1),
            "position": position,
        }

    pe_median = _median([p.trailing_pe for p in peers])
    pb_median = _median([p.price_to_book for p in peers])
    roe_median = _median([p.return_on_equity for p in peers])
    rg_median = _median([p.revenue_growth for p in peers])
    de_median = _median([p.debt_to_equity for p in peers])

    bench: dict = {}

    pe_comp = _compare(company.trailing_pe, pe_median)
    if pe_comp:
        bench["pe"] = pe_comp

    pb_comp = _compare(company.price_to_book, pb_median)
    if pb_comp:
        bench["pb"] = pb_comp

    roe_comp = _compare(company.return_on_equity, roe_median)
    if roe_comp:
        bench["roe"] = roe_comp

    rg_comp = _compare(company.revenue_growth, rg_median)
    if rg_comp:
        bench["revenue_growth"] = rg_comp

    de_comp = _compare(company.debt_to_equity, de_median, invert=True)
    if de_comp:
        bench["debt_to_equity"] = de_comp

    # Rank by ROE within sector (descending)
    roe_values = sorted(
        [(p.asset_id, p.return_on_equity or 0.0) for p in peers],
        key=lambda x: x[1],
        reverse=True,
    )
    rank = next(
        (i + 1 for i, (aid, _) in enumerate(roe_values) if aid == asset.id),
        len(roe_values),
    )
    bench["rank"] = rank
    bench["of"] = len(peers)

    log.info("sector_benchmark_computed", metrics=len(bench) - 2, rank=rank)
    return bench


# ---------------------------------------------------------------------------
# Management quality (DUED-03)
# ---------------------------------------------------------------------------


def compute_management_quality(financial_records: list) -> dict:
    """Score management quality from FinancialData records.

    Uses revenue CAGR (40% weight), ROE trend (30%), and capital
    allocation (30%).  Returns ``{"score": 0.0, "label": "Insufficient data"}``
    when fewer than 4 revenue records are available.
    """
    # Group records by metric
    revenues = sorted(
        [r for r in financial_records if r.metric_name == "revenue"],
        key=lambda r: r.period_date,
    )
    net_profits = sorted(
        [r for r in financial_records if r.metric_name == "net_profit"],
        key=lambda r: r.period_date,
    )
    equities = sorted(
        [r for r in financial_records if r.metric_name == "total_equity"],
        key=lambda r: r.period_date,
    )

    if len(revenues) < 4:
        return {"score": 0.0, "label": "Insufficient data", "detail": {}}

    # --- Revenue CAGR (40% weight) ---
    first_rev = revenues[0].metric_value
    last_rev = revenues[-1].metric_value
    n_periods = len(revenues) - 1

    if first_rev and first_rev > 0 and last_rev and last_rev > 0 and n_periods > 0:
        cagr = (last_rev / first_rev) ** (1.0 / n_periods) - 1.0
        # Annualise if quarterly data (multiply by 4)
        if n_periods <= 8:  # likely quarterly
            cagr_annual = cagr * 4.0
        else:
            cagr_annual = cagr
        revenue_cagr_score = min(max(cagr_annual / 0.15, 0.0), 1.0)
    else:
        cagr_annual = 0.0
        revenue_cagr_score = 0.0

    # --- ROE trend (30% weight) ---
    roe_values: list[float] = []
    for i in range(min(len(net_profits), len(equities))):
        np_val = net_profits[i].metric_value
        eq_val = equities[i].metric_value
        if np_val is not None and eq_val and eq_val > 0:
            roe_values.append(np_val / eq_val)

    if roe_values:
        avg_roe = sum(roe_values) / len(roe_values)
        roe_score = min(max(avg_roe / 0.20, 0.0), 1.0)
    else:
        avg_roe = 0.0
        roe_score = 0.0

    # --- Capital allocation (30% weight) ---
    # Net profit / total equity trend; default 0.5 if insufficient
    if len(net_profits) >= 4 and len(equities) >= 4:
        recent_roe = roe_values[-1] if roe_values else 0.0
        cap_alloc_score = min(max(recent_roe / 0.20, 0.0), 1.0)
    else:
        cap_alloc_score = 0.5

    # --- Weighted total ---
    total_score = (
        revenue_cagr_score * 0.40
        + roe_score * 0.30
        + cap_alloc_score * 0.30
    )

    # Labels
    if total_score > 0.7:
        label = "Excellent"
    elif total_score > 0.5:
        label = "Good"
    elif total_score > 0.3:
        label = "Fair"
    else:
        label = "Weak"

    return {
        "score": round(total_score, 3),
        "label": label,
        "detail": {
            "revenue_cagr": round(cagr_annual, 4),
            "roe_score": round(roe_score, 3),
            "cap_alloc_score": round(cap_alloc_score, 3),
        },
    }


# ---------------------------------------------------------------------------
# Competitive positioning (DUED-04)
# ---------------------------------------------------------------------------


async def compute_competitive_position(
    session: AsyncSession, asset: Asset, sector: str
) -> dict:
    """Rank asset within sector peers by composite score.

    Composite = ROE + revenue_growth + (inverted D/E penalty).
    Moat indicators derived from comparison against sector median.
    """
    log = logger.bind(component="competitive_position", asset=asset.symbol, sector=sector)

    sector_symbols = [sym for sym, sec in IDX_SECTOR_MAP.items() if sec == sector]

    result = await session.execute(
        select(StockFundamental).where(
            StockFundamental.asset_id.in_(
                select(Asset.id).where(Asset.symbol.in_(sector_symbols))
            )
        )
    )
    peers: list[StockFundamental] = list(result.all())

    if not peers:
        log.debug("no_peers_for_competitive_position")
        return {"rank": 1, "of": 1, "metric": "ROE-weighted composite", "moat_indicators": []}

    def _composite(p: StockFundamental) -> float:
        roe = p.return_on_equity or 0.0
        rg = p.revenue_growth or 0.0
        de = p.debt_to_equity or 0.0
        de_penalty = max(0, de - 1.0) * 0.1  # penalize high leverage
        return roe + rg - de_penalty

    ranked = sorted(peers, key=_composite, reverse=True)
    rank = next(
        (i + 1 for i, p in enumerate(ranked) if p.asset_id == asset.id),
        len(ranked),
    )

    # Moat indicators
    roe_median = statistics.median([p.return_on_equity or 0 for p in peers]) if peers else 0
    rg_median = statistics.median([p.revenue_growth or 0 for p in peers]) if peers else 0
    de_median = statistics.median([p.debt_to_equity or 0 for p in peers]) if peers else 0

    company = next((p for p in peers if p.asset_id == asset.id), None)
    moat: list[str] = []
    if company:
        if (company.return_on_equity or 0) > roe_median * 1.5 and roe_median > 0:
            moat.append("High ROE vs peers")
        if (company.revenue_growth or 0) > rg_median and rg_median > 0:
            moat.append("Consistent margins")
        if de_median > 0 and (company.debt_to_equity or 0) < de_median * 0.5:
            moat.append("Low leverage")

    log.info("competitive_position_computed", rank=rank, of=len(peers))

    return {
        "rank": rank,
        "of": len(peers),
        "metric": "ROE-weighted composite",
        "moat_indicators": moat,
    }


# ---------------------------------------------------------------------------
# DD flags (D-18)
# ---------------------------------------------------------------------------


def generate_dd_flags(
    sector_bench: dict | None,
    mgmt_quality: dict | None,
    ownership_changes: dict | None,
) -> list[dict]:
    """Generate due diligence flags for LLM consumption.

    Scans ownership changes, management quality, and sector benchmark
    data for noteworthy conditions.
    """
    flags: list[dict] = []

    # Ownership decrease >5pp by any major holder
    if ownership_changes and ownership_changes.get("major_changes"):
        for change in ownership_changes["major_changes"]:
            if change["direction"] == "decrease":
                decrease_pp = change["old_pct"] - change["new_pct"]
                if decrease_pp > 5.0:
                    flags.append(
                        {
                            "type": "insider_selling",
                            "severity": "warning",
                            "message": (
                                f"{change['name']} reduced stake by "
                                f"{decrease_pp:.1f}pp "
                                f"({change['old_pct']:.1f}% -> {change['new_pct']:.1f}%)"
                            ),
                        }
                    )

    # Management score <0.3
    if mgmt_quality and mgmt_quality.get("score", 1.0) < 0.3:
        flags.append(
            {
                "type": "weak_management",
                "severity": "warning",
                "message": (
                    f"Management quality score {mgmt_quality['score']:.2f} "
                    f"({mgmt_quality.get('label', 'N/A')})"
                ),
            }
        )

    # P/E >50% above sector median
    if sector_bench and "pe" in sector_bench:
        pe_vs = sector_bench["pe"].get("vs_median", 0)
        if pe_vs > 50:
            flags.append(
                {
                    "type": "overvaluation_risk",
                    "severity": "info",
                    "message": (
                        f"P/E {pe_vs:.0f}% above sector median "
                        f"({sector_bench['pe']['value']:.1f} vs {sector_bench['pe']['median']:.1f})"
                    ),
                }
            )

    # D/E >2x sector median (vs_median > 100%)
    if sector_bench and "debt_to_equity" in sector_bench:
        de_vs = sector_bench["debt_to_equity"].get("vs_median", 0)
        if de_vs > 100:
            flags.append(
                {
                    "type": "high_leverage",
                    "severity": "warning",
                    "message": (
                        f"D/E ratio {de_vs:.0f}% above sector median "
                        f"({sector_bench['debt_to_equity']['value']:.1f} vs "
                        f"{sector_bench['debt_to_equity']['median']:.1f})"
                    ),
                }
            )

    return flags


# ---------------------------------------------------------------------------
# DD report orchestrator
# ---------------------------------------------------------------------------


async def compute_dd_report(
    session: AsyncSession, asset: Asset, run_date: date
) -> DueDiligenceReport | None:
    """Main DD orchestrator.  Checks weekly cache, computes all sections.

    If a cached :class:`DueDiligenceReport` exists for this week, returns
    it directly.  Otherwise computes sector benchmark, management quality,
    ownership, competitive position, and DD flags, then stores as a new
    report.
    """
    log = logger.bind(component="dd_report", asset=asset.symbol, run_date=str(run_date))

    # Check weekly cache
    week_start = run_date - timedelta(days=run_date.weekday())
    result = await session.execute(
        select(DueDiligenceReport)
        .where(DueDiligenceReport.asset_id == asset.id)
        .where(DueDiligenceReport.report_date >= week_start)
        .order_by(DueDiligenceReport.report_date.desc())
        .limit(1)
    )
    cached: DueDiligenceReport | None = result.scalar_one_or_none()
    if cached is not None:
        log.debug("dd_report_cache_hit", report_date=str(cached.report_date))
        return cached

    # Resolve sector
    sector = IDX_SECTOR_MAP.get(asset.symbol)

    # Sector benchmark (requires sector)
    sector_bench = None
    if sector:
        sector_bench = await compute_sector_benchmark(session, asset, sector)

    # Financial data for management quality
    result = await session.execute(
        select(FinancialData)
        .where(FinancialData.asset_id == asset.id)
        .order_by(FinancialData.period_date.asc())
    )
    fin_records = list(result.all())
    mgmt_quality = compute_management_quality(fin_records)

    # Ownership data
    ownership_data = await fetch_ownership_data(session, asset)

    # Ownership changes vs previous snapshot
    ownership_changes = None
    if ownership_data:
        # Try to find previous snapshot
        prev_result = await session.execute(
            select(OwnershipSnapshot)
            .where(OwnershipSnapshot.asset_id == asset.id)
            .order_by(OwnershipSnapshot.snapshot_date.desc())
            .offset(1)
            .limit(1)
        )
        prev_snap = prev_result.scalar_one_or_none()
        if prev_snap:
            ownership_changes = _compute_ownership_changes(
                ownership_data,
                {"shareholders": prev_snap.shareholders},
            )

    # Competitive position (requires sector)
    competitive = None
    if sector:
        competitive = await compute_competitive_position(session, asset, sector)

    # Generate DD flags
    dd_flags = generate_dd_flags(sector_bench, mgmt_quality, ownership_changes)

    # Build and store report
    report = DueDiligenceReport(
        asset_id=asset.id,
        report_date=run_date,
        sector=sector,
        sector_rank=sector_bench,
        management_quality=mgmt_quality,
        ownership_changes=ownership_changes,
        competitive_position=competitive,
        dd_flags=dd_flags,
    )
    session.add(report)

    log.info(
        "dd_report_created",
        sector=sector,
        flags=len(dd_flags),
        has_sector_bench=sector_bench is not None,
    )

    return report
