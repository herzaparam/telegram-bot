"""Discovery scanner: screens IHSG stocks and crypto for unusual activity.

Detects four trigger types (volume spike, price breakout, momentum surge,
statistical anomaly), computes composite scores, and stores top candidates
as DiscoveryCandidate rows.
"""

from __future__ import annotations

import asyncio
from datetime import date
from functools import partial
from typing import Any

import httpx
import numpy as np
import pandas as pd
import pandas_ta_classic as _ta  # type: ignore[import-untyped]  # noqa: F401 -- registers .ta accessor
import structlog
import yfinance as yf
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import DiscoveryCandidate
from src.engines.valuation import IDX_SECTOR_MAP

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

BATCH_SIZE = 80
BATCH_DELAY = 3.0  # seconds between yfinance batches
SCAN_TIMEOUT = 300  # 5 min hard timeout
TOP_N = 20  # store top 20 candidates (report shows top 5)

TRIGGER_WEIGHTS: dict[str, float] = {
    "volume_spike": 0.30,
    "price_breakout": 0.30,
    "momentum_surge": 0.25,
    "statistical_anomaly": 0.15,
}

# Minimum data requirements
_MIN_VOLUME_DAYS = 20
_MIN_BREAKOUT_DAYS = 30  # Need some history; 252 ideal for 52-week
_MIN_MOMENTUM_DAYS = 30
_MIN_ANOMALY_DAYS = 22  # 20-day window + 2 for returns

# CoinGecko API
_COINGECKO_MARKETS_URL = "https://api.coingecko.com/api/v3/coins/markets"


# ---------------------------------------------------------------------------
# Composite scoring
# ---------------------------------------------------------------------------


def compute_composite_score(triggers: dict[str, float]) -> float:
    """Compute weighted composite score from trigger dict.

    Applies multi-trigger bonuses:
    - 2 active triggers: 1.15x
    - 3+ active triggers: 1.30x
    Result capped at 1.0.
    """
    if not triggers:
        return 0.0

    # Weighted sum using TRIGGER_WEIGHTS
    weighted_sum = sum(
        score * TRIGGER_WEIGHTS.get(name, 0.0) for name, score in triggers.items()
    )

    # Count active triggers (non-zero)
    active_count = sum(1 for v in triggers.values() if v > 0)

    # Multi-trigger bonus
    if active_count >= 3:
        weighted_sum *= 1.30
    elif active_count == 2:
        weighted_sum *= 1.15

    return min(1.0, weighted_sum)


# ---------------------------------------------------------------------------
# Individual trigger detectors
# ---------------------------------------------------------------------------


def _detect_volume_spike(volumes: pd.Series) -> float:
    """Detect volume spike: today's volume vs 20-day average.

    Returns normalized score 0-1. Threshold: >2x avg triggers.
    Score scales gradually: min(1.0, ratio / 5.0).
    Returns 0.0 if insufficient data (<20 days).
    """
    if len(volumes) < _MIN_VOLUME_DAYS + 1:
        return 0.0

    avg_20 = volumes.iloc[-21:-1].mean()
    if avg_20 <= 0:
        return 0.0

    ratio = volumes.iloc[-1] / avg_20
    if ratio <= 2.0:
        return 0.0

    return min(1.0, ratio / 5.0)


def _detect_breakout(closes: pd.Series, highs: pd.Series) -> float:
    """Detect price breakout: 52-week high or Bollinger upper band break.

    Returns max of individual breakout scores (0-1).
    """
    if len(closes) < _MIN_BREAKOUT_DAYS:
        return 0.0

    scores: list[float] = []

    # (a) 52-week high check
    lookback = min(252, len(closes) - 1)
    hist_max = closes.iloc[-lookback - 1 : -1].max()
    if hist_max > 0 and closes.iloc[-1] >= hist_max:
        # How far above previous max
        overshoot = (closes.iloc[-1] - hist_max) / hist_max
        scores.append(min(1.0, 0.6 + overshoot * 10))

    # (b) Bollinger upper band break
    try:
        df_bb = pd.DataFrame({"close": closes})
        bbands = df_bb.ta.bbands(close="close", length=20)
        if bbands is not None and not bbands.empty:
            upper_col = [c for c in bbands.columns if "BBU" in c]
            if upper_col:
                upper_val = bbands[upper_col[0]].iloc[-1]
                if pd.notna(upper_val) and upper_val > 0 and closes.iloc[-1] > upper_val:
                    bb_score = min(1.0, (closes.iloc[-1] - upper_val) / upper_val * 20 + 0.5)
                    scores.append(bb_score)
    except Exception:
        pass  # Bollinger calc failed, rely on 52-week high

    return max(scores) if scores else 0.0


