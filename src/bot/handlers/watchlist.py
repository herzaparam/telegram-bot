"""Handlers for /add, /remove, /watchlist commands (WTCH-01, WTCH-02, WTCH-03)."""

from __future__ import annotations

import asyncio

import structlog
from sqlalchemy import func, select
from telegram import Update
from telegram.ext import ContextTypes

from src.bot.auth import is_authorized
from src.db.database import async_session_factory
from src.db.models import Asset, PriceHistory, Watchlist
from src.report.formatter import format_watchlist_message

logger = structlog.get_logger(__name__)


def _validate_stock(symbol: str) -> dict | None:
    """Validate IDX stock symbol via yfinance (synchronous)."""
    import yfinance as yf

    yf_symbol = f"{symbol}.JK"
    try:
        ticker = yf.Ticker(yf_symbol)
        info = ticker.info
        if info.get("regularMarketPrice"):
            return {
                "name": info.get("shortName") or info.get("longName") or symbol,
                "yfinance_symbol": yf_symbol,
            }
    except Exception:
        pass
    return None


def _validate_crypto(symbol: str) -> dict | None:
    """Validate crypto symbol against Binance via ccxt (synchronous)."""
    import ccxt

    try:
        exchange = ccxt.binance()
        exchange.load_markets()
        ccxt_symbol = f"{symbol}/USDT"
        if ccxt_symbol in exchange.markets:
            return {
                "name": symbol,
                "ccxt_symbol": ccxt_symbol,
            }
    except Exception:
        pass
    return None


async def add_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Add an asset to the watchlist (WTCH-01, D-10, D-11, D-12)."""
    if not is_authorized(update):
        return

    if not context.args:
        await update.message.reply_text(  # type: ignore[union-attr]
            "\u274c Please specify a symbol. Example: /add BBCA",
            parse_mode="HTML",
        )
        return

    symbol = context.args[0].upper()
    chat_id = str(update.effective_chat.id)  # type: ignore[union-attr]
    logger.info("add_command", symbol=symbol, chat_id=chat_id)

    async with async_session_factory() as session:
        # Check if asset exists in DB
        result = await session.execute(
            select(Asset).where(func.upper(Asset.symbol) == symbol)
        )
        asset = result.scalar_one_or_none()

        if asset:
            # Check if already in watchlist
            wl_result = await session.execute(
                select(Watchlist).where(Watchlist.asset_id == asset.id)
            )
            if wl_result.scalar_one_or_none():
                await update.message.reply_text(  # type: ignore[union-attr]
                    f"\u2139\ufe0f <b>{symbol}</b> is already in your watchlist.",
                    parse_mode="HTML",
                )
                return

            # Add to watchlist
            session.add(Watchlist(asset_id=asset.id, added_by_chat_id=chat_id))
            await session.commit()
            await update.message.reply_text(  # type: ignore[union-attr]
                f"\u2705 Added <b>{symbol}</b> ({asset.name or symbol}) to watchlist.",
                parse_mode="HTML",
            )
            return

        # Asset not in DB -- validate externally
        loop = asyncio.get_event_loop()

        # Try stock validation first
        stock_info = await loop.run_in_executor(None, _validate_stock, symbol)
        if stock_info:
            new_asset = Asset(
                symbol=symbol,
                name=stock_info["name"],
                asset_type="stock",
                exchange="IDX",
                yfinance_symbol=stock_info["yfinance_symbol"],
            )
            session.add(new_asset)
            await session.flush()
            session.add(Watchlist(asset_id=new_asset.id, added_by_chat_id=chat_id))
            await session.commit()

            # Check if price history exists
            ph_result = await session.execute(
                select(func.count()).select_from(PriceHistory).where(
                    PriceHistory.asset_id == new_asset.id
                )
            )
            has_prices = (ph_result.scalar() or 0) > 0

            msg = f"\u2705 Added <b>{symbol}</b> ({new_asset.name}) to watchlist."
            if not has_prices:
                msg += (
                    "\n\n\u2139\ufe0f Price data will be fetched on next pipeline run. "
                    "Signals available tomorrow."
                )
            await update.message.reply_text(msg, parse_mode="HTML")  # type: ignore[union-attr]
            return

        # Try crypto validation
        crypto_info = await loop.run_in_executor(None, _validate_crypto, symbol)
        if crypto_info:
            new_asset = Asset(
                symbol=symbol,
                name=crypto_info["name"],
                asset_type="crypto",
                exchange="binance",
                ccxt_symbol=crypto_info["ccxt_symbol"],
            )
            session.add(new_asset)
            await session.flush()
            session.add(Watchlist(asset_id=new_asset.id, added_by_chat_id=chat_id))
            await session.commit()

            ph_result = await session.execute(
                select(func.count()).select_from(PriceHistory).where(
                    PriceHistory.asset_id == new_asset.id
                )
            )
            has_prices = (ph_result.scalar() or 0) > 0

            msg = f"\u2705 Added <b>{symbol}</b> ({new_asset.name}) to watchlist."
            if not has_prices:
                msg += (
                    "\n\n\u2139\ufe0f Price data will be fetched on next pipeline run. "
                    "Signals available tomorrow."
                )
            await update.message.reply_text(msg, parse_mode="HTML")  # type: ignore[union-attr]
            return

        # Neither validates
        await update.message.reply_text(  # type: ignore[union-attr]
            f"\u274c Symbol <code>{symbol}</code> not found.\n"
            "\n"
            "Check the symbol and try again. Examples:\n"
            "- IDX stocks: /add BBCA, /add TLKM\n"
            "- Crypto: /add BTC, /add ETH",
            parse_mode="HTML",
        )


async def remove_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Remove an asset from the watchlist (WTCH-02)."""
    if not is_authorized(update):
        return

    if not context.args:
        await update.message.reply_text(  # type: ignore[union-attr]
            "\u274c Please specify a symbol. Example: /remove BBCA",
            parse_mode="HTML",
        )
        return

    symbol = context.args[0].upper()
    logger.info("remove_command", symbol=symbol, chat_id=update.effective_chat.id)  # type: ignore[union-attr]

    async with async_session_factory() as session:
        result = await session.execute(
            select(Watchlist)
            .join(Asset, Watchlist.asset_id == Asset.id)
            .where(func.upper(Asset.symbol) == symbol)
        )
        wl_entry = result.scalar_one_or_none()

        if wl_entry:
            await session.delete(wl_entry)
            await session.commit()
            await update.message.reply_text(  # type: ignore[union-attr]
                f"\u2705 Removed <b>{symbol}</b> from watchlist.",
                parse_mode="HTML",
            )
        else:
            await update.message.reply_text(  # type: ignore[union-attr]
                f"\u2139\ufe0f <b>{symbol}</b> is not in your watchlist.",
                parse_mode="HTML",
            )


async def watchlist_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show current watchlist (WTCH-03)."""
    if not is_authorized(update):
        return

    logger.info("watchlist_command", chat_id=update.effective_chat.id)  # type: ignore[union-attr]

    async with async_session_factory() as session:
        result = await session.execute(
            select(Asset.symbol, Asset.name, Asset.exchange)
            .join(Watchlist, Watchlist.asset_id == Asset.id)
            .order_by(Asset.symbol)
        )
        rows = result.all()

    assets = [(row.symbol, row.name or row.symbol, row.exchange or "Unknown") for row in rows]
    msg = format_watchlist_message(assets)
    await update.message.reply_text(msg, parse_mode="HTML")  # type: ignore[union-attr]
