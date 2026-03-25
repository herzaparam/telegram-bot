"""FundamentalEngine: P/E, P/B, ROE, revenue growth, dividend yield, debt/equity analysis."""

from __future__ import annotations

import pandas as pd
import structlog

from src.config import settings
from src.engines.base import BaseEngine, Signal

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Zone-mapping functions (module-level, private)
# ---------------------------------------------------------------------------


def _pe_to_score(pe: float | None) -> float:
    """Map P/E ratio to sub-score.

    Negative P/E (unprofitable) -> -0.8
    P/E < 8 -> +0.8 (very cheap)
    P/E < 12 -> +0.5
    P/E < 18 -> +0.2 (fair value)
    P/E < 25 -> -0.2
    P/E < 40 -> -0.5
    P/E >= 40 -> -0.8 (very expensive)
    """
    if pe is None:
        return 0.0
    if pe < 0:
        return -0.8
    if pe < 8:
        return 0.8
    if pe < 12:
        return 0.5
    if pe < 18:
        return 0.2
    if pe < 25:
        return -0.2
    if pe < 40:
        return -0.5
    return -0.8


def _pb_to_score(pb: float | None) -> float:
    """Map P/B ratio to sub-score.

    P/B < 0.5 -> +0.8 (deeply undervalued)
    P/B < 1.0 -> +0.5
    P/B < 2.0 -> +0.2
    P/B < 3.5 -> -0.2
    P/B < 6.0 -> -0.5
    P/B >= 6.0 -> -0.8
    """
    if pb is None:
        return 0.0
    if pb < 0.5:
        return 0.8
    if pb < 1.0:
        return 0.5
    if pb < 2.0:
        return 0.2
    if pb < 3.5:
        return -0.2
    if pb < 6.0:
        return -0.5
    return -0.8


def _roe_to_score(roe: float | None) -> float:
    """Map ROE to sub-score.

    ROE < 0 -> -0.7 (losing money)
    ROE < 0.05 -> -0.3
    ROE < 0.10 -> 0.0
    ROE < 0.15 -> +0.3
    ROE < 0.20 -> +0.6
    ROE >= 0.20 -> +0.8 (excellent)
    """
    if roe is None:
        return 0.0
    if roe < 0:
        return -0.7
    if roe < 0.05:
        return -0.3
    if roe < 0.10:
        return 0.0
    if roe < 0.15:
        return 0.3
    if roe < 0.20:
        return 0.6
    return 0.8


def _revenue_growth_to_score(rg: float | None) -> float:
    """Map revenue growth to sub-score.

    rg < -0.1 -> -0.7 (shrinking revenue)
    rg < 0 -> -0.3
    rg < 0.05 -> 0.0
    rg < 0.15 -> +0.3
    rg < 0.30 -> +0.6
    rg >= 0.30 -> +0.8
    """
    if rg is None:
        return 0.0
    if rg < -0.1:
        return -0.7
    if rg < 0:
        return -0.3
    if rg < 0.05:
        return 0.0
    if rg < 0.15:
        return 0.3
    if rg < 0.30:
        return 0.6
    return 0.8


def _dividend_yield_to_score(dy: float | None) -> float:
    """Map dividend yield to sub-score.

    dy < 0.01 -> -0.2 (no dividend)
    dy < 0.02 -> 0.0
    dy < 0.04 -> +0.3
    dy < 0.06 -> +0.6
    dy >= 0.06 -> +0.8 (high yield)
    """
    if dy is None:
        return 0.0
    if dy < 0.01:
        return -0.2
    if dy < 0.02:
        return 0.0
    if dy < 0.04:
        return 0.3
    if dy < 0.06:
        return 0.6
    return 0.8


def _debt_to_equity_to_score(de: float | None) -> float:
    """Map debt/equity ratio to sub-score.

    de < 0.3 -> +0.8 (very low leverage)
    de < 0.5 -> +0.5
    de < 1.0 -> +0.2
    de < 2.0 -> -0.2
    de < 3.0 -> -0.5
    de >= 3.0 -> -0.8 (heavily leveraged)
    """
    if de is None:
        return 0.0
    if de < 0.3:
        return 0.8
    if de < 0.5:
        return 0.5
    if de < 1.0:
        return 0.2
    if de < 2.0:
        return -0.2
    if de < 3.0:
        return -0.5
    return -0.8


# ---------------------------------------------------------------------------
# FundamentalEngine
# ---------------------------------------------------------------------------