def _detect_momentum(closes: pd.Series) -> float:
    """Detect momentum surge: RSI crossover above 50, MACD signal crossover.

    Returns max of momentum scores (0-1).
    """
    if len(closes) < _MIN_MOMENTUM_DAYS:
        return 0.0

    scores: list[float] = []

    # RSI crossover above 50
    try:
        rsi = pd.DataFrame({"close": closes}).ta.rsi(close="close", length=14)
        if rsi is not None and len(rsi) >= 2:
            rsi_now = rsi.iloc[-1]
            rsi_prev = rsi.iloc[-2]
            if pd.notna(rsi_now) and pd.notna(rsi_prev):
                if rsi_prev < 50 and rsi_now >= 50:
                    # Score based on how far above 50
                    scores.append(min(1.0, (rsi_now - 50) / 30 + 0.5))
    except Exception:
        pass

    # MACD signal crossover
    try:
        macd_df = pd.DataFrame({"close": closes}).ta.macd(close="close")
        if macd_df is not None and not macd_df.empty:
            macd_col = [c for c in macd_df.columns if "MACD_" in c and "MACDs" not in c and "MACDh" not in c]
            signal_col = [c for c in macd_df.columns if "MACDs" in c]
            if macd_col and signal_col:
                macd_now = macd_df[macd_col[0]].iloc[-1]
                macd_prev = macd_df[macd_col[0]].iloc[-2]
                signal_now = macd_df[signal_col[0]].iloc[-1]
                signal_prev = macd_df[signal_col[0]].iloc[-2]
                if all(pd.notna(v) for v in [macd_now, macd_prev, signal_now, signal_prev]):
                    if macd_prev <= signal_prev and macd_now > signal_now:
                        scores.append(0.7)
    except Exception:
        pass

    return max(scores) if scores else 0.0


def _detect_anomaly(closes: pd.Series, volumes: pd.Series) -> float:
    """Detect statistical anomaly via Z-score of daily returns.

    Flags if today's return Z-score > 2.0 std devs.
    Returns normalized score 0-1.
    """
    if len(closes) < _MIN_ANOMALY_DAYS:
        return 0.0

    returns = closes.pct_change().dropna()
    if len(returns) < 20:
        return 0.0

    rolling_mean = returns.iloc[-21:-1].mean()
    rolling_std = returns.iloc[-21:-1].std()

    if rolling_std is None or rolling_std <= 0 or pd.isna(rolling_std):
        return 0.0

    today_return = returns.iloc[-1]
    z_score = abs((today_return - rolling_mean) / rolling_std)

    if z_score <= 2.0:
        return 0.0

    return min(1.0, (z_score - 2.0) / 3.0 + 0.3)


def _detect_triggers(
    closes: pd.Series, highs: pd.Series, volumes: pd.Series
) -> dict[str, float]:
    """Run all four trigger detectors and return dict with non-zero triggers."""
    triggers: dict[str, float] = {}

    vol_score = _detect_volume_spike(volumes)
    if vol_score > 0:
        triggers["volume_spike"] = vol_score

    breakout_score = _detect_breakout(closes, highs)
    if breakout_score > 0:
        triggers["price_breakout"] = breakout_score

    momentum_score = _detect_momentum(closes)
    if momentum_score > 0:
        triggers["momentum_surge"] = momentum_score

    anomaly_score = _detect_anomaly(closes, volumes)
    if anomaly_score > 0:
        triggers["statistical_anomaly"] = anomaly_score

    return triggers


# ---------------------------------------------------------------------------
# Data fetching
# ---------------------------------------------------------------------------


def _get_ihsg_tickers() -> list[str]:
    """Return list of IHSG tickers with .JK suffix.

    Tries IDX API first, falls back to hardcoded list from IDX_SECTOR_MAP.
    """
    try:
        resp = httpx.get(
            "https://www.idx.co.id/primary/StockData/GetSecurityStock",
            params={"start": 0, "length": 9999, "code": "", "sector": "", "board": ""},
            timeout=15,
            headers={"User-Agent": "Mozilla/5.0"},
        )
        if resp.status_code == 200:
            data = resp.json()
            records = data.get("data", data) if isinstance(data, dict) else data
            if isinstance(records, list) and len(records) > 50:
                tickers = []
                for rec in records:
                    code = rec.get("Code") or rec.get("code") or rec.get("KodeEmiten", "")
                    if code:
                        tickers.append(f"{code}.JK")
                if len(tickers) > 50:
                    logger.info("idx_tickers_fetched", count=len(tickers))
                    return tickers
    except Exception as exc:
        logger.warning("idx_ticker_fetch_failed", error=str(exc))

    # Fallback: IDX_SECTOR_MAP keys + additional large-cap
    tickers = [f"{sym}.JK" for sym in IDX_SECTOR_MAP.keys()]
    logger.info("idx_tickers_fallback", count=len(tickers))
    return tickers


