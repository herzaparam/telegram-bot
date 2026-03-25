"""MacroEngine: Fed funds rate, CPI, DXY, and USD/IDR analysis."""

from __future__ import annotations

import pandas as pd
import structlog

from src.config import settings
from src.engines.base import BaseEngine, Signal

logger = structlog.get_logger(__name__)

# FRED series identifiers for reference
FRED_SERIES = {
    "fed_funds_rate": "FEDFUNDS",
    "cpi": "CPIAUCSL",
    "dxy": "DTWEXBGS",
    "usd_idr": "DEXINUS",
}


# ---------------------------------------------------------------------------
# Zone-mapping functions (module-level, private)
# ---------------------------------------------------------------------------


def _fed_rate_to_score(rate: float | None) -> float:
    """Map Fed funds rate to sub-score.

    Higher rates = bearish for risk assets.
    rate < 1.0 -> +0.6 (very accommodative)
    rate < 3.0 -> +0.2
    rate < 5.0 -> -0.2
    rate < 7.0 -> -0.5
    rate >= 7.0 -> -0.8 (very restrictive)
    """
    if rate is None:
        return 0.0
    if rate < 1.0:
        return 0.6
    if rate < 3.0:
        return 0.2
    if rate < 5.0:
        return -0.2
    if rate < 7.0:
        return -0.5
    return -0.8


def _cpi_to_score(cpi: float | None) -> float:
    """Map CPI (YoY % change proxy or raw level) to sub-score.

    Higher CPI = bearish (tightening policy ahead).
    cpi < 2.0 -> +0.5 (stable prices)
    cpi < 3.0 -> +0.2
    cpi < 5.0 -> -0.2
    cpi < 7.0 -> -0.5
    cpi >= 7.0 -> -0.8 (runaway inflation)
    """
    if cpi is None:
        return 0.0
    if cpi < 2.0:
        return 0.5
    if cpi < 3.0:
        return 0.2
    if cpi < 5.0:
        return -0.2
    if cpi < 7.0:
        return -0.5
    return -0.8


def _dxy_to_score(dxy: float | None) -> float:
    """Map DXY (US Dollar Index) to sub-score.

    Stronger dollar = bearish for IDX and crypto.
    dxy < 90 -> +0.5 (weak dollar = bullish)
    dxy < 100 -> +0.2
    dxy < 105 -> -0.2
    dxy < 110 -> -0.5
    dxy >= 110 -> -0.8 (very strong dollar)
    """
    if dxy is None:
        return 0.0
    if dxy < 90:
        return 0.5
    if dxy < 100:
        return 0.2
    if dxy < 105:
        return -0.2
    if dxy < 110:
        return -0.5
    return -0.8


def _usd_idr_to_score(rate: float | None) -> float:
    """Map USD/IDR exchange rate to sub-score.

    Weaker rupiah (higher rate) = bearish for IDX stocks.
    rate < 14000 -> +0.5 (strong rupiah)
    rate < 15000 -> +0.2
    rate < 16000 -> -0.2
    rate < 17000 -> -0.5
    rate >= 17000 -> -0.8 (very weak rupiah)
    """
    if rate is None:
        return 0.0
    if rate < 14000:
        return 0.5
    if rate < 15000:
        return 0.2
    if rate < 16000:
        return -0.2
    if rate < 17000:
        return -0.5
    return -0.8


def _is_stock_symbol(symbol: str) -> bool:
    """Heuristic: IDX stock symbols are typically 4 uppercase chars, no slash."""
    if "/" in symbol:
        return False
    if len(symbol) >= 3 and symbol.isalpha() and symbol.isupper():
        return True
    return False


# ---------------------------------------------------------------------------
# MacroEngine
# ---------------------------------------------------------------------------