class FundamentalEngine(BaseEngine):
    """Fundamental analysis engine using P/E, P/B, ROE, revenue growth, dividend yield, D/E.

    Data injected via constructor (store-backed pattern -- not read from price DataFrame).
    FundamentalEngine returns score=0/confidence=0 with crypto-not-applicable reasoning
    when fundamentals is None (per D-03: keep visible to LLM).
    """

    def __init__(
        self,
        fundamentals: dict[str, float | None] | None = None,
    ) -> None:
        """Initialize with optional fundamentals dict.

        Args:
            fundamentals: Dict with keys: trailing_pe, price_to_book, return_on_equity,
                revenue_growth, dividend_yield, debt_to_equity. Pass None for crypto assets.
        """
        self._fundamentals = fundamentals

    @property
    def category(self) -> str:
        """Return engine category."""
        return "fundamental"

    @property
    def supports_stocks(self) -> bool:
        """Fundamental analysis applies to stocks."""
        return True

    @property
    def supports_crypto(self) -> bool:
        """Keep visible to LLM for crypto (returns not-applicable signal per D-03)."""
        return True

    def analyze(
        self, asset_id: int, asset_symbol: str, df: pd.DataFrame
    ) -> Signal:
        """Run fundamental analysis.

        Never raises -- returns score=0/confidence=0 on failure.
        """
        try:
            return self._analyze_impl(asset_id, asset_symbol, df)
        except Exception as exc:
            logger.warning(
                "fundamental_engine_error",
                asset_id=asset_id,
                asset_symbol=asset_symbol,
                error=str(exc),
            )
            return Signal(
                category="fundamental",
                score=0.0,
                confidence=0.0,
                reasoning=f"Fundamental analysis failed: {exc}",
                indicators={},
                data_quality={"error": str(exc)},
            )

    def _analyze_impl(
        self, asset_id: int, asset_symbol: str, df: pd.DataFrame
    ) -> Signal:
        """Internal analysis implementation."""
        # Crypto: fundamentals not applicable
        if self._fundamentals is None:
            return Signal(
                category="fundamental",
                score=0.0,
                confidence=0.0,
                reasoning="Fundamentals not applicable for crypto",
                indicators={},
                data_quality={"reason": "crypto_asset"},
            )

        fund = self._fundamentals
        pe = fund.get("trailing_pe")
        pb = fund.get("price_to_book")
        roe = fund.get("return_on_equity")
        rg = fund.get("revenue_growth")
        dy = fund.get("dividend_yield")
        de = fund.get("debt_to_equity")

        # Zone-map each ratio
        sub_scores: dict[str, float] = {
            "pe": _pe_to_score(float(pe) if pe is not None else None),
            "pb": _pb_to_score(float(pb) if pb is not None else None),
            "roe": _roe_to_score(float(roe) if roe is not None else None),
            "revenue_growth": _revenue_growth_to_score(float(rg) if rg is not None else None),
            "dividend_yield": _dividend_yield_to_score(float(dy) if dy is not None else None),
            "debt_to_equity": _debt_to_equity_to_score(float(de) if de is not None else None),
        }

        # Weighted average using settings
        weights = {
            "pe": settings.weight_fundamental_pe,
            "pb": settings.weight_fundamental_pb,
            "roe": settings.weight_fundamental_roe,
            "revenue_growth": settings.weight_fundamental_revenue_growth,
            "dividend_yield": settings.weight_fundamental_dividend_yield,
            "debt_to_equity": settings.weight_fundamental_debt_to_equity,
        }

        composite = sum(sub_scores[k] * weights[k] for k in weights)
        composite = max(-1.0, min(1.0, composite))

        # --- Confidence ---
        # Count non-None ratios (data availability)
        available_ratios = [
            v for v in [pe, pb, roe, rg, dy, de] if v is not None
        ]
        data_ratio = len(available_ratios) / 6.0

        # Agreement ratio: count sub-scores agreeing with composite direction
        if composite == 0.0:
            agreement_ratio = 0.5
        else:
            direction = 1 if composite > 0 else -1
            agreeing = sum(
                1 for v in sub_scores.values() if (v > 0 and direction > 0) or (v < 0 and direction < 0)
            )
            agreement_ratio = agreeing / len(sub_scores) if sub_scores else 0.5

        confidence = data_ratio * agreement_ratio
        confidence = max(0.0, min(1.0, confidence))

        # --- Reasoning ---
        reasoning_parts = []
        if pe is not None:
            pe_label = "cheap" if float(pe) < 12 else "expensive" if float(pe) > 25 else "fair"
            reasoning_parts.append(f"P/E={float(pe):.1f} ({pe_label})")
        if roe is not None:
            roe_pct = float(roe) * 100
            roe_label = "strong" if float(roe) >= 0.15 else "weak" if float(roe) < 0.05 else "moderate"
            reasoning_parts.append(f"ROE={roe_pct:.1f}% ({roe_label})")
        if pb is not None:
            reasoning_parts.append(f"P/B={float(pb):.2f}")
        if rg is not None:
            rg_pct = float(rg) * 100
            reasoning_parts.append(f"RevGrowth={rg_pct:.1f}%")
        if dy is not None:
            dy_pct = float(dy) * 100
            reasoning_parts.append(f"DivYield={dy_pct:.1f}%")
        if de is not None:
            reasoning_parts.append(f"D/E={float(de):.2f}")

        if composite > 0.1:
            bias = "Bullish"
        elif composite < -0.1:
            bias = "Bearish"
        else:
            bias = "Neutral"

        reasoning_parts.append(f"{bias} fundamental bias.")

        reasoning = ", ".join(reasoning_parts[:-1])
        if reasoning:
            reasoning += ". " + reasoning_parts[-1]
        else:
            reasoning = reasoning_parts[-1] if reasoning_parts else "No fundamental data."

        # --- Indicators dict ---
        indicators: dict[str, object] = {
            "trailing_pe": pe,
            "price_to_book": pb,
            "return_on_equity": roe,
            "revenue_growth": rg,
            "dividend_yield": dy,
            "debt_to_equity": de,
        }
        for k, v in sub_scores.items():
            indicators[f"sub_score_{k}"] = round(v, 4)

        data_quality: dict[str, object] = {
            "available_ratios": len(available_ratios),
            "total_ratios": 6,
        }

        return Signal(
            category="fundamental",
            score=round(composite, 6),
            confidence=round(confidence, 4),
            reasoning=reasoning,
            indicators=indicators,
            data_quality=data_quality,
        )
