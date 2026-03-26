"""Handler for /compare command (TBOT-10).

Side-by-side sector comparison for IDX stocks. Reads from stock_fundamentals table.
Does NOT import pipeline modules (two-process boundary).
"""

from __future__ import annotations

import structlog
from sqlalchemy import select
from telegram import Update
from telegram.ext import ContextTypes

from src.bot.auth import is_authorized
from src.db.database import async_session_factory
from src.db.models import Asset, StockFundamental
from src.engines.valuation import IDX_SECTOR_MAP
from src.report.formatter import MAX_MESSAGE_LENGTH, format_compare_table

logger = structlog.get_logger(__name__)

ERROR_EMOJI = "\u274c"
WARNING_EMOJI = "\u26a0\ufe0f"


async def compare_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /compare command -- side-by-side sector comparison for IDX stocks."""
    if not is_authorized(update):
        return

    logger.info("compare_command", chat_id=update.effective_chat.id, args=context.args)  # type: ignore[union-attr]

    if not context.args or len(context.args) < 2:
        await update.message.reply_text(  # type: ignore[union-attr]
            f"{ERROR_EMOJI} Please specify 2-5 IDX stock symbols. Example: /compare BBCA BBRI BMRI",
            parse_mode="HTML",
        )
        return

    if len(context.args) > 5:
        await update.message.reply_text(  # type: ignore[union-attr]
            f"{ERROR_EMOJI} Maximum 5 symbols per comparison. Example: /compare BBCA BBRI BMRI",
            parse_mode="HTML",
        )
        return

    symbols = [a.upper() for a in context.args[:5]]

    try:
        async with async_session_factory() as session:
            # Look up all assets
            stock_assets: list = []
            crypto_symbols: list[str] = []

            for sym in symbols:
                asset_stmt = select(Asset).where(Asset.symbol.ilike(sym))
                asset_result = await session.execute(asset_stmt)
                asset = asset_result.scalar_one_or_none()

                if asset is None:
                    # Try with prefix match for .JK suffix
                    asset_stmt2 = select(Asset).where(Asset.symbol.ilike(f"{sym}%"))
                    asset_result2 = await session.execute(asset_stmt2)
                    asset = asset_result2.scalar_one_or_none()

                if asset is None:
                    continue  # Skip unknown symbols

                if asset.asset_type == "crypto":
                    crypto_symbols.append(sym)
                else:
                    stock_assets.append(asset)

            # Build warning prefix if crypto was filtered
            prefix = ""
            if crypto_symbols:
                crypto_list = ", ".join(crypto_symbols)
                prefix = (
                    f"{WARNING_EMOJI} Skipping crypto assets: {crypto_list}. "
                    "/compare works with IDX stocks only.\n\n"
                )

            if len(stock_assets) < 2:
                await update.message.reply_text(  # type: ignore[union-attr]
                    prefix + f"{ERROR_EMOJI} Please specify at least 2 IDX stock symbols to compare. "
                    "Example: /compare BBCA BBRI",
                    parse_mode="HTML",
                )
                return

            # Query StockFundamental for each stock
            data: list[dict] = []
            resolved_symbols: list[str] = []

            for asset in stock_assets:
                sf_stmt = select(StockFundamental).where(StockFundamental.asset_id == asset.id)
                sf_result = await session.execute(sf_stmt)
                fundamental = sf_result.scalar_one_or_none()

                sym = asset.symbol
                resolved_symbols.append(sym)

                if fundamental:
                    data.append({
                        "symbol": sym,
                        "pe": fundamental.trailing_pe,
                        "pb": fundamental.price_to_book,
                        "roe": fundamental.return_on_equity,
                        "debt_to_equity": fundamental.debt_to_equity,
                        "revenue_cagr": fundamental.revenue_growth,
                    })
                else:
                    data.append({
                        "symbol": sym,
                        "pe": None,
                        "pb": None,
                        "roe": None,
                        "debt_to_equity": None,
                        "revenue_cagr": None,
                    })

            # Determine sector
            sectors = [IDX_SECTOR_MAP.get(a.symbol, "Unknown") for a in stock_assets]
            unique_sectors = set(sectors)
            sector = sectors[0] if len(unique_sectors) == 1 else "Mixed"

    except Exception:
        logger.exception("compare_db_error")
        await update.message.reply_text(  # type: ignore[union-attr]
            f"{ERROR_EMOJI} Comparison data unavailable. Please try again later.",
            parse_mode="HTML",
        )
        return

    msg = format_compare_table(resolved_symbols, data, sector)
    if not msg:
        await update.message.reply_text(  # type: ignore[union-attr]
            f"{ERROR_EMOJI} No fundamental data available for comparison.",
            parse_mode="HTML",
        )
        return

    full_msg = prefix + msg if prefix else msg

    if len(full_msg) > MAX_MESSAGE_LENGTH:
        # Split into prefix + table
        if prefix:
            await update.message.reply_text(prefix.strip(), parse_mode="HTML")  # type: ignore[union-attr]
            await update.message.reply_text(msg, parse_mode="HTML")  # type: ignore[union-attr]
        else:
            # Table itself too long -- unlikely with max 5 symbols
            await update.message.reply_text(full_msg[:MAX_MESSAGE_LENGTH], parse_mode="HTML")  # type: ignore[union-attr]
    else:
        await update.message.reply_text(full_msg, parse_mode="HTML")  # type: ignore[union-attr]
