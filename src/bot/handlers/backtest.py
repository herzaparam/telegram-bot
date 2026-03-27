"""Handler for /backtest command (TBOT-08).

Spawns subprocess to run backtest (two-process boundary).
Does NOT import src/pipeline or src/llm.
"""

from __future__ import annotations

import asyncio
import json
import sys
from datetime import date

import structlog
from sqlalchemy import select
from telegram import Update
from telegram.ext import ContextTypes

from src.bot.auth import is_authorized
from src.db.database import async_session_factory
from src.db.models import Asset, BacktestResult

logger = structlog.get_logger(__name__)

VALID_PERIODS = {"7d", "30d", "90d"}
CHART_EMOJI = "\U0001f4ca"
ERROR_EMOJI = "\u274c"
CLOCK_EMOJI = "\u23f3"


async def _format_backtest_result(data: dict) -> str:
    """Format backtest result dict as HTML message."""
    symbol = data.get("symbol", "?")
    period = data.get("period", "?")
    win_rate = data.get("win_rate", 0) * 100
    total_return = data.get("total_return", 0) * 100
    buy_hold = data.get("buy_hold_return", 0) * 100
    max_dd = data.get("max_drawdown", 0) * 100
    sharpe = data.get("sharpe_ratio")
    days = data.get("days_tested", 0)

    diff = total_return - buy_hold
    if diff >= 0:
        comparison = f"Signal outperformed buy-and-hold by +{diff:.1f}%"
    else:
        comparison = f"Signal underperformed buy-and-hold by {diff:.1f}%"

    sharpe_str = f"{sharpe:.1f}" if sharpe is not None else "N/A"

    return (
        f"<b>{CHART_EMOJI} Backtest: {symbol} ({period})</b>\n\n"
        f"Win Rate: {win_rate:.1f}%\n"
        f"Total Return: {total_return:+.1f}%\n"
        f"Buy &amp; Hold: {buy_hold:+.1f}%\n"
        f"Max Drawdown: {max_dd:.1f}%\n"
        f"Sharpe Ratio: {sharpe_str}\n"
        f"Days Tested: {days}\n\n"
        f"{comparison}\n\n"
        f"<i>Based on full pipeline replay with engines + LLM verdict</i>"
    )


async def backtest_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /backtest command -- run historical signal backtest via subprocess."""
    if not is_authorized(update):
        return

    logger.info("backtest_command", chat_id=update.effective_chat.id)  # type: ignore[union-attr]

    # Parse args
    args = context.args or []
    if not args:
        await update.message.reply_text(  # type: ignore[union-attr]
            f"{CHART_EMOJI} <b>/backtest</b> - Run historical signal replay\n\n"
            "Usage: <code>/backtest BTC 30d</code>\n"
            "Periods: 7d, 30d, 90d\n\n"
            "Replays all engines + LLM verdict for each historical day.",
            parse_mode="HTML",
        )
        return

    symbol = args[0].upper()
    period = args[1] if len(args) > 1 else "30d"

    if period not in VALID_PERIODS:
        await update.message.reply_text(  # type: ignore[union-attr]
            f"{ERROR_EMOJI} Invalid period: {period}\nValid periods: 7d, 30d, 90d",
            parse_mode="HTML",
        )
        return

    # Check for cached result first (no subprocess needed)
    try:
        async with async_session_factory() as session:
            asset_result = await session.execute(
                select(Asset).where(Asset.symbol.ilike(symbol))
            )
            asset = asset_result.scalar_one_or_none()
            if asset is not None:
                cached = await session.execute(
                    select(BacktestResult).where(
                        BacktestResult.asset_id == asset.id,
                        BacktestResult.period == period,
                        BacktestResult.run_date == date.today(),
                    )
                )
                cached_result = cached.scalar_one_or_none()
                if cached_result is not None:
                    result_data = {
                        "symbol": symbol,
                        "period": period,
                        "win_rate": cached_result.win_rate,
                        "total_return": cached_result.total_return,
                        "buy_hold_return": cached_result.buy_hold_return,
                        "max_drawdown": cached_result.max_drawdown,
                        "sharpe_ratio": cached_result.sharpe_ratio,
                        "days_tested": cached_result.daily_results.get("days_tested", 0) if cached_result.daily_results else 0,
                    }
                    text = await _format_backtest_result(result_data)
                    await update.message.reply_text(text, parse_mode="HTML")  # type: ignore[union-attr]
                    return
    except Exception:
        logger.exception("backtest_cache_check_error")

    # Send processing message
    msg = await update.message.reply_text(  # type: ignore[union-attr]
        f"{CLOCK_EMOJI} Running backtest for {symbol} ({period})... This may take several minutes.",
        parse_mode="HTML",
    )

    try:
        # Spawn subprocess (two-process boundary)
        proc = await asyncio.create_subprocess_exec(
            sys.executable, "-m", "src.data.backtest",
            "--asset", symbol, "--period", period,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=600)
        except asyncio.TimeoutError:
            proc.kill()
            await msg.edit_text(
                f"{ERROR_EMOJI} Backtest timed out after 10 minutes. Try a shorter period.",
                parse_mode="HTML",
            )
            return

        if proc.returncode != 0:
            error_msg = stderr.decode().strip() if stderr else "Unknown error"
            logger.warning("backtest_subprocess_error", returncode=proc.returncode, stderr=error_msg)
            await msg.edit_text(
                f"{ERROR_EMOJI} Backtest failed: {error_msg[:200]}",
                parse_mode="HTML",
            )
            return

        # Parse result JSON
        try:
            data = json.loads(stdout.decode())
        except (json.JSONDecodeError, UnicodeDecodeError):
            await msg.edit_text(
                f"{ERROR_EMOJI} Failed to parse backtest results.",
                parse_mode="HTML",
            )
            return

        if data.get("status") == "error":
            await msg.edit_text(
                f"{ERROR_EMOJI} {data.get('message', 'Backtest failed')}",
                parse_mode="HTML",
            )
            return

        # Format and display results
        result_text = await _format_backtest_result(data)
        await msg.edit_text(result_text, parse_mode="HTML")

    except Exception:
        logger.exception("backtest_handler_error")
        await msg.edit_text(
            f"{ERROR_EMOJI} An unexpected error occurred during backtest.",
            parse_mode="HTML",
        )
