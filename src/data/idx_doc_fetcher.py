"""IDX financial document (laporan keuangan) PDF fetcher.

Downloads quarterly and annual financial reports from idx.co.id for IDX
stock assets. PDFs are saved to ``data/financial_docs/{SYMBOL}/`` and
recorded in the ``financial_docs`` table with ``parse_status='pending'``
for downstream PDF parsing.

Respects a 7-day fetch interval to avoid hammering the IDX website.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING

import httpx
import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import Asset, FinancialDoc

if TYPE_CHECKING:
    pass

logger = structlog.get_logger(__name__)

IDX_REPORT_URL = "https://idx.co.id/umbraco/Surface/ListedCompany/GetFinancialReport"
_FETCH_INTERVAL_DAYS = 7

FINANCIAL_DOCS_DIR = "data/financial_docs"

_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
}

PERIODE_MAP = {
    "tw1": ("quarterly", "Q1"),
    "tw2": ("quarterly", "Q2"),
    "tw3": ("quarterly", "Q3"),
    "tahunan": ("annual", "FY"),
}


async def fetch_idx_docs(session: AsyncSession, asset: Asset) -> None:
    """Fetch IDX financial report PDFs for a single stock asset.

    1. Check if last fetch was within 7 days -- skip if recent.
    2. Strip ``.JK`` suffix to get IDX emiten code.
    3. Query IDX API for current and previous year, all 4 periode values.
    4. Download PDFs and record in ``financial_docs`` table.

    All HTTP errors are caught and logged -- this function never raises.

    Args:
        session: Active SQLAlchemy async session.
        asset: Asset ORM instance (must be a stock with yfinance_symbol).
    """
    log = logger.bind(component="idx_doc_fetcher", asset=asset.symbol)

    # Only fetch for stock assets
    if asset.asset_type != "stock":
        log.debug("skipping_non_stock", asset_type=asset.asset_type)
        return

    # Check cache freshness -- most recent download for this asset
    result = await session.execute(
        select(FinancialDoc)
        .where(FinancialDoc.asset_id == asset.id)
        .order_by(FinancialDoc.downloaded_at.desc())
        .limit(1)
    )
    latest: FinancialDoc | None = result.scalar_one_or_none()

    if latest is not None:
        dl_at = latest.downloaded_at
        if dl_at.tzinfo is None:
            dl_at = dl_at.replace(tzinfo=UTC)
        age = datetime.now(UTC) - dl_at
        if age < timedelta(days=_FETCH_INTERVAL_DAYS):
            log.debug(
                "cache_fresh",
                asset_id=asset.id,
                age_days=age.days,
                ttl_days=_FETCH_INTERVAL_DAYS,
            )
            return

    # Resolve IDX emiten code: strip .JK suffix
    yf_symbol = asset.yfinance_symbol or f"{asset.symbol}.JK"
    code = yf_symbol.replace(".JK", "")

    log.info("fetching_idx_docs", code=code)

    # Load existing docs for this asset to skip duplicates
    existing_result = await session.scalars(
        select(FinancialDoc).where(FinancialDoc.asset_id == asset.id)
    )
    existing_docs = existing_result.all()
    existing_keys = {(d.doc_type, d.period) for d in existing_docs}

    current_year = datetime.now(UTC).year
    years = [current_year, current_year - 1]

    async with httpx.AsyncClient(timeout=30.0, headers=_HEADERS) as client:
        for year in years:
            for periode, (doc_type, period_prefix) in PERIODE_MAP.items():
                period_label = f"{period_prefix}-{year}"

                # Skip if already exists
                if (doc_type, period_label) in existing_keys:
                    log.debug("doc_already_exists", period=period_label, doc_type=doc_type)
                    continue

                try:
                    resp = await client.get(
                        IDX_REPORT_URL,
                        params={
                            "indexFrom": "0",
                            "pageSize": "10",
                            "year": str(year),
                            "reportType": "rdf",
                            "periode": periode,
                            "kodeEmiten": code,
                        },
                    )
                    resp.raise_for_status()
                    data = resp.json()
                except Exception as exc:  # noqa: BLE001
                    log.error(
                        "idx_api_request_failed",
                        code=code,
                        year=year,
                        periode=periode,
                        error=str(exc),
                    )
                    await asyncio.sleep(1.0)
                    continue

                results = data.get("Results", [])
                if not results:
                    log.debug("no_results", code=code, year=year, periode=periode)
                    await asyncio.sleep(1.0)
                    continue

                # Process first result's attachments
                for entry in results:
                    attachments = entry.get("Attachments", [])
                    for attachment in attachments:
                        file_url = attachment.get("File_Path")
                        if not file_url:
                            continue

                        # Download PDF
                        try:
                            pdf_resp = await client.get(file_url)
                            pdf_resp.raise_for_status()
                            pdf_bytes = await pdf_resp.aread() if hasattr(pdf_resp, "aread") else pdf_resp.content
                        except Exception as exc:  # noqa: BLE001
                            log.error(
                                "pdf_download_failed",
                                url=file_url,
                                error=str(exc),
                            )
                            continue

                        # Save to filesystem
                        symbol_dir = Path(FINANCIAL_DOCS_DIR) / code
                        symbol_dir.mkdir(parents=True, exist_ok=True)
                        pdf_path = symbol_dir / f"{period_label}.pdf"
                        pdf_path.write_bytes(pdf_bytes)

                        # Record in DB
                        doc = FinancialDoc(
                            asset_id=asset.id,
                            doc_type=doc_type,
                            period=period_label,
                            file_path=str(pdf_path),
                            source_url=file_url,
                            parse_status="pending",
                        )
                        session.add(doc)
                        existing_keys.add((doc_type, period_label))

                        log.info(
                            "doc_downloaded",
                            code=code,
                            period=period_label,
                            path=str(pdf_path),
                        )

                        # Only take first valid attachment per period
                        break
                    # Only process first result entry per period
                    break

                await asyncio.sleep(1.0)

    await session.commit()
    log.info("idx_doc_fetch_complete", code=code, asset_id=asset.id)
