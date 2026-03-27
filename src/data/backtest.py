"""Historical signal backtest replay (TBOT-08).

Runs as subprocess: python -m src.data.backtest --asset BTC --period 30d
Stores results in backtest_results table.

This module CAN import from src/engines and src/llm because it runs
in its own process (not the bot process).
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from dataclasses import asdict, dataclass
from datetime import date, timedelta

import numpy as np
import pandas as pd
import structlog
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from src.config import settings
from src.db.database import async_session_factory
from src.db.models import Asset, BacktestResult, PriceHistory, SignalRecord
from src.engines.base import Signal

logger = structlog.get_logger(__name__)

VALID_PERIODS = {"7d": 7, "30d": 30, "90d": 90}

VERDICT_THRESHOLDS = [
    (0.6, "STRONG_BUY"),
    (0.2, "BUY"),
    (-0.2, "HOLD"),
    (-0.6, "SELL"),
]


def _score_to_verdict(score: float) -> str:
    """Map numeric score to verdict string."""
    for threshold, verdict in VERDICT_THRESHOLDS:
        if score > threshold:
            return verdict
    return "STRONG_SELL"


def _deterministic_verdict(signals: list[Signal]) -> str:
    """Produce a verdict from engine signals without LLM (fallback).

    Uses confidence-weighted average score mapped to verdict thresholds.
    """
    if not signals:
        return "HOLD"
    total_weight = sum(s.confidence for s in signals)
    if total_weight == 0:
        return "HOLD"
    weighted_score = sum(s.score * s.confidence for s in signals) / total_weight
    return _score_to_verdict(weighted_score)


async def _get_llm_verdict(signals: list[Signal], symbol: str) -> str:
    """Get LLM verdict from engine signals.

    Falls back to deterministic if LLM unavailable.
    """
    try:
        from src.llm.client import llm_completion

        # Build condensed prompt for backtest (not full decide_stage)
        signal_summary = "\n".join(
            f"- {s.category}: score={s.score:+.2f}, confidence={s.confidence:.2f}"
            for s in signals
        )
        messages = [
            {
                "role": "system",
                "content": (
                    "You are a trading signal analyzer. Given engine scores, "
                    "respond with JSON: {\"verdict\": \"STRONG_BUY|BUY|HOLD|SELL|STRONG_SELL\"}"
                ),
            },
            {
                "role": "user",
                "content": f"Asset: {symbol}\nEngine signals:\n{signal_summary}\n\nProvide verdict.",
            },
        ]
        result = await llm_completion(
            messages=messages,
            response_format={"type": "json_object"},
            timeout=12,
        )
        if result.model_used == "none":
            return _deterministic_verdict(signals)

        data = json.loads(result.content)
        verdict = data.get("verdict", "")
        if verdict in {"STRONG_BUY", "BUY", "HOLD", "SELL", "STRONG_SELL"}:
            return verdict
        return _deterministic_verdict(signals)
    except Exception:
        return _deterministic_verdict(signals)


async def run_backtest(symbol: str, period: str) -> dict:
    """Run historical backtest for an asset over a given period.

    Args:
        symbol: Asset symbol (e.g., "BTC", "BBCA").
        period: Backtest period ("7d", "30d", "90d").

    Returns:
        Dict with backtest results including win_rate, total_return, etc.

    Raises:
        ValueError: If period is not valid.
    """
    if period not in VALID_PERIODS:
        raise ValueError(f"Invalid period: {period}. Must be one of {list(VALID_PERIODS.keys())}")

    days = VALID_PERIODS[period]
    today = date.today()

    async with async_session_factory() as session:
        # Look up asset
        result = await session.execute(
            select(Asset).where(Asset.symbol.ilike(symbol))
        )
        asset = result.scalar_one_or_none()
        if asset is None:
            return {"status": "error", "message": f"Asset not found: {symbol}"}

        # Check cache
        cached = await session.execute(
            select(BacktestResult).where(
                BacktestResult.asset_id == asset.id,
                BacktestResult.period == period,
                BacktestResult.run_date == today,
            )
        )
        cached_result = cached.scalar_one_or_none()
        if cached_result is not None:
            return {
                "symbol": symbol.upper(),
                "period": period,
                "win_rate": cached_result.win_rate,
                "total_return": cached_result.total_return,
                "buy_hold_return": cached_result.buy_hold_return,
                "max_drawdown": cached_result.max_drawdown,
                "sharpe_ratio": cached_result.sharpe_ratio,
                "days_tested": cached_result.daily_results.get("days_tested", 0) if cached_result.daily_results else 0,
                "status": "complete",
            }

        # Load all price history up to today
        price_result = await session.execute(
            select(PriceHistory)
            .where(PriceHistory.asset_id == asset.id)
            .where(PriceHistory.time <= today)
            .order_by(PriceHistory.time.asc())
        )
        all_prices = price_result.scalars().all()

        if len(all_prices) < 30:
            return {"status": "error", "message": "Insufficient price history for backtest"}

        # Build full price list
        price_records = [
            {
                "time": p.time,
                "open": p.open,
                "high": p.high,
                "low": p.low,
                "close": p.close,
                "volume": p.volume,
            }
            for p in all_prices
        ]

        # Import engines (lazy to keep import footprint small at top level)
        from src.data.analyze import _get_engines_for_asset

        start_date = today - timedelta(days=days)
        end_date = today

        daily_verdicts: list[dict] = []
        daily_returns: list[float] = []

        for i, record in enumerate(price_records):
            record_date = record["time"].date() if hasattr(record["time"], "date") else record["time"]
            if record_date < start_date or record_date >= end_date:
                continue

            # Slice: only data up to and including this date (no look-ahead)
            slice_data = [r for r in price_records if r["time"] <= record["time"]]
            if len(slice_data) < 30:
                continue

            df = pd.DataFrame(slice_data)
            df.set_index("time", inplace=True)

            # Run engines
            engines = _get_engines_for_asset(asset)
            signals: list[Signal] = []
            for engine in engines:
                try:
                    signal = engine.analyze(asset.id, asset.symbol, df)
                    signals.append(signal)
                except Exception:
                    pass  # Skip failed engines

            if not signals:
                continue

            # Get verdict (LLM with deterministic fallback)
            verdict = await _get_llm_verdict(signals, asset.symbol)

            # Compute next-day return
            next_idx = i + 1
            if next_idx < len(price_records):
                current_close = record["close"]
                next_close = price_records[next_idx]["close"]
                if current_close > 0:
                    actual_return = (next_close - current_close) / current_close
                else:
                    actual_return = 0.0
            else:
                actual_return = 0.0

            # Determine if verdict was correct
            is_buy = verdict in ("STRONG_BUY", "BUY")
            is_sell = verdict in ("STRONG_SELL", "SELL")
            is_hold = verdict == "HOLD"

            if is_buy and actual_return > 0:
                correct = True
            elif is_sell and actual_return < 0:
                correct = True
            elif is_hold and abs(actual_return) < 0.01:
                correct = True
            else:
                correct = False

            # Signal-following return
            if is_buy:
                signal_return = actual_return
            elif is_sell:
                signal_return = -actual_return
            else:
                signal_return = 0.0

            daily_returns.append(signal_return)
            daily_verdicts.append({
                "date": str(record_date),
                "verdict": verdict,
                "actual_return": round(actual_return, 6),
                "signal_return": round(signal_return, 6),
                "correct": correct,
            })

            # Rate limit between LLM calls
            await asyncio.sleep(0.5)

        if not daily_verdicts:
            return {"status": "error", "message": "Insufficient price history for backtest"}

        # Compute summary stats
        wins = sum(1 for d in daily_verdicts if d["correct"])
        win_rate = wins / len(daily_verdicts) if daily_verdicts else 0.0

        total_return = sum(daily_returns) if daily_returns else 0.0

        # Buy-and-hold return
        first_record = None
        last_record = None
        for r in price_records:
            rd = r["time"].date() if hasattr(r["time"], "date") else r["time"]
            if rd >= start_date and first_record is None:
                first_record = r
            if rd < end_date:
                last_record = r
        if first_record and last_record and first_record["close"] > 0:
            buy_hold_return = (last_record["close"] - first_record["close"]) / first_record["close"]
        else:
            buy_hold_return = 0.0

        # Max drawdown from cumulative signal-following returns
        if daily_returns:
            cumulative = np.cumprod(1 + np.array(daily_returns))
            running_max = np.maximum.accumulate(cumulative)
            drawdowns = (cumulative - running_max) / running_max
            max_drawdown = float(np.min(drawdowns))
        else:
            max_drawdown = 0.0

        # Sharpe ratio (annualized)
        if len(daily_returns) > 1:
            returns_arr = np.array(daily_returns)
            ann_return = float(np.mean(returns_arr)) * 252
            ann_vol = float(np.std(returns_arr)) * np.sqrt(252)
            sharpe_ratio = (ann_return - 0.05) / ann_vol if ann_vol > 0 else 0.0
        else:
            sharpe_ratio = None

        # Store result
        stmt = pg_insert(BacktestResult).values(
            asset_id=asset.id,
            period=period,
            run_date=today,
            win_rate=round(win_rate, 4),
            total_return=round(total_return, 6),
            buy_hold_return=round(buy_hold_return, 6),
            max_drawdown=round(max_drawdown, 6),
            sharpe_ratio=round(sharpe_ratio, 4) if sharpe_ratio is not None else None,
            daily_results={"days_tested": len(daily_verdicts), "verdicts": daily_verdicts},
        ).on_conflict_do_update(
            constraint="uq_backtest_asset_period_date",
            set_={
                "win_rate": round(win_rate, 4),
                "total_return": round(total_return, 6),
                "buy_hold_return": round(buy_hold_return, 6),
                "max_drawdown": round(max_drawdown, 6),
                "sharpe_ratio": round(sharpe_ratio, 4) if sharpe_ratio is not None else None,
                "daily_results": {"days_tested": len(daily_verdicts), "verdicts": daily_verdicts},
            },
        )
        await session.execute(stmt)
        await session.commit()

        return {
            "symbol": symbol.upper(),
            "period": period,
            "win_rate": round(win_rate, 4),
            "total_return": round(total_return, 6),
            "buy_hold_return": round(buy_hold_return, 6),
            "max_drawdown": round(max_drawdown, 6),
            "sharpe_ratio": round(sharpe_ratio, 4) if sharpe_ratio is not None else None,
            "days_tested": len(daily_verdicts),
            "status": "complete",
        }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run historical backtest")
    parser.add_argument("--asset", required=True, help="Asset symbol")
    parser.add_argument("--period", required=True, choices=["7d", "30d", "90d"])
    args = parser.parse_args()

    try:
        result = asyncio.run(run_backtest(args.asset, args.period))
        print(json.dumps(result))
    except Exception as exc:
        print(json.dumps({"status": "error", "message": str(exc)}))
        sys.exit(1)
