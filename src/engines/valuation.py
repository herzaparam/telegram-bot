"""ValuationEngine: DCF fair value, peer comparison, scenario analysis, crypto NVT + TVL proxies."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
import structlog

from src.engines.base import BaseEngine, Signal

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Sector peer map (D-12) -- hardcoded for initial IDX watchlist stocks
# ---------------------------------------------------------------------------

IDX_SECTOR_MAP: dict[str, str] = {
    # Banking
    "BBCA": "banking",
    "BBRI": "banking",
    "BMRI": "banking",
    "BBNI": "banking",
    "BRIS": "banking",
    "BTPS": "banking",
    "MEGA": "banking",
    "NISP": "banking",
    # Telco
    "TLKM": "telco",
    "EXCL": "telco",
    "ISAT": "telco",
    # Consumer
    "UNVR": "consumer",
    "ICBP": "consumer",
    "INDF": "consumer",
    "MYOR": "consumer",
    "KLBF": "consumer",
    "HMSP": "consumer",
    "GGRM": "consumer",
    # Mining
    "ADRO": "mining",
    "PTBA": "mining",
    "ITMG": "mining",
    "ANTM": "mining",
    "INCO": "mining",
    "MDKA": "mining",
    "TINS": "mining",
    # Energy
    "PGAS": "energy",
    "AKRA": "energy",
    "MEDC": "energy",
    # Property
    "BSDE": "property",
    "CTRA": "property",
    "SMRA": "property",
    "PWON": "property",
    # Infrastructure
    "JSMR": "infrastructure",
    "WIKA": "infrastructure",
    "WSKT": "infrastructure",
    "PTPP": "infrastructure",
    # Automotive
    "ASII": "automotive",
    "AUTO": "automotive",
    "IMAS": "automotive",
    # Cement/Construction Materials
    "SMGR": "construction_materials",
    "INTP": "construction_materials",
    "WTON": "construction_materials",
    # Technology
    "GOTO": "technology",
    "BUKA": "technology",
    "EMTK": "technology",
    # Healthcare
    "SIDO": "healthcare",
    "HEAL": "healthcare",
    "MIKA": "healthcare",
    # Retail
    "ACES": "retail",
    "LPPF": "retail",
    "MAPI": "retail",
    "ERAA": "retail",
}

# Crypto symbols that use NVT proxy (major L1 chains)
_NVT_SYMBOLS: set[str] = {"BTC", "ETH"}


# ---------------------------------------------------------------------------
# DCF computation (per D-11, D-14)
# ---------------------------------------------------------------------------


def _compute_dcf(
    fcf: float,
    growth_rate: float,
    wacc: float,
    shares_outstanding: float,
    projection_years: int = 5,
    terminal_growth: float = 0.03,
) -> float:
    """Compute DCF fair value per share using two-stage model.

    Stage 1: Explicit FCF projection for ``projection_years`` years.
    Stage 2: Gordon Growth terminal value.

    Returns 0.0 when inputs are invalid (zero shares, wacc <= terminal_growth).
    """
    if shares_outstanding <= 0:
        return 0.0
    if wacc <= terminal_growth:
        return 0.0

    # Stage 1: project FCFs and discount
    pv_fcfs = 0.0
    projected_fcf = fcf
    for year in range(1, projection_years + 1):
        projected_fcf *= 1 + growth_rate
        pv_fcfs += projected_fcf / (1 + wacc) ** year

    # Stage 2: Gordon Growth terminal value at end of projection period
    terminal_fcf = projected_fcf * (1 + terminal_growth)
    terminal_value = terminal_fcf / (wacc - terminal_growth)
    pv_terminal = terminal_value / (1 + wacc) ** projection_years

    enterprise_value = pv_fcfs + pv_terminal
    return enterprise_value / shares_outstanding


# ---------------------------------------------------------------------------
# WACC computation (per D-11)
# ---------------------------------------------------------------------------


def _compute_wacc(
    risk_free_rate: float,
    beta: float,
    equity_risk_premium: float = 0.065,
    debt_ratio: float = 0.0,
    cost_of_debt: float = 0.0,
    tax_rate: float = 0.22,
) -> float:
    """Compute Weighted Average Cost of Capital.

    CAPM: cost_of_equity = risk_free_rate + beta * equity_risk_premium
    WACC = cost_of_equity * (1 - debt_ratio) + cost_of_debt * (1 - tax_rate) * debt_ratio

    Result clamped to [0.05, 0.25] for sanity.
    """
    cost_of_equity = risk_free_rate + beta * equity_risk_premium
    wacc = cost_of_equity * (1 - debt_ratio) + cost_of_debt * (1 - tax_rate) * debt_ratio
    return max(0.05, min(0.25, wacc))


# ---------------------------------------------------------------------------
# Peer comparison (per D-12)
# ---------------------------------------------------------------------------


def _compute_peer_score(
    stock_metrics: dict[str, float],
    sector_averages: dict[str, float],
) -> tuple[float, str]:
    """Compare stock metrics against sector averages.

    Lower P/E, P/B, EV/EBITDA vs sector = cheaper = positive score.
    Returns (composite_score, rank_label).
    """
    scores: list[float] = []

    for metric in ("pe", "pb", "ev_ebitda"):
        stock_val = stock_metrics.get(metric)
        sector_val = sector_averages.get(metric)
        if stock_val is None or sector_val is None or sector_val == 0:
            continue

        ratio = stock_val / sector_val
        if ratio < 0.85:
            scores.append(0.5)  # cheap
        elif ratio > 1.15:
            scores.append(-0.5)  # expensive
        else:
            scores.append(0.0)  # fair

    if not scores:
        return 0.0, "fair"

    composite = sum(scores) / len(scores)
    composite = max(-1.0, min(1.0, composite))

    if composite > 0.1:
        label = "cheap"
    elif composite < -0.1:
        label = "expensive"
    else:
        label = "fair"

    return composite, label


# ---------------------------------------------------------------------------
# Scenario analysis (per D-14)
# ---------------------------------------------------------------------------


def _compute_scenarios(
    current_price: float,
    fair_value: float,
    cagr: float,
    std_dev: float,
) -> dict[str, object]:
    """Produce bull/base/bear scenario analysis.

    Bull (25%): fair_value * (1 + cagr + std_dev)
    Base (50%): fair_value (unchanged)
    Bear (25%): fair_value * (1 + cagr - std_dev)

    Returns dict with bull/base/bear entries and weighted_return.
    """
    # Bull: upside scenario using growth + volatility premium
    bull_value = fair_value * (1 + cagr + std_dev)
    base_value = fair_value
    # Bear: downside scenario -- subtract growth and volatility
    bear_value = fair_value * (1 - cagr - std_dev)

    def _return_pct(target: float) -> float:
        if current_price <= 0:
            return 0.0
        return (target - current_price) / current_price

    bull_return = _return_pct(bull_value)
    base_return = _return_pct(base_value)
    bear_return = _return_pct(bear_value)

    weighted_return = 0.25 * bull_return + 0.50 * base_return + 0.25 * bear_return

    return {
        "bull": {"value": bull_value, "return_pct": bull_return, "weight": 0.25},
        "base": {"value": base_value, "return_pct": base_return, "weight": 0.50},
        "bear": {"value": bear_value, "return_pct": bear_return, "weight": 0.25},
        "weighted_return": weighted_return,
    }


# ---------------------------------------------------------------------------
# Margin of safety zone mapping
# ---------------------------------------------------------------------------


def _margin_of_safety_to_score(margin: float) -> float:
    """Map margin of safety to valuation score [-1, +1].

    margin > 0.40 -> 0.8 (deeply undervalued)
    margin > 0.20 -> 0.5
    margin > 0.05 -> 0.2
    margin > -0.05 -> 0.0 (fairly valued)
    margin > -0.20 -> -0.3
    margin > -0.40 -> -0.6
    margin <= -0.40 -> -0.8 (deeply overvalued)
    """
    if margin > 0.40:
        return 0.8
    if margin > 0.20:
        return 0.5
    if margin > 0.05:
        return 0.2
    if margin > -0.05:
        return 0.0
    if margin > -0.20:
        return -0.3
    if margin > -0.40:
        return -0.6
    return -0.8


# ---------------------------------------------------------------------------
# Crypto NVT proxy (per D-13 -- for BTC/ETH)
# ---------------------------------------------------------------------------


def _compute_nvt_proxy(
    nvt_data: dict[str, float] | None,
) -> tuple[float, float, str]:
    """Compute NVT-based valuation proxy for major crypto.

    NVT = market_cap / (volume_24h * 365) -- annualized.
    NVT < 20 -> bullish (0.3), 20-50 -> neutral (0.0), > 50 -> bearish (-0.3).

    Returns (score, confidence, reasoning).
    """
    if nvt_data is None:
        return 0.0, 0.0, "No NVT data available"

    market_cap = nvt_data.get("market_cap", 0)
    volume_24h = nvt_data.get("volume_24h", 0)

    if volume_24h <= 0 or market_cap <= 0:
        return 0.0, 0.0, "Invalid NVT data (zero market cap or volume)"

    annualized_volume = volume_24h * 365
    nvt_ratio = market_cap / annualized_volume

    if nvt_ratio < 20:
        score = 0.3
        reasoning = f"NVT={nvt_ratio:.1f} (low, bullish -- high network utility)"
    elif nvt_ratio <= 50:
        score = 0.0
        reasoning = f"NVT={nvt_ratio:.1f} (neutral range)"
    else:
        score = -0.3
        reasoning = f"NVT={nvt_ratio:.1f} (high, bearish -- low network utility)"

    return score, 0.4, reasoning


# ---------------------------------------------------------------------------
# Crypto TVL proxy (per D-13 -- for DeFi tokens)
# ---------------------------------------------------------------------------


def _compute_tvl_proxy(
    tvl_data: dict[str, float] | None,
) -> tuple[float, float, str]:
    """Compute TVL-based valuation proxy for DeFi tokens.

    mcap_tvl_ratio = market_cap / tvl.
    < 1.0 -> bullish (0.4), 1.0-3.0 -> neutral (0.1),
    3.0-10.0 -> slightly bearish (-0.1), > 10.0 -> bearish (-0.3).

    Returns (score, confidence, reasoning).
    """
    if tvl_data is None:
        return 0.0, 0.0, "No TVL data available"

    market_cap = tvl_data.get("market_cap", 0)
    tvl = tvl_data.get("tvl", 0)

    if not tvl or tvl <= 0:
        return 0.0, 0.0, "No TVL data available"

    if market_cap <= 0:
        return 0.0, 0.0, "Invalid market cap for TVL comparison"

    mcap_tvl_ratio = market_cap / tvl

    if mcap_tvl_ratio < 1.0:
        score = 0.4
        reasoning = f"Mcap/TVL={mcap_tvl_ratio:.2f} -- market cap below TVL, potentially undervalued"
    elif mcap_tvl_ratio <= 3.0:
        score = 0.1
        reasoning = f"Mcap/TVL={mcap_tvl_ratio:.2f} -- reasonable mcap/TVL ratio"
    elif mcap_tvl_ratio <= 10.0:
        score = -0.1
        reasoning = f"Mcap/TVL={mcap_tvl_ratio:.2f} -- elevated mcap/TVL"
    else:
        score = -0.3
        reasoning = f"Mcap/TVL={mcap_tvl_ratio:.2f} -- mcap far exceeds TVL"

    return score, 0.5, reasoning


# ---------------------------------------------------------------------------
# QoQ ratio change detection (per D-21 and UI-SPEC)
# ---------------------------------------------------------------------------

QOQ_THRESHOLDS: dict[str, float] = {
    "gross_margin": 0.03,       # 3 percentage points
    "operating_margin": 0.03,
    "net_margin": 0.03,
    "revenue": 0.10,            # 10% change
    "net_profit": 0.10,
    "total_debt": 0.15,         # 15% change
    "operating_cash_flow": 0.15,
    "capex": 0.15,
}

_MARGIN_METRICS: set[str] = {"gross_margin", "operating_margin", "net_margin"}


@dataclass(frozen=True)
class QoQAlert:
    """Significant QoQ ratio change alert."""

    metric_name: str
    current_value: float
    previous_value: float
    change: float  # absolute change for margins (pp), percentage for others
    is_percentage_point: bool  # True for margins, False for absolute metrics


def detect_qoq_changes(financial_data: list[dict]) -> list[QoQAlert]:  # type: ignore[type-arg]
    """Detect significant QoQ ratio changes.

    Args:
        financial_data: List of period dicts ordered by period_date DESC.
            At least 2 periods needed for comparison.

    Returns:
        List of up to 2 most significant QoQAlert objects.
    """
    if len(financial_data) < 2:
        return []

    current = financial_data[0]
    previous = financial_data[1]

    alerts: list[QoQAlert] = []

    for metric, threshold in QOQ_THRESHOLDS.items():
        cur_val = current.get(metric)
        prev_val = previous.get(metric)

        if cur_val is None or prev_val is None:
            continue
        if not isinstance(cur_val, (int, float)) or not isinstance(prev_val, (int, float)):
            continue

        is_pp = metric in _MARGIN_METRICS

        if is_pp:
            # Absolute difference in percentage points
            change = abs(cur_val - prev_val)
        else:
            # Percentage change
            if prev_val == 0:
                continue
            change = abs(cur_val - prev_val) / abs(prev_val)

        if change > threshold:
            alerts.append(
                QoQAlert(
                    metric_name=metric,
                    current_value=float(cur_val),
                    previous_value=float(prev_val),
                    change=round(change, 4),
                    is_percentage_point=is_pp,
                )
            )

    # Sort by magnitude of change descending and return top 2
    alerts.sort(key=lambda a: a.change, reverse=True)
    return alerts[:2]


# ---------------------------------------------------------------------------
# ValuationEngine (per D-15)
# ---------------------------------------------------------------------------


class ValuationEngine(BaseEngine):
    """Valuation engine: DCF, peer comparison, scenario analysis for stocks; NVT + TVL for crypto.

    Data injected via constructor (store-backed pattern matching FundamentalEngine).
    """

    def __init__(
        self,
        financial_data: list[dict] | None = None,  # type: ignore[type-arg]
        peer_data: list[dict] | None = None,  # type: ignore[type-arg]
        macro_rates: dict[str, float] | None = None,
        shares_outstanding: float | None = None,
        nvt_data: dict[str, float] | None = None,
        tvl_data: dict[str, float] | None = None,
    ) -> None:
        """Initialize ValuationEngine.

        Args:
            financial_data: List of annual financial dicts with operating_cash_flow, capex, revenue.
            peer_data: List of sector peer metric dicts with pe, pb, ev_ebitda.
            macro_rates: Dict with risk_free_rate, beta, etc.
            shares_outstanding: Total shares outstanding.
            nvt_data: Dict with market_cap, volume_24h for NVT proxy (crypto).
            tvl_data: Dict with market_cap, tvl for TVL proxy (DeFi crypto).
        """
        self._financial_data = financial_data
        self._peer_data = peer_data
        self._macro_rates = macro_rates or {}
        self._shares_outstanding = shares_outstanding or 0
        self._nvt_data = nvt_data
        self._tvl_data = tvl_data

    @property
    def category(self) -> str:
        """Return engine category."""
        return "valuation"

    @property
    def supports_stocks(self) -> bool:
        """Valuation applies to stocks."""
        return True

    @property
    def supports_crypto(self) -> bool:
        """Valuation applies to crypto (via NVT/TVL proxy per D-13)."""
        return True

    def analyze(
        self, asset_id: int, asset_symbol: str, df: pd.DataFrame
    ) -> Signal:
        """Run valuation analysis. Never raises."""
        try:
            return self._analyze_impl(asset_id, asset_symbol, df)
        except Exception as exc:
            logger.warning(
                "valuation_engine_error",
                asset_id=asset_id,
                asset_symbol=asset_symbol,
                error=str(exc),
            )
            return Signal(
                category="valuation",
                score=0.0,
                confidence=0.0,
                reasoning=f"Valuation analysis failed: {exc}",
                indicators={},
                data_quality={"error": str(exc)},
            )

    def _analyze_impl(
        self, asset_id: int, asset_symbol: str, df: pd.DataFrame
    ) -> Signal:
        """Internal analysis dispatch -- stocks vs crypto."""
        # Determine if stock or crypto
        is_stock = self._financial_data is not None or asset_symbol in IDX_SECTOR_MAP

        if is_stock:
            return self._analyze_stock(asset_id, asset_symbol, df)
        return self._analyze_crypto(asset_id, asset_symbol, df)

    # ------------------------------------------------------------------
    # Stock valuation
    # ------------------------------------------------------------------

    def _analyze_stock(
        self, asset_id: int, asset_symbol: str, df: pd.DataFrame
    ) -> Signal:
        """Full DCF + peer + scenario valuation for stocks."""
        if not self._financial_data:
            return Signal(
                category="valuation",
                score=0.0,
                confidence=0.0,
                reasoning="No financial data available",
                indicators={},
                data_quality={"reason": "no_financial_data"},
            )

        latest = self._financial_data[0]
        indicators: dict[str, object] = {}

        # 1. Compute FCF
        ocf = latest.get("operating_cash_flow", 0) or 0
        capex = latest.get("capex", 0) or 0
        fcf = ocf - abs(capex)
        indicators["fcf"] = fcf

        # 2. Compute revenue CAGR from historical data
        cagr = self._compute_revenue_cagr()
        cagr = min(cagr, 0.05)  # Cap at 5% GDP growth per D-11
        indicators["revenue_cagr"] = round(cagr, 4)

        # 3. Compute WACC
        risk_free_rate = self._macro_rates.get("risk_free_rate", 0.06)
        beta = self._macro_rates.get("beta", 1.0)
        wacc = _compute_wacc(risk_free_rate=risk_free_rate, beta=beta)
        indicators["wacc"] = round(wacc, 4)

        # 4. Run DCF
        fair_value = _compute_dcf(
            fcf=fcf,
            growth_rate=cagr,
            wacc=wacc,
            shares_outstanding=self._shares_outstanding,
        )
        indicators["dcf_fair_value"] = round(fair_value, 2)

        # 5. Current price from DataFrame
        current_price = 0.0
        if not df.empty and "close" in df.columns:
            current_price = float(df["close"].iloc[-1])
        indicators["current_price"] = current_price

        # 6. Margin of safety
        if current_price > 0 and fair_value > 0:
            margin = (fair_value - current_price) / current_price
        else:
            margin = 0.0
        indicators["margin_of_safety"] = round(margin, 4)

        # 7. Peer comparison
        peer_score = 0.0
        peer_label = "n/a"
        if self._peer_data:
            sector_avg = self._peer_data[0]  # First entry is sector averages
            stock_metrics = {}
            for fd in self._financial_data:
                for key in ("pe", "pb", "ev_ebitda"):
                    if key in fd and fd[key] is not None:
                        stock_metrics[key] = fd[key]
            if stock_metrics and sector_avg:
                peer_score, peer_label = _compute_peer_score(stock_metrics, sector_avg)
        indicators["peer_score"] = round(peer_score, 4)
        indicators["peer_rank"] = peer_label

        # 8. Scenario analysis
        std_dev = self._compute_revenue_std()
        scenarios = _compute_scenarios(
            current_price=current_price,
            fair_value=fair_value,
            cagr=cagr,
            std_dev=std_dev,
        )
        indicators["scenarios"] = scenarios

        # Store enriched data for bot display (two-process boundary)
        indicators["fair_value"] = round(fair_value, 2)
        sector = IDX_SECTOR_MAP.get(asset_symbol)
        indicators["sector"] = sector
        indicators["has_pdf_data"] = True
        # Build peer comparison dict for bot display
        if self._peer_data:
            peer_display: dict[str, dict[str, object]] = {}
            _sa = self._peer_data[0]
            _sm: dict[str, float] = {}
            for _fd in self._financial_data:
                for _k in ("pe", "pb", "ev_ebitda"):
                    if _k in _fd and _fd[_k] is not None:
                        _sm[_k] = _fd[_k]
            for _k in ("pe", "pb", "ev_ebitda"):
                if _k in _sm and _k in _sa:
                    _v, _a = _sm[_k], _sa[_k]
                    _r = "cheap" if _a > 0 and _v / _a < 0.85 else ("expensive" if _a > 0 and _v / _a > 1.15 else "fair")
                    peer_display[_k] = {"value": _v, "sector_avg": _a, "rank": _r}
            indicators["peer_comparison"] = peer_display
        # Store period from financial data
        indicators["period"] = latest.get("period", "N/A")

        # 9. Score from margin of safety
        mos_score = _margin_of_safety_to_score(margin)

        # Blend DCF score with peer score (if available)
        if peer_score != 0.0:
            score = 0.7 * mos_score + 0.3 * peer_score
        else:
            score = mos_score
        score = max(-1.0, min(1.0, round(score, 4)))

        # 10. Confidence
        confidence = self._compute_confidence()

        # Reasoning
        reasoning_parts = []
        if fair_value > 0:
            reasoning_parts.append(f"DCF fair value={fair_value:.2f}")
        reasoning_parts.append(f"MoS={margin:.1%}")
        if peer_label != "n/a":
            reasoning_parts.append(f"Peer rank={peer_label}")
        weighted_ret = scenarios.get("weighted_return", 0)
        if isinstance(weighted_ret, (int, float)):
            reasoning_parts.append(f"Scenario weighted return={weighted_ret:.1%}")
        reasoning = "; ".join(reasoning_parts)

        return Signal(
            category="valuation",
            score=score,
            confidence=round(confidence, 4),
            reasoning=reasoning,
            indicators=indicators,
            data_quality={
                "financial_periods": len(self._financial_data),
                "has_peer_data": bool(self._peer_data),
                "has_macro_rates": bool(self._macro_rates),
            },
        )

    # ------------------------------------------------------------------
    # Crypto valuation
    # ------------------------------------------------------------------

    def _analyze_crypto(
        self, asset_id: int, asset_symbol: str, df: pd.DataFrame
    ) -> Signal:
        """NVT + TVL proxy valuation for crypto assets."""
        has_tvl = self._tvl_data is not None
        has_nvt = self._nvt_data is not None

        if not has_tvl and not has_nvt:
            return Signal(
                category="valuation",
                score=0.0,
                confidence=0.0,
                reasoning="No valuation data available for crypto",
                indicators={},
                data_quality={"reason": "no_crypto_valuation_data"},
            )

        tvl_score, tvl_conf, tvl_reason = _compute_tvl_proxy(self._tvl_data)
        nvt_score, nvt_conf, nvt_reason = _compute_nvt_proxy(self._nvt_data)

        # Combine if both available
        if has_tvl and tvl_conf > 0 and has_nvt and nvt_conf > 0:
            score = 0.6 * tvl_score + 0.4 * nvt_score
            confidence = max(tvl_conf, nvt_conf)
            reasoning = f"TVL: {tvl_reason}; NVT: {nvt_reason}"
        elif has_tvl and tvl_conf > 0:
            score = tvl_score
            confidence = tvl_conf
            reasoning = tvl_reason
        else:
            score = nvt_score
            confidence = nvt_conf
            reasoning = nvt_reason

        score = max(-1.0, min(1.0, round(score, 4)))

        return Signal(
            category="valuation",
            score=score,
            confidence=round(confidence, 4),
            reasoning=reasoning,
            indicators={
                "nvt_score": nvt_score,
                "nvt_confidence": nvt_conf,
                "tvl_score": tvl_score,
                "tvl_confidence": tvl_conf,
            },
            data_quality={
                "has_nvt_data": has_nvt,
                "has_tvl_data": has_tvl,
            },
        )

    # ------------------------------------------------------------------
    # Helper methods
    # ------------------------------------------------------------------

    def _compute_revenue_cagr(self) -> float:
        """Compute revenue CAGR from historical financial_data."""
        if not self._financial_data or len(self._financial_data) < 2:
            return 0.03  # Default conservative growth

        revenues = [
            d.get("revenue", 0) or 0 for d in self._financial_data
        ]
        # Filter out zeros
        revenues = [r for r in revenues if r > 0]
        if len(revenues) < 2:
            return 0.03

        # CAGR = (end/start)^(1/n) - 1
        # financial_data[0] is latest, [-1] is oldest
        latest_rev = revenues[0]
        oldest_rev = revenues[-1]
        years = len(revenues) - 1

        if oldest_rev <= 0:
            return 0.03

        cagr = (latest_rev / oldest_rev) ** (1.0 / years) - 1
        return max(0.0, cagr)  # Floor at 0

    def _compute_revenue_std(self) -> float:
        """Compute standard deviation of revenue growth rates."""
        if not self._financial_data or len(self._financial_data) < 2:
            return 0.05  # Default volatility

        revenues = [
            d.get("revenue", 0) or 0 for d in self._financial_data
        ]
        revenues = [r for r in revenues if r > 0]
        if len(revenues) < 2:
            return 0.05

        growth_rates = []
        for i in range(len(revenues) - 1):
            if revenues[i + 1] > 0:
                gr = (revenues[i] / revenues[i + 1]) - 1
                growth_rates.append(gr)

        if not growth_rates:
            return 0.05

        return float(np.std(growth_rates))

    def _compute_confidence(self) -> float:
        """Compute confidence based on data availability.

        0.7 with full data, 0.4 with partial, 0.0 with none.
        """
        score = 0.0
        total = 4  # financial_data, peer_data, macro_rates, shares

        if self._financial_data and len(self._financial_data) >= 2:
            score += 1.0
        elif self._financial_data:
            score += 0.5

        if self._peer_data:
            score += 1.0

        if self._macro_rates:
            score += 1.0

        if self._shares_outstanding and self._shares_outstanding > 0:
            score += 1.0

        ratio = score / total
        # Scale to 0.0-0.7 range
        return ratio * 0.7
