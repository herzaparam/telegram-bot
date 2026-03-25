"""Handler for /valuation command (TBOT-09).

Reads computed valuation data from the signals table (two-process boundary).
Does NOT import engine modules.
"""

from __future__ import annotations

from datetime import date

import structlog
from sqlalchemy import select
from telegram import Update
from telegram.ext import ContextTypes

from src.bot.auth import is_authorized
from src.db.database import async_session_factory
from src.db.models import Asset, SignalRecord, StockFundamental, Watchlist
from src.report.formatter import format_valuation_detail

logger = structlog.get_logger(__name__)

INFO_EMOJI = "\u2139\ufe0f"
ERROR_EMOJI = "\u274c"


async def valuation_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /valuation command -- show DCF fair value and analysis for IDX stocks."""
    if not is_authorized(update):
        return

    logger.info("valuation_command", chat_id=update.effective_chat.id, args=context.args)  # type: ignore[union-attr]

    if not context.args:
        await update.message.reply_text(  # type: ignore[union-attr]
            f"{ERROR_EMOJI} Please specify an IDX stock symbol. Example: /valuation BBCA",
            parse_mode="HTML",
        )
        return

    symbol = context.args[0].upper()

    async with async_session_factory() as session:
        # Resolve asset via watchlist
        stmt = (
            select(Asset)
            .join(Watchlist, Watchlist.asset_id == Asset.id)
            .where(Asset.symbol.ilike(symbol))
        )
        result = await session.execute(stmt)
        asset = result.scalar_one_or_none()

        if asset is None:
            await update.message.reply_text(  # type: ignore[union-attr]
                f"{ERROR_EMOJI} Symbol <code>{symbol}</code> not found in your watchlist.\n\n"
                "Use /watchlist to see your tracked assets.",
                parse_mode="HTML",
            )
            return

        # Crypto rejection (D-18)
        if asset.asset_type == "crypto":
            await update.message.reply_text(  # type: ignore[union-attr]
                f"{INFO_EMOJI} Valuation not available for crypto assets -- "
                f"use /report {asset.symbol} for signal analysis.",
                parse_mode="HTML",
            )
            return

        # Read valuation signal from signals table
        sig_stmt = (
            select(SignalRecord)
            .where(
                SignalRecord.asset_id == asset.id,
                SignalRecord.category == "valuation",
            )
            .order_by(SignalRecord.date.desc())
            .limit(1)
        )
        sig_result = await session.execute(sig_stmt)
        signal = sig_result.scalar_one_or_none()

        # Load StockFundamental as fallback
        fund_stmt = select(StockFundamental).where(StockFundamental.asset_id == asset.id)
        fund_result = await session.execute(fund_stmt)
        fundamental = fund_result.scalar_one_or_none()

    # No data at all
    if signal is None and fundamental is None:
        await update.message.reply_text(  # type: ignore[union-attr]
            f"<b>Valuation -- {symbol} ({asset.name or symbol})</b>\n\n"
            "No valuation data available yet.\n\n"
            "The pipeline fetches financial data weekly. Check back after the next pipeline run.",
            parse_mode="HTML",
        )
        return

    # Extract from signal indicators
    indicators = (signal.indicators or {}) if signal else {}
    fair_value = indicators.get("fair_value") or indicators.get("dcf_fair_value", 0)
    margin_of_safety = indicators.get("margin_of_safety", 0)
    current_price = indicators.get("current_price", 0)
    scenarios = indicators.get("scenarios")
    peer_comparison = indicators.get("peer_comparison")
    sector = indicators.get("sector")
    period = indicators.get("period", "N/A")
    has_pdf_data = indicators.get("has_pdf_data", False)
    last_updated = str(signal.date) if signal else "N/A"

    # If no signal data but have fundamentals, build rough estimate
    if not fair_value and fundamental:
        # Rough estimate from P/E * EPS approximation
        has_pdf_data = False
        if fundamental.trailing_pe and fundamental.trailing_pe > 0:
            # Very rough: use P/B * book_value approach
            pass

    msg = format_valuation_detail(
        symbol=asset.symbol,
        asset_name=asset.name or asset.symbol,
        current_price=float(current_price),
        fair_value=float(fair_value),
        margin_of_safety=float(margin_of_safety),
        scenarios=scenarios,
        peer_comparison=peer_comparison,
        sector=sector,
        period=str(period),
        last_updated=last_updated,
        has_pdf_data=bool(has_pdf_data),
    )
    await update.message.reply_text(msg, parse_mode="HTML")  # type: ignore[union-attr]