class MacroEngine(BaseEngine):
    """Macro analysis engine using FRED indicators.

    One global macro score per asset (D-07). Reasoning emphasizes
    IDX-relevant factors for stocks and global factors for crypto.
    """

    def __init__(
        self,
        macro_data: dict[str, float] | None = None,
    ) -> None:
        """Initialize with optional macro data.

        Args:
            macro_data: Dict with keys: fed_funds_rate, cpi, dxy, usd_idr.
                Pass None or {} when macro data is unavailable.
        """
        self._macro_data = macro_data

    @property
    def category(self) -> str:
        """Return engine category."""
        return "macro"

    @property
    def supports_stocks(self) -> bool:
        return True

    @property
    def supports_crypto(self) -> bool:
        return True

    def analyze(
        self, asset_id: int, asset_symbol: str, df: pd.DataFrame
    ) -> Signal:
        """Run macro analysis.

        Never raises -- returns score=0/confidence=0 on failure.
        """
        try:
            return self._analyze_impl(asset_id, asset_symbol, df)
        except Exception as exc:
            logger.warning(
                "macro_engine_error",
                asset_id=asset_id,
                asset_symbol=asset_symbol,
                error=str(exc),
            )
            return Signal(
                category="macro",
                score=0.0,
                confidence=0.0,
                reasoning=f"Macro analysis failed: {exc}",
                indicators={},
                data_quality={"error": str(exc)},
            )

    def _analyze_impl(
        self, asset_id: int, asset_symbol: str, df: pd.DataFrame
    ) -> Signal:
        """Internal analysis implementation."""
        if not self._macro_data:
            return Signal(
                category="macro",
                score=0.0,
                confidence=0.0,
                reasoning="No macro data available",
                indicators={},
                data_quality={"available_indicators": 0, "total_indicators": 4},
            )

        data = self._macro_data
        fed_rate = data.get("fed_funds_rate")
        cpi = data.get("cpi")
        dxy = data.get("dxy")
        usd_idr = data.get("usd_idr")

        # Zone-map each indicator
        sub_scores: dict[str, float] = {
            "fed_rate": _fed_rate_to_score(float(fed_rate) if fed_rate is not None else None),
            "cpi": _cpi_to_score(float(cpi) if cpi is not None else None),
            "dxy": _dxy_to_score(float(dxy) if dxy is not None else None),
            "usd_idr": _usd_idr_to_score(float(usd_idr) if usd_idr is not None else None),
        }

        # Weighted average
        weights = {
            "fed_rate": settings.weight_macro_fed_rate,
            "cpi": settings.weight_macro_cpi,
            "dxy": settings.weight_macro_dxy,
            "usd_idr": settings.weight_macro_usd_idr,
        }

        composite = sum(sub_scores[k] * weights[k] for k in weights)
        composite = max(-1.0, min(1.0, composite))

        # Confidence: count available indicators / 4
        available = sum(
            1 for v in [fed_rate, cpi, dxy, usd_idr] if v is not None
        )
        confidence = available / 4.0
        confidence = max(0.0, min(1.0, confidence))

        # --- Reasoning (differentiated by asset type) ---
        is_stock = _is_stock_symbol(asset_symbol)
        reasoning_parts = []

        if fed_rate is not None:
            rate_label = "accommodative" if float(fed_rate) < 3.0 else "restrictive"
            reasoning_parts.append(f"Fed rate={float(fed_rate):.1f}% ({rate_label})")

        if cpi is not None:
            cpi_label = "low" if float(cpi) < 3.0 else "elevated" if float(cpi) < 6.0 else "high"
            reasoning_parts.append(f"CPI={float(cpi):.1f}% ({cpi_label})")

        if is_stock:
            # IDX-relevant: emphasize rupiah and local factors
            if usd_idr is not None:
                idr_label = (
                    "strong rupiah" if float(usd_idr) < 15000
                    else "weak rupiah" if float(usd_idr) > 16000
                    else "stable rupiah"
                )
                reasoning_parts.append(f"USD/IDR={float(usd_idr):,.0f} ({idr_label})")
            if dxy is not None:
                reasoning_parts.append(f"DXY={float(dxy):.1f} (IDX pressure)")
            reasoning_parts.append("IDX macro context.")
        else:
            # Crypto: emphasize global factors (Fed, DXY)
            if dxy is not None:
                dxy_label = "weak dollar" if float(dxy) < 100 else "strong dollar"
                reasoning_parts.append(f"DXY={float(dxy):.1f} ({dxy_label})")
            if usd_idr is not None:
                reasoning_parts.append(f"USD/IDR={float(usd_idr):,.0f}")
            reasoning_parts.append("Global macro context.")

        reasoning = ", ".join(reasoning_parts[:-1])
        if reasoning:
            reasoning += ". " + reasoning_parts[-1]
        else:
            reasoning = reasoning_parts[-1] if reasoning_parts else "Macro data processed."

        indicators: dict[str, object] = {
            "fed_funds_rate": fed_rate,
            "cpi": cpi,
            "dxy": dxy,
            "usd_idr": usd_idr,
            "sub_score_fed_rate": round(sub_scores["fed_rate"], 4),
            "sub_score_cpi": round(sub_scores["cpi"], 4),
            "sub_score_dxy": round(sub_scores["dxy"], 4),
            "sub_score_usd_idr": round(sub_scores["usd_idr"], 4),
        }

        data_quality: dict[str, object] = {
            "available_indicators": available,
            "total_indicators": 4,
        }

        return Signal(
            category="macro",
            score=round(composite, 6),
            confidence=round(confidence, 4),
            reasoning=reasoning,
            indicators=indicators,
            data_quality=data_quality,
        )
