"""Handler for /duediligence command (TBOT-11).

Shows full due diligence report for IDX stocks. Reads from due_diligence_reports table.
Does NOT import pipeline modules (two-process boundary).
"""

from __future__ import annotations

import structlog
from sqlalchemy import select
from telegram import Update
from telegram.ext import ContextTypes

from src.bot.auth import is_authorized
from src.db.database import async_session_factory
from src.db.models import Asset, DueDiligenceReport, OwnershipSnapshot
from src.report.formatter import format_dd_report

logger = structlog.get_logger(__name__)

INFO_EMOJI = "\u2139\ufe0f"
ERROR_EMOJI = "\u274c"
CHART_EMOJI = "\U0001f4ca"


async def duediligence_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /duediligence command -- show full DD report for IDX stocks."""
    if not is_authorized(update):
        return

    logger.info("duediligence_command", chat_id=update.effective_chat.id, args=context.args)  # type: ignore[union-attr]

    if not context.args:
        await update.message.reply_text(  # type: ignore[union-attr]
            f"{ERROR_EMOJI} Please specify an IDX stock symbol. Example: /duediligence BBCA",
            parse_mode="HTML",
        )
        return

    symbol = context.args[0].upper()

    try:
        async with async_session_factory() as session:
            # Find asset -- don't require watchlist membership
            asset_stmt = (
                select(Asset)
                .where(Asset.symbol.ilike(symbol))
            )
            asset_result = await session.execute(asset_stmt)
            asset = asset_result.scalar_one_or_none()

            if asset is None:
                # Try with .JK suffix fallback
                asset_stmt2 = (
                    select(Asset)
                    .where(Asset.symbol.ilike(f"{symbol}%"))
                )
                asset_result2 = await session.execute(asset_stmt2)
                asset = asset_result2.scalar_one_or_none()

            if asset is None:
                await update.message.reply_text(  # type: ignore[union-attr]
                    f"{ERROR_EMOJI} Symbol <code>{symbol}</code> not found.\n\n"
                    "Use /add to track a new asset first.",
                    parse_mode="HTML",
                )
                return

            # Crypto rejection
            if asset.asset_type == "crypto":
                await update.message.reply_text(  # type: ignore[union-attr]
                    f"{INFO_EMOJI} Due diligence is not available for crypto assets -- "
                    f"use /report {asset.symbol} for signal analysis.",
                    parse_mode="HTML",
                )
                return

            # Query latest DueDiligenceReport
            dd_stmt = (
                select(DueDiligenceReport)
                .where(DueDiligenceReport.asset_id == asset.id)
                .order_by(DueDiligenceReport.report_date.desc())
                .limit(1)
            )
            dd_result = await session.execute(dd_stmt)
            dd_report = dd_result.scalar_one_or_none()

            if dd_report is None:
                await update.message.reply_text(  # type: ignore[union-attr]
                    f"{CHART_EMOJI} No due diligence data available for {symbol}.\n\n"
                    "DD data is refreshed weekly. If this is a new stock, data will be "
                    "available after the next weekly scan.",
                    parse_mode="HTML",
                )
                return

            # Load latest OwnershipSnapshot
            own_stmt = (
                select(OwnershipSnapshot)
                .where(OwnershipSnapshot.asset_id == asset.id)
                .order_by(OwnershipSnapshot.snapshot_date.desc())
                .limit(1)
            )
            own_result = await session.execute(own_stmt)
            ownership = own_result.scalar_one_or_none()

    except Exception:
        logger.exception("duediligence_db_error")
        await update.message.reply_text(  # type: ignore[union-attr]
            f"{ERROR_EMOJI} Due diligence data unavailable. Please try again later.",
            parse_mode="HTML",
        )
        return

    # Build dd_data dict from report fields
    dd_data: dict = {
        "sector": dd_report.sector or "Unknown",
        "sector_rank": dd_report.sector_rank or {},
        "management_quality": dd_report.management_quality or {},
        "ownership_changes": dd_report.ownership_changes or {},
        "competitive_position": dd_report.competitive_position or {},
    }

    # Add ownership data if available
    if ownership:
        dd_data["shareholders"] = ownership.shareholders or []
        dd_data["public_float_pct"] = ownership.public_float_pct

    msg = format_dd_report(symbol, asset.name or symbol, dd_data)
    await update.message.reply_text(msg, parse_mode="HTML")  # type: ignore[union-attr]