async def _fetch_idx_screening_data(tickers: list[str]) -> pd.DataFrame:
    """Download 1-month OHLCV for IDX tickers using yfinance in batches.

    Uses run_in_executor since yfinance is synchronous.
    """
    loop = asyncio.get_running_loop()
    all_frames: list[pd.DataFrame] = []

    for i in range(0, len(tickers), BATCH_SIZE):
        batch = tickers[i : i + BATCH_SIZE]
        try:
            df = await loop.run_in_executor(
                None,
                partial(
                    yf.download,
                    tickers=batch,
                    period="1mo",
                    group_by="ticker",
                    progress=False,
                    threads=False,
                ),
            )
            if df is not None and not df.empty:
                all_frames.append(df)
        except Exception as exc:
            logger.warning("idx_batch_fetch_error", batch_start=i, error=str(exc))

        # Rate limit between batches
        if i + BATCH_SIZE < len(tickers):
            await asyncio.sleep(BATCH_DELAY)

    if not all_frames:
        return pd.DataFrame()

    return pd.concat(all_frames, axis=1) if len(all_frames) > 1 else all_frames[0]


async def _fetch_crypto_screening_data() -> list[dict[str, Any]]:
    """Fetch top 100 crypto by market cap from CoinGecko."""
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(
            _COINGECKO_MARKETS_URL,
            params={
                "vs_currency": "usd",
                "order": "market_cap_desc",
                "per_page": 100,
                "page": 1,
                "sparkline": "false",
                "price_change_percentage": "24h,7d",
            },
        )
        resp.raise_for_status()
        return resp.json()


# ---------------------------------------------------------------------------
# Crypto scoring
# ---------------------------------------------------------------------------


def _score_crypto_candidate(coin: dict[str, Any]) -> dict[str, float]:
    """Score a crypto coin for discovery triggers.

    Returns dict with non-zero trigger scores.
    """
    triggers: dict[str, float] = {}

    # Volume spike: market cap change percentage magnitude
    mcap_change = abs(coin.get("market_cap_change_percentage_24h", 0) or 0)
    if mcap_change > 5:
        triggers["volume_spike"] = min(1.0, mcap_change / 20)

    # Momentum surge: price change > 10% in 24h
    price_24h = abs(coin.get("price_change_percentage_24h", 0) or 0)
    if price_24h > 10:
        triggers["momentum_surge"] = min(1.0, price_24h / 30)

    # Statistical anomaly: 7d vs 24h divergence
    price_7d = coin.get("price_change_percentage_7d_in_currency", 0) or 0
    price_24h_raw = coin.get("price_change_percentage_24h", 0) or 0
    divergence = abs(price_24h_raw - price_7d)
    if divergence > 15:
        triggers["statistical_anomaly"] = min(1.0, divergence / 40)

    return triggers


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


async def run_discovery_scan(
    session: AsyncSession, run_date: date
) -> list[dict[str, Any]]:
    """Main discovery scanner entry point.

    Orchestrates IDX + crypto scanning with SCAN_TIMEOUT hard timeout.
    Returns list of candidate dicts sorted by composite_score descending.
    """
    try:
        return await asyncio.wait_for(
            _run_discovery_scan_inner(session, run_date),
            timeout=SCAN_TIMEOUT,
        )
    except asyncio.TimeoutError:
        logger.error("discovery_scan_timeout", timeout=SCAN_TIMEOUT)
        return []
    except Exception as exc:
        logger.error("discovery_scan_error", error=str(exc))
        return []


