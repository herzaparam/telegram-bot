"""Handler for /portfolio command (TBOT-12).

Shows portfolio-level risk analysis: correlation heatmap, VaR, concentration,
stress tests, and risk-adjusted metrics.

Does NOT import pipeline modules (two-process boundary).
Imports from src.risk/ (pure computation) are safe for both processes.
"""

from __future__ import annotations

from datetime import datetime, timedelta

import pandas as pd
import structlog
from sqlalchemy import select
from telegram import Update
from telegram.ext import ContextTypes

from src.bot.auth import is_authorized
from src.db.database import async_session_factory
from src.db.models import Asset, PriceHistory, Watchlist
from src.engines.valuation import IDX_SECTOR_MAP
from src.report.formatter import split_report
from src.risk.concentration import compute_concentration
from src.risk.correlation import compute_correlation_matrix, format_correlation_heatmap
from src.risk.metrics import compute_risk_metrics
from src.risk.stress import run_stress_test
from src.risk.var import compute_historical_var

logger = structlog.get_logger(__name__)

CHART_EMOJI = "\U0001f4ca"
ERROR_EMOJI = "\u274c"
WARNING_EMOJI = "\u26a0\ufe0f"
INFO_EMOJI = "\u2139\ufe0f"


async def portfolio_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /portfolio command -- show portfolio risk analysis."""
    if not is_authorized(update):
        return

    logger.info("portfolio_command", chat_id=update.effective_chat.id)  # type: ignore[union-attr]

    try:
        async with async_session_factory() as session:
            # Query all watchlist assets
            stmt = (
                select(Asset)
                .join(Watchlist, Watchlist.asset_id == Asset.id)
                .order_by(Asset.symbol)
            )
            result = await session.execute(stmt)
            assets_list = result.scalars().all()

            if not assets_list:
                await update.message.reply_text(  # type: ignore[union-attr]
                    f"{INFO_EMOJI} Your watchlist is empty. Add assets with /add first.",
                    parse_mode="HTML",
                )
                return

            # Fetch price history (last 252 days) for all watchlist assets
            cutoff = datetime.now() - timedelta(days=365)
            asset_ids = [a.id for a in assets_list]

            price_stmt = (
                select(PriceHistory)
                .where(
                    PriceHistory.asset_id.in_(asset_ids),
                    PriceHistory.time >= cutoff,
                )
                .order_by(PriceHistory.asset_id, PriceHistory.time)
            )
            price_result = await session.execute(price_stmt)
            price_rows = price_result.scalars().all()

    except Exception:
        logger.exception("portfolio_db_error")
        await update.message.reply_text(  # type: ignore[union-attr]
            f"{ERROR_EMOJI} Portfolio data unavailable. Try again later.",
            parse_mode="HTML",
        )
        return

    # Build price_data dict: {symbol: pd.Series of close prices}
    # and assets dict for concentration/stress
    asset_map = {a.id: a for a in assets_list}
    price_data: dict[str, pd.Series] = {}
    for row in price_rows:
        sym = asset_map[row.asset_id].symbol
        if sym not in price_data:
            price_data[sym] = pd.Series(dtype=float)
        price_data[sym] = pd.concat([
            price_data[sym],
            pd.Series([row.close], index=[pd.Timestamp(row.time)]),
        ])

    assets_dicts = [
        {"symbol": a.symbol, "asset_type": a.asset_type}
        for a in assets_list
    ]

    # Build sections
    sections: list[str] = []

    # Header
    header = f"<b>{CHART_EMOJI} Portfolio Risk Analysis</b>\n{len(assets_list)} assets in watchlist"

    # Section 1: Correlation Heatmap
    if len(price_data) >= 2:
        try:
            corr_result = compute_correlation_matrix(price_data)
            heatmap = format_correlation_heatmap(corr_result)
            corr_section = f"<b>Correlation Heatmap</b>\n{heatmap}"
            if corr_result.high_pairs:
                alerts = ", ".join(
                    f"{a}/{b} {v:.2f}" for a, b, v in corr_result.high_pairs[:5]
                )
                corr_section += f"\n{WARNING_EMOJI} High: {alerts}"
            sections.append(corr_section)
        except Exception:
            logger.debug("correlation_computation_failed", exc_info=True)

    # Compute portfolio-level equal-weight daily returns
    portfolio_returns: pd.Series | None = None
    if price_data:
        returns_list = []
        for sym, series in price_data.items():
            if len(series) > 1:
                ret = series.sort_index().pct_change().dropna()
                returns_list.append(ret)
        if returns_list:
            returns_df = pd.concat(returns_list, axis=1).dropna()
            if not returns_df.empty:
                portfolio_returns = returns_df.mean(axis=1)

    # Section 2: Concentration
    try:
        conc_result = compute_concentration(assets_dicts, IDX_SECTOR_MAP)
        conc_lines = ["<b>Concentration</b>"]
        # Top sectors
        sorted_sectors = sorted(conc_result.sector_pct.items(), key=lambda x: x[1], reverse=True)
        sector_parts = [f"{s} {v:.0f}%" for s, v in sorted_sectors[:5]]
        conc_lines.append(" | ".join(sector_parts))
        conc_lines.append(f"Max single asset: {conc_result.max_single_pct:.1f}%")
        conc_lines.append(f"IDR: {conc_result.idr_pct:.0f}% | USD: {conc_result.usd_pct:.0f}%")
        sections.append("\n".join(conc_lines))
    except Exception:
        logger.debug("concentration_computation_failed", exc_info=True)

    # Section 3: Value at Risk
    if portfolio_returns is not None:
        try:
            var_result = compute_historical_var(portfolio_returns)
            var_lines = ["<b>Value at Risk</b>"]
            var_lines.append(
                f"Daily: {var_result.daily_var_95 * 100:.1f}% (95%) | "
                f"{var_result.daily_var_99 * 100:.1f}% (99%)"
            )
            var_lines.append(
                f"Weekly: {var_result.weekly_var_95 * 100:.1f}% (95%) | "
                f"{var_result.weekly_var_99 * 100:.1f}% (99%)"
            )
            var_lines.append(
                f"Max Drawdown: {var_result.max_drawdown * 100:.1f}% "
                f"({var_result.max_drawdown_start} to {var_result.max_drawdown_end})"
            )
            sections.append("\n".join(var_lines))
        except ValueError as e:
            sections.append(f"<b>Value at Risk</b>\n{INFO_EMOJI} {e}")
        except Exception:
            logger.debug("var_computation_failed", exc_info=True)

    # Section 4: Risk Metrics
    if portfolio_returns is not None and len(portfolio_returns) > 0:
        try:
            metrics_result = compute_risk_metrics(portfolio_returns)
            met_lines = ["<b>Risk Metrics</b>"]
            met_lines.append(
                f"Sharpe: {metrics_result.sharpe_ratio:.2f} | "
                f"Sortino: {metrics_result.sortino_ratio:.2f}"
            )
            met_lines.append(
                f"Ann. Return: {metrics_result.annualized_return * 100:.1f}% | "
                f"Ann. Vol: {metrics_result.annualized_volatility * 100:.1f}%"
            )
            sections.append("\n".join(met_lines))
        except Exception:
            logger.debug("metrics_computation_failed", exc_info=True)

    # Section 5: Stress Test
    try:
        stress_results = run_stress_test(assets_dicts)
        if stress_results:
            stress_lines = ["<b>Stress Test</b>"]
            for sr in stress_results:
                stress_lines.append(
                    f"{sr.scenario_name}: {sr.portfolio_impact * 100:.1f}%"
                )
            sections.append("\n".join(stress_lines))
    except Exception:
        logger.debug("stress_test_failed", exc_info=True)

    # Footer note
    sections.append(f"<i>Based on equal-weight portfolio assumption</i>")

    # Send using split_report for long messages
    messages = split_report(header, sections)
    for msg in messages:
        await update.message.reply_text(msg, parse_mode="HTML")  # type: ignore[union-attr]
