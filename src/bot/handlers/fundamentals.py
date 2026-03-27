"""Handler for /fundamentals command (TBOT-13).

Reads financial data from DB tables (two-process boundary).
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
from src.db.models import Asset, FinancialData, FinancialDoc, StockFundamental, Watchlist
from src.report.formatter import (
    format_dividend_analysis,
    format_earnings_quality,
    format_five_year_trends,
    format_fundamentals_dashboard,
    split_report,
)

logger = structlog.get_logger(__name__)

INFO_EMOJI = "\u2139\ufe0f"
ERROR_EMOJI = "\u274c"
CHART_EMOJI = "\U0001f4ca"


async def fundamentals_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /fundamentals command -- show ratio dashboard with QoQ trends."""
    if not is_authorized(update):
        return

    logger.info("fundamentals_command", chat_id=update.effective_chat.id, args=context.args)  # type: ignore[union-attr]

    if not context.args:
        await update.message.reply_text(  # type: ignore[union-attr]
            f"{ERROR_EMOJI} Please specify an IDX stock symbol. Example: /fundamentals BBCA",
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
                f"{INFO_EMOJI} Fundamentals dashboard not available for crypto assets -- "
                f"use /report {asset.symbol} for signal analysis.",
                parse_mode="HTML",
            )
            return

        # Load FinancialData for latest 2 periods (for QoQ)
        fd_stmt = (
            select(FinancialData)
            .where(FinancialData.asset_id == asset.id)
            .order_by(FinancialData.period_date.desc())
        )
        fd_result = await session.execute(fd_stmt)
        fd_rows = fd_result.scalars().all()

        # Load StockFundamental (yfinance cached)
        sf_stmt = select(StockFundamental).where(StockFundamental.asset_id == asset.id)
        sf_result = await session.execute(sf_stmt)
        fundamental = sf_result.scalar_one_or_none()

    # No data at all
    if not fd_rows and not fundamental:
        await update.message.reply_text(  # type: ignore[union-attr]
            f"{CHART_EMOJI} <b>Fundamentals -- {symbol} ({asset.name or symbol})</b>\n\n"
            "No fundamental data available yet.\n\n"
            "The pipeline fetches financial data weekly. Check back after the next pipeline run, "
            f"or use /valuation {symbol} for a market-data estimate.",
            parse_mode="HTML",
        )
        return

    # Group FinancialData by period
    periods: dict[str, dict[str, float]] = {}
    for fd in fd_rows:
        periods.setdefault(fd.period, {})[fd.metric_name] = fd.metric_value or 0.0

    # Determine source and build display data
    has_pdf_data = bool(periods)
    source_label = "IDX financial report" if has_pdf_data else "Market data (yfinance)"

    # Get latest 2 distinct periods for QoQ comparison
    sorted_periods = sorted(periods.keys(), reverse=True)
    latest_period_key = sorted_periods[0] if sorted_periods else "N/A"
    latest = periods.get(latest_period_key, {}) if sorted_periods else {}
    previous = periods.get(sorted_periods[1], {}) if len(sorted_periods) > 1 else {}

    # Build profitability dict
    profitability: dict[str, dict] = {}
    for metric in ("net_margin", "roe", "gross_margin"):
        val = latest.get(metric)
        if val is not None:
            prev_val = previous.get(metric)
            qoq = (val - prev_val) if prev_val is not None else 0.0
            if abs(qoq) < 0.02:
                trend = "flat"
            elif qoq > 0:
                trend = "up"
            else:
                trend = "down"
            profitability[metric] = {"value": val, "qoq_change": qoq, "trend": trend}

    # If no PDF data, fill from StockFundamental
    if not profitability and fundamental:
        if fundamental.return_on_equity is not None:
            profitability["roe"] = {
                "value": fundamental.return_on_equity,
                "qoq_change": 0.0,
                "trend": "flat",
            }

    # Build valuation ratios
    valuation_ratios: dict[str, float] = {}
    if fundamental:
        if fundamental.trailing_pe is not None:
            valuation_ratios["pe"] = fundamental.trailing_pe
        if fundamental.price_to_book is not None:
            valuation_ratios["pb"] = fundamental.price_to_book

    # Build leverage dict
    leverage: dict[str, dict] = {}
    de_val = latest.get("debt_equity")
    if de_val is not None:
        de_prev = previous.get("debt_equity")
        de_qoq = (de_val - de_prev) / de_prev if de_prev and de_prev != 0 else 0.0
        if abs(de_qoq) < 0.05:
            de_trend = "flat"
        elif de_qoq > 0:
            de_trend = "up"
        else:
            de_trend = "down"
        leverage["debt_equity"] = {"value": de_val, "qoq_change": de_qoq, "trend": de_trend}
    elif fundamental and fundamental.debt_to_equity is not None:
        leverage["debt_equity"] = {
            "value": fundamental.debt_to_equity,
            "qoq_change": 0.0,
            "trend": "flat",
        }

    # Build cash flow dict
    cash_flow: dict[str, float] = {}
    for cf_key in ("operating_cash_flow", "free_cash_flow", "capex"):
        val = latest.get(cf_key)
        if val is not None:
            # Map to display keys
            display_key = {
                "operating_cash_flow": "operating_cf",
                "free_cash_flow": "fcf",
                "capex": "capex",
            }.get(cf_key, cf_key)
            cash_flow[display_key] = val

    # Cross-validation warnings (D-09)
    cross_warnings: list[str] | None = None
    if has_pdf_data and fundamental:
        # Compare revenue if available
        pdf_revenue = latest.get("revenue")
        if pdf_revenue and fundamental.revenue_growth is not None:
            # We only have revenue_growth from yfinance, not absolute revenue
            # So skip absolute comparison for now -- only warn if we had totalRevenue
            pass

    msg = format_fundamentals_dashboard(
        symbol=asset.symbol,
        asset_name=asset.name or asset.symbol,
        profitability=profitability,
        valuation_ratios=valuation_ratios,
        leverage=leverage,
        cash_flow=cash_flow,
        source_label=source_label,
        period=latest_period_key,
        cross_validation_warnings=cross_warnings,
    )

    # Enhanced sections for stock assets only (D-17)
    enhanced_sections: list[str] = []
    if asset.asset_type == "stock":
        # Build financial_data list of dicts for enhanced formatters
        financial_data_dicts = [
            {
                "metric_name": fd.metric_name,
                "metric_value": fd.metric_value,
                "period_date": fd.period_date,
            }
            for fd in fd_rows
        ]

        # 5-year trends
        trends_section = format_five_year_trends(financial_data_dicts)
        if trends_section:
            enhanced_sections.append(trends_section)

        # Earnings quality
        eq_section = format_earnings_quality(financial_data_dicts)
        if eq_section:
            enhanced_sections.append(eq_section)

        # Dividend analysis
        fund_dict: dict = {}
        if fundamental and isinstance(fundamental.dividend_yield, (int, float)):
            fund_dict["dividend_yield"] = fundamental.dividend_yield
        div_section = format_dividend_analysis(fund_dict, financial_data_dicts)
        if div_section:
            enhanced_sections.append(div_section)
    elif asset.asset_type == "crypto":
        enhanced_sections.append(
            f"{INFO_EMOJI} Enhanced fundamentals available for IDX stocks only"
        )

    # Combine and send, using split_report for long messages
    if enhanced_sections:
        cards = [msg] + enhanced_sections
        messages = split_report("", cards)
        for m in messages:
            # strip leading newlines from empty header
            text = m.lstrip("\n")
            if text:
                await update.message.reply_text(text, parse_mode="HTML")  # type: ignore[union-attr]
    else:
        await update.message.reply_text(msg, parse_mode="HTML")  # type: ignore[union-attr]