async def _run_discovery_scan_inner(
    session: AsyncSession, run_date: date
) -> list[dict[str, Any]]:
    """Inner scan logic without timeout wrapper."""
    candidates: list[dict[str, Any]] = []

    # --- IDX scanning ---
    try:
        tickers = _get_ihsg_tickers()
        idx_data = await _fetch_idx_screening_data(tickers)
        if idx_data is not None and not idx_data.empty:
            candidates.extend(_process_idx_data(idx_data, tickers))
        logger.info("idx_scan_complete", candidates=len(candidates))
    except Exception as exc:
        logger.warning("idx_scan_failed", error=str(exc))

    # --- Crypto scanning ---
    try:
        crypto_data = await _fetch_crypto_screening_data()
        crypto_candidates = _process_crypto_data(crypto_data)
        candidates.extend(crypto_candidates)
        logger.info("crypto_scan_complete", candidates=len(crypto_candidates))
    except Exception as exc:
        logger.warning("crypto_scan_failed", error=str(exc))

    if not candidates:
        return []

    # Sort by composite_score descending
    candidates.sort(key=lambda c: c["composite_score"], reverse=True)

    # Take top N
    top = candidates[:TOP_N]

    # Persist to DB
    try:
        # Delete old rows for same scan_date
        await session.execute(
            delete(DiscoveryCandidate).where(
                DiscoveryCandidate.scan_date == run_date
            )
        )

        for c in top:
            row = DiscoveryCandidate(
                scan_date=run_date,
                symbol=c["symbol"],
                name=c.get("name"),
                asset_type=c["asset_type"],
                composite_score=c["composite_score"],
                triggers=c["triggers"],
                current_price=c.get("current_price"),
                price_change_pct=c.get("price_change_pct"),
                volume_ratio=c.get("volume_ratio"),
            )
            session.add(row)

        await session.commit()
        logger.info("discovery_candidates_persisted", count=len(top))
    except Exception as exc:
        logger.error("discovery_persist_error", error=str(exc))

    return top


# ---------------------------------------------------------------------------
# Data processing helpers
# ---------------------------------------------------------------------------


def _process_idx_data(
    data: pd.DataFrame, tickers: list[str]
) -> list[dict[str, Any]]:
    """Process yfinance batch data and detect triggers for each ticker."""
    results: list[dict[str, Any]] = []

    for ticker in tickers:
        try:
            # Multi-ticker yfinance returns multi-level columns
            if isinstance(data.columns, pd.MultiIndex):
                if ticker not in data.columns.get_level_values(0):
                    continue
                ticker_df = data[ticker].dropna()
            else:
                # Single ticker result
                ticker_df = data.dropna()

            if ticker_df.empty or len(ticker_df) < _MIN_VOLUME_DAYS:
                continue

            closes = ticker_df["Close"] if "Close" in ticker_df.columns else ticker_df.get("close", pd.Series())
            highs = ticker_df["High"] if "High" in ticker_df.columns else ticker_df.get("high", pd.Series())
            volumes = ticker_df["Volume"] if "Volume" in ticker_df.columns else ticker_df.get("volume", pd.Series())

            if closes.empty or volumes.empty:
                continue

            triggers = _detect_triggers(closes, highs, volumes)
            if not triggers:
                continue

            score = compute_composite_score(triggers)
            if score <= 0:
                continue

            symbol = ticker.replace(".JK", "")
            vol_avg = volumes.iloc[-20:].mean()
            vol_ratio = float(volumes.iloc[-1] / vol_avg) if vol_avg > 0 else None

            results.append(
                {
                    "symbol": symbol,
                    "name": None,
                    "asset_type": "stock",
                    "composite_score": round(score, 4),
                    "triggers": {k: round(v, 4) for k, v in triggers.items()},
                    "current_price": float(closes.iloc[-1]) if len(closes) > 0 else None,
                    "price_change_pct": float(
                        (closes.iloc[-1] - closes.iloc[-2]) / closes.iloc[-2] * 100
                    )
                    if len(closes) >= 2 and closes.iloc[-2] != 0
                    else None,
                    "volume_ratio": round(vol_ratio, 2) if vol_ratio else None,
                }
            )
        except Exception as exc:
            logger.debug("idx_ticker_process_error", ticker=ticker, error=str(exc))

    return results


def _process_crypto_data(coins: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Score crypto coins and return candidate dicts."""
    results: list[dict[str, Any]] = []

    for coin in coins:
        try:
            triggers = _score_crypto_candidate(coin)
            if not triggers:
                continue

            score = compute_composite_score(triggers)
            if score <= 0:
                continue

            results.append(
                {
                    "symbol": (coin.get("symbol") or "").upper(),
                    "name": coin.get("name"),
                    "asset_type": "crypto",
                    "composite_score": round(score, 4),
                    "triggers": {k: round(v, 4) for k, v in triggers.items()},
                    "current_price": coin.get("current_price"),
                    "price_change_pct": coin.get("price_change_percentage_24h"),
                    "volume_ratio": None,
                }
            )
        except Exception as exc:
            logger.debug("crypto_process_error", coin=coin.get("id"), error=str(exc))

    return results
