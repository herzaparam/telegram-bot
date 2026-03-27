"""Shared report formatting for Telegram messages (HTML parse_mode).

Placed in src/report/ so both the bot process and pipeline report stage
can import without crossing the two-process boundary.

Uses HTML parse_mode per D-06 research recommendation to avoid
MarkdownV2 escape issues with financial data.
"""

from __future__ import annotations

import html
from dataclasses import dataclass

MAX_MESSAGE_LENGTH = 4096

VERDICT_EMOJI: dict[str, str] = {
    "STRONG BUY": "\U0001f7e2\U0001f7e2",   # green green
    "BUY": "\U0001f7e2",                      # green
    "HOLD": "\U0001f7e1",                      # yellow
    "SELL": "\U0001f534",                      # red
    "STRONG SELL": "\U0001f534\U0001f534",     # red red
}

DEFAULT_EMOJI = "\u26aa"  # white circle for unknown/fallback

VALUATION_EMOJI: dict[str, str] = {
    "undervalued": "\U0001f7e2",   # green circle (margin > 20%)
    "fair": "\U0001f7e1",          # yellow circle (-5% to 20%)
    "overvalued": "\U0001f534",    # red circle (< -5%)
}
TREND_EMOJI: dict[str, str] = {
    "up": "\u2b06\ufe0f",         # up arrow
    "down": "\u2b07\ufe0f",       # down arrow
    "flat": "\u2796",              # minus
}
WARNING_EMOJI = "\u26a0\ufe0f"
CHART_EMOJI = "\U0001f4ca"
INFO_EMOJI = "\u2139\ufe0f"


DISCOVERY_EMOJI = "\U0001f50d"  # magnifying glass
TRIGGER_ICONS: dict[str, str] = {
    "volume_spike": "\U0001f4c8",      # chart increasing
    "price_breakout": "\U0001f680",    # rocket
    "momentum_surge": "\u26a1",        # lightning
    "statistical_anomaly": "\u2728",   # sparkles
}
SECTOR_ABOVE_EMOJI = "\U0001f7e2"   # green circle
SECTOR_BELOW_EMOJI = "\U0001f534"   # red circle
SECTOR_AT_EMOJI = "\U0001f7e1"      # yellow circle
MGMT_EMOJI: dict[str, str] = {
    "Excellent": "\u2b50",
    "Good": "\U0001f44d",
    "Fair": "\U0001f610",
    "Weak": "\u26a0\ufe0f",
    "Insufficient data": "\u2139\ufe0f",
}
CROWN_EMOJI = "\U0001f451"
OWNERSHIP_UP = "\u2b06\ufe0f"
OWNERSHIP_DOWN = "\u2b07\ufe0f"


def _truncate_reasoning(text: str, max_len: int = 100) -> str:
    """Truncate text at word boundary, appending '...' if needed."""
    if len(text) <= max_len:
        return text
    truncated = text[:max_len]
    # Find last space to break at word boundary
    last_space = truncated.rfind(" ")
    if last_space > 0:
        truncated = truncated[:last_space]
    return truncated + "..."


def _format_key_factors(key_factors: dict[str, object] | None) -> str:
    """Format key factors dict into readable text."""
    if not key_factors:
        return "None"
    lines = []
    for key, value in key_factors.items():
        lines.append(f"- {html.escape(str(key))}: {html.escape(str(value))}")
    return "\n".join(lines)


def format_asset_card(
    symbol: str,
    name: str,
    verdict: str,
    score: float,
    confidence: float,
    reasoning: str,
) -> str:
    """Format a compact asset card for the daily report.

    Per UI-SPEC Asset Card format (D-06):
        {emoji} <b>{SYMBOL}</b> ({name})
           {VERDICT} | Score: {+0.00} | Conf: {00%}
           <i>{reasoning truncated to 100 chars at word boundary}...</i>
    """
    emoji = VERDICT_EMOJI.get(verdict, DEFAULT_EMOJI)
    escaped_symbol = html.escape(symbol)
    escaped_name = html.escape(name)
    escaped_reasoning = html.escape(_truncate_reasoning(reasoning))

    return (
        f"{emoji} <b>{escaped_symbol}</b> ({escaped_name})\n"
        f"   {verdict} | Score: {score:+.2f} | Conf: {confidence:.0%}\n"
        f"   <i>{escaped_reasoning}</i>"
    )


def format_asset_detail(
    symbol: str,
    name: str,
    verdict: str,
    score: float,
    confidence: float,
    reasoning: str,
    key_factors: dict[str, object] | None,
    risk_warning: str | None,
) -> str:
    """Format a full single-asset detail view.

    Per UI-SPEC Single-Asset Detail format (TBOT-03).
    No truncation on reasoning.
    """
    emoji = VERDICT_EMOJI.get(verdict, DEFAULT_EMOJI)
    escaped_symbol = html.escape(symbol)
    escaped_name = html.escape(name)
    escaped_reasoning = html.escape(reasoning)

    lines = [
        f"<b>{emoji} {escaped_symbol} ({escaped_name})</b>",
        "",
        f"<b>Verdict:</b> {verdict}",
        f"<b>Score:</b> {score:+.2f}",
        f"<b>Confidence:</b> {confidence:.0%}",
        "",
        "<b>Reasoning:</b>",
        f"<i>{escaped_reasoning}</i>",
        "",
        "<b>Key Factors:</b>",
        _format_key_factors(key_factors),
    ]

    if risk_warning is not None:
        lines.append("")
        lines.append("<b>Risk Warning:</b>")
        lines.append(html.escape(risk_warning))

    return "\n".join(lines)


def format_report_header(
    run_date: str,
    total: int,
    distribution: dict[str, int],
    risk_warnings: list[str],
) -> str:
    """Format the report header.

    Per UI-SPEC Report Header format (D-07).
    Only shows non-zero categories in distribution.
    Omits risk warnings line when list is empty.
    """
    # Build sentiment distribution string (non-zero only)
    dist_parts = [f"{k}: {v}" for k, v in distribution.items() if v > 0]
    dist_str = " | ".join(dist_parts)

    lines = [
        f"<b>Daily Signal Report - {run_date}</b>",
        f"Assets: {total} | {dist_str}" if dist_str else f"Assets: {total}",
    ]

    if risk_warnings:
        warnings_str = " | ".join(risk_warnings)
        lines.append(f"\u26a0\ufe0f {warnings_str}")

    return "\n".join(lines)


def split_report(header: str, asset_cards: list[str]) -> list[str]:
    """Split report into messages respecting Telegram's 4096-char limit.

    Per D-08:
    - Split at asset card boundaries, never mid-card
    - First message: full header + as many cards as fit
    - Subsequent messages: continuation mini-header + remaining cards
    - Each message <= MAX_MESSAGE_LENGTH
    """
    if not asset_cards:
        return [header]

    card_break = "\n\n"
    messages: list[str] = []
    remaining_cards = list(asset_cards)

    # First message includes the full header
    current = header
    while remaining_cards:
        candidate = current + card_break + remaining_cards[0]
        if len(candidate) <= MAX_MESSAGE_LENGTH:
            current = candidate
            remaining_cards.pop(0)
        else:
            # If current message has content beyond just header, save it
            if current != header or not messages:
                messages.append(current)
                current = ""
            break
    else:
        # All cards fit
        messages.append(current)
        return messages

    # If we broke out with current having content, it was already appended
    # Handle remaining cards with continuation headers
    page = len(messages) + 1
    while remaining_cards:
        cont_header = f"<b>... continued ({page})</b>"
        current = cont_header
        while remaining_cards:
            candidate = current + card_break + remaining_cards[0]
            if len(candidate) <= MAX_MESSAGE_LENGTH:
                current = candidate
                remaining_cards.pop(0)
            else:
                break
        messages.append(current)
        page += 1

    return messages


@dataclass(frozen=True)
class EvalDisplayItem:
    """A single evaluation result for display."""

    symbol: str
    verdict: str
    change_pct: float
    was_correct: bool


# Ordered windows for scorecard display
_WINDOW_ORDER = ["24h", "3d", "7d", "30d"]

# Period label mapping for /scorecard command
_PERIOD_LABELS: dict[str, str] = {
    "7d": "7 Days",
    "30d": "30 Days",
    "90d": "90 Days",
    "all": "All Time",
}


def format_scorecard_section(
    results_by_window: dict[str, list[EvalDisplayItem]],
    weekly_trend: str | None,
) -> str:
    """Format the scorecard section for the daily report.

    Per D-18: return "" if no results in any window.
    Per D-16: iterate windows in order ["24h", "3d", "7d", "30d"].
    Per D-15: each line uses checkmark/cross emoji.
    Per D-17: trend line at bottom in italics if not None.
    """
    # D-18: skip entirely when no evaluations
    has_any = any(items for items in results_by_window.values())
    if not has_any:
        return ""

    lines: list[str] = ["<b>Yesterday's Scorecard</b>", ""]

    first_window = True
    for window in _WINDOW_ORDER:
        items = results_by_window.get(window, [])
        if not items:
            continue

        if not first_window:
            lines.append("")  # blank line between window sections

        correct = sum(1 for item in items if item.was_correct)
        total = len(items)
        lines.append(f"<b>{window} Results ({correct}/{total})</b>")

        for item in items:
            emoji = "\u2705" if item.was_correct else "\u274c"
            sign = "+" if item.change_pct >= 0 else ""
            lines.append(
                f"{emoji} {item.symbol} -- {item.verdict} -> {sign}{item.change_pct:.1f}%"
            )

        first_window = False

    if weekly_trend is not None:
        lines.append("")
        lines.append(f"<i>{weekly_trend}</i>")

    return "\n".join(lines)


def format_scorecard_message(
    period: str,
    asset_filter: str | None,
    win_rates_by_window: dict[str, tuple[int, int]],
    total_decisions: int,
    best_engine: tuple[str, float] | None,
    worst_engine: tuple[str, float] | None,
    per_asset_buyhold: list[dict[str, object]],
    recent_calls: list[dict[str, object]] | None = None,
    period_empty: bool = False,
    per_engine_accuracy: dict[str, tuple[int, int] | None] | None = None,
) -> str:
    """Format the /scorecard command response.

    Per UI-SPEC: title, win rates by window, best/worst engine,
    buy-and-hold comparison, optional recent calls for asset filter.
    """
    # Empty state
    if total_decisions == 0 and not win_rates_by_window:
        if period_empty:
            period_label = _PERIOD_LABELS.get(period, period)
            return (
                f"\u2139\ufe0f No evaluations in the last {period_label.lower()}.\n\n"
                "Try a longer period: /scorecard 30d"
            )
        return (
            "\u2139\ufe0f No scorecard data available yet.\n\n"
            "Signals need at least one day to be evaluated. "
            "Check back after the pipeline has run for two consecutive days."
        )

    period_label = _PERIOD_LABELS.get(period, period)

    # Title
    if asset_filter:
        title = f"<b>Scorecard - {asset_filter} - Last {period_label}</b>"
    else:
        title = f"<b>Scorecard - Last {period_label}</b>"

    lines: list[str] = [title, ""]

    # Win Rate by Window
    if win_rates_by_window:
        lines.append("<b>Win Rate by Window</b>")
        for window in _WINDOW_ORDER:
            if window not in win_rates_by_window:
                continue
            correct, total = win_rates_by_window[window]
            pct = round((correct / total) * 100) if total > 0 else 0
            # Pad shorter window names for alignment
            padded = f"{window}:".rjust(4)
            lines.append(f"{padded} {pct}% ({correct}/{total})")
        lines.append("")

    # Total Decisions
    lines.append(f"<b>Total Decisions:</b> {total_decisions}")
    lines.append("")

    # Best/Worst Engine
    if best_engine:
        name, rate = best_engine
        lines.append(
            f"<b>Best Engine:</b> \U0001f3c6 {name} ({rate:.0f}% at 24h)"
        )
    if worst_engine:
        name, rate = worst_engine
        lines.append(
            f"<b>Worst Engine:</b> \u26a0\ufe0f {name} ({rate:.0f}% at 24h)"
        )

    # Buy & Hold comparison
    if per_asset_buyhold:
        lines.append("")
        lines.append("<b>vs Buy & Hold</b>")
        for entry in per_asset_buyhold:
            symbol = entry["symbol"]
            sig_ret = float(entry["signal_return"])  # type: ignore[arg-type]
            bh_ret = float(entry["buyhold_return"])  # type: ignore[arg-type]
            alpha = sig_ret - bh_ret

            sig_sign = "+" if sig_ret >= 0 else ""
            bh_sign = "+" if bh_ret >= 0 else ""

            if alpha >= 0:
                alpha_str = f"<b>+{alpha:.1f}% alpha</b>"
            else:
                alpha_str = f"<i>{alpha:.1f}% underperform</i>"

            lines.append(
                f"{symbol}: Signals {sig_sign}{sig_ret:.1f}% | "
                f"B&H {bh_sign}{bh_ret:.1f}% | {alpha_str}"
            )

    # Recent Calls (asset-filtered mode)
    if asset_filter and recent_calls:
        lines.append("")
        lines.append("<b>Recent Calls</b>")
        for call in recent_calls[:5]:
            emoji = "\u2705" if call["was_correct"] else "\u274c"
            sign = "+" if float(call["change_pct"]) >= 0 else ""  # type: ignore[arg-type]
            lines.append(
                f"{emoji} {call['date']} {call['verdict']} -> "
                f"{sign}{float(call['change_pct']):.1f}% ({call['window']})"  # type: ignore[arg-type]
            )

    # Engine Breakdown (D-24): per-engine accuracy for all 15 categories
    if per_engine_accuracy:
        lines.append("")
        lines.append("<b>Engine Breakdown (24h):</b>")
        for cat in sorted(per_engine_accuracy.keys()):
            val = per_engine_accuracy[cat]
            if val is None:
                lines.append(f"  {cat}: N/A \u2014 data source unavailable")
            elif val[1] == 0:
                lines.append(f"  {cat}: no evaluations yet")
            else:
                correct, total = val
                pct = (correct / total * 100) if total > 0 else 0
                lines.append(f"  {cat}: {pct:.0f}% ({correct}/{total})")

    return "\n".join(lines)


def format_lessons_message(
    recently_learned: list[dict[str, object]],
    top_lessons: list[dict[str, object]],
    asset_filter: str | None = None,
    engine_filter: str | None = None,
) -> str:
    """Format /lessons response with two sections (D-16)."""
    lines: list[str] = []

    # Title with filters
    filters = []
    if asset_filter:
        filters.append(asset_filter)
    if engine_filter:
        filters.append(engine_filter)
    filter_str = f" ({', '.join(filters)})" if filters else ""
    lines.append(f"<b>Lessons{filter_str}</b>")
    lines.append("")

    # Recently Learned section
    if recently_learned:
        lines.append("<b>Recently Learned (7d)</b>")
        for item in recently_learned:
            tier = item.get("tier", "hypothesis")
            tier_icon = {"hypothesis": "?", "pattern": "~", "rule": "!"}.get(str(tier), "?")
            lesson_text = html.escape(str(item.get("lesson", ""))[:120])
            times_obs = item.get("times_observed", 0)
            lines.append(
                f"[{tier_icon}] {lesson_text}"
                f"\n    {tier} | seen {times_obs}x"
            )
        lines.append("")

    # Top Lessons section
    if top_lessons:
        lines.append("<b>Top Lessons (by accuracy)</b>")
        for item in top_lessons:
            accuracy_val = item.get("accuracy")
            accuracy_pct = round(float(accuracy_val) * 100) if accuracy_val else 0
            times_app = item.get("times_applied", 0)
            tier = item.get("tier", "hypothesis")
            lesson_text = html.escape(str(item.get("lesson", ""))[:120])
            lines.append(
                f"[!] {lesson_text}"
                f"\n    {tier} | {accuracy_pct}% accuracy over {times_app} uses"
            )

    if not recently_learned and not top_lessons:
        lines.append("No lessons learned yet. Check back after the pipeline runs for a few days.")

    return "\n".join(lines)


def format_lessons_applied(
    lessons_applied: dict[str, str] | None,
) -> str:
    """Format lessons applied for a single asset card in the daily report.

    Per D-19: list which lessons influenced this decision.
    Returns empty string if no lessons applied.

    Args:
        lessons_applied: Dict mapping lesson ID to lesson text from DailyDecision.lessons_applied JSONB.
    """
    if not lessons_applied:
        return ""

    lines = ["   <b>Lessons applied:</b>"]
    for lesson_id, lesson_text in list(lessons_applied.items())[:5]:
        truncated = html.escape(str(lesson_text)[:80])
        lines.append(f"   - {truncated}")

    return "\n".join(lines)


def format_news_digest(
    news_items: list[dict[str, object]],
) -> str:
    """Format the News & Events section for the daily report.

    Per D-19: Separate section at bottom of report. Top 5-10 high-impact
    headlines grouped by category. Each shows headline + source + affected
    assets + impact direction.

    Args:
        news_items: List of dicts with keys: headline, source, category,
                    impact_score, affected_assets.

    Returns:
        HTML-formatted string. Empty string if no news items.
    """
    if not news_items:
        return ""

    # Filter items with a non-None impact_score, sort by absolute score descending, take top 10
    scored = [n for n in news_items if n.get("impact_score") is not None]
    scored.sort(key=lambda n: abs(float(n.get("impact_score", 0))), reverse=True)
    top = scored[:10]

    if not top:
        return ""

    # Group by category
    by_category: dict[str, list[dict[str, object]]] = {}
    for item in top:
        cat = str(item.get("category", "other"))
        by_category.setdefault(cat, []).append(item)

    # Category display order and labels
    cat_labels = {
        "central_bank": "Central Bank",
        "earnings": "Earnings",
        "regulation": "Regulation",
        "halving": "Crypto Events",
        "macro": "Macro",
        "sector": "Sector",
        "company": "Company",
        "market": "Market",
        "other": "Other",
    }
    cat_order = [
        "central_bank",
        "earnings",
        "regulation",
        "halving",
        "macro",
        "sector",
        "company",
        "market",
        "other",
    ]

    lines: list[str] = ["<b>News &amp; Events</b>", ""]

    for cat in cat_order:
        items = by_category.get(cat)
        if not items:
            continue
        label = cat_labels.get(cat, cat.title())
        lines.append(f"<b>{label}</b>")
        for item in items:
            headline_text = html.escape(str(item.get("headline", ""))[:120])
            source_text = html.escape(str(item.get("source", "")))
            impact = float(item.get("impact_score", 0))
            direction = (
                "\U0001f7e2" if impact > 0.1
                else "\U0001f534" if impact < -0.1
                else "\u26aa"
            )

            # Affected assets
            affected = item.get("affected_assets") or {}
            if isinstance(affected, dict) and affected:
                assets_str = ", ".join(sorted(affected.keys())[:5])
            else:
                assets_str = "general"

            lines.append(f"{direction} {headline_text}")
            lines.append(f"   <i>{source_text} | {assets_str}</i>")
        lines.append("")

    return "\n".join(lines).rstrip()


def format_scorecard_error() -> str:
    """Format scorecard error message per UI-SPEC copywriting."""
    return "\u26a0\ufe0f Failed to load scorecard data. Try again in a few minutes."


def format_idr(value: float) -> str:
    """Format IDR value with unit abbreviation. Rp 2.1T, Rp 450B, Rp 12.3M."""
    abs_val = abs(value)
    sign = "-" if value < 0 else ""
    if abs_val >= 1_000_000_000_000:
        return f"{sign}Rp {abs_val / 1_000_000_000_000:.1f}T"
    if abs_val >= 1_000_000_000:
        return f"{sign}Rp {abs_val / 1_000_000_000:.0f}B"
    if abs_val >= 1_000_000:
        return f"{sign}Rp {abs_val / 1_000_000:.1f}M"
    return f"{sign}Rp {abs_val:,.0f}"


def _margin_emoji(margin: float) -> str:
    """Return valuation emoji based on margin of safety percentage."""
    if margin > 0.20:
        return VALUATION_EMOJI["undervalued"]
    if margin >= -0.05:
        return VALUATION_EMOJI["fair"]
    return VALUATION_EMOJI["overvalued"]


def _peer_rank_label(value: float, sector_avg: float) -> str:
    """Return peer rank label based on comparison to sector median."""
    if sector_avg <= 0:
        return "fair"
    ratio = value / sector_avg
    if ratio < 0.85:
        return "cheap"
    if ratio > 1.15:
        return "expensive"
    return "fair"


def format_valuation_detail(
    symbol: str,
    asset_name: str,
    current_price: float,
    fair_value: float,
    margin_of_safety: float,
    scenarios: dict[str, dict[str, float]] | None,
    peer_comparison: dict[str, dict] | None,
    sector: str | None,
    period: str,
    last_updated: str,
    has_pdf_data: bool = True,
) -> str:
    """Format /valuation command response per UI-SPEC TBOT-09.

    When has_pdf_data=False, uses the "No Data Response" template.
    """
    escaped_symbol = html.escape(symbol)
    escaped_name = html.escape(asset_name)

    if not has_pdf_data:
        # No Data Response template
        emoji = _margin_emoji(margin_of_safety)
        margin_pct = f"{margin_of_safety * 100:+.0f}"
        lines = [
            f"<b>Valuation -- {escaped_symbol} ({escaped_name})</b>",
            "",
            f"<b>Current Price:</b> Rp {current_price:,.0f}",
            f"<b>Estimated Fair Value:</b> Rp {fair_value:,.0f}",
            f"<b>Margin of Safety:</b> {emoji} {margin_pct}%",
            "",
            f"{WARNING_EMOJI} <i>Estimated from market data only -- no financial reports parsed yet. Accuracy is limited.</i>",
            "",
            f"Use /fundamentals {escaped_symbol} for available ratio data.",
        ]
        return "\n".join(lines)

    # Full valuation response
    emoji = _margin_emoji(margin_of_safety)
    margin_pct = f"{margin_of_safety * 100:+.0f}"

    lines = [
        f"<b>Valuation -- {escaped_symbol} ({escaped_name})</b>",
        "",
        f"<b>Current Price:</b> Rp {current_price:,.0f}",
        f"<b>Fair Value (DCF):</b> Rp {fair_value:,.0f}",
        f"<b>Margin of Safety:</b> {emoji} {margin_pct}%",
    ]

    # Scenario analysis
    if scenarios:
        lines.append("")
        lines.append("<b>Scenario Analysis</b>")
        for label, weight in [("Bull", "25%"), ("Base", "50%"), ("Bear", "25%")]:
            key = label.lower()
            if key in scenarios:
                sc = scenarios[key]
                sc_value = sc.get("value", 0)
                sc_return = sc.get("return_pct", 0)
                return_str = f"{sc_return * 100:+.1f}"
                lines.append(f"{label} ({weight}): Rp {sc_value:,.0f} ({return_str}%)")

    # Peer comparison
    if peer_comparison and sector:
        lines.append("")
        lines.append(f"<b>Peer Comparison ({html.escape(sector)})</b>")
        for metric_label, metric_key in [("P/E", "pe"), ("P/B", "pb"), ("EV/EBITDA", "ev_ebitda")]:
            if metric_key in peer_comparison:
                pc = peer_comparison[metric_key]
                val = pc.get("value", 0)
                avg = pc.get("sector_avg", 0)
                rank = pc.get("rank") or _peer_rank_label(val, avg)
                lines.append(f"{metric_label}: {val:.1f} (sector avg {avg:.1f}) -- {rank}")

    lines.append("")
    lines.append(f"<i>Based on {html.escape(period)} financials. Last updated {html.escape(last_updated)}.</i>")

    return "\n".join(lines)


def format_fundamentals_dashboard(
    symbol: str,
    asset_name: str,
    profitability: dict[str, dict],
    valuation_ratios: dict[str, float],
    leverage: dict[str, dict],
    cash_flow: dict[str, float],
    source_label: str,
    period: str,
    cross_validation_warnings: list[str] | None = None,
) -> str:
    """Format /fundamentals command response per UI-SPEC TBOT-13."""
    escaped_symbol = html.escape(symbol)
    escaped_name = html.escape(asset_name)

    lines = [
        f"{CHART_EMOJI} <b>Fundamentals -- {escaped_symbol} ({escaped_name})</b>",
    ]

    # Profitability section
    if profitability:
        lines.append("")
        lines.append("<b>Profitability</b>")
        label_map = {
            "net_margin": "Net Margin",
            "roe": "ROE",
            "gross_margin": "Gross Margin",
        }
        for key in ("net_margin", "roe", "gross_margin"):
            if key in profitability:
                p = profitability[key]
                value_pct = f"{p.get('value', 0) * 100:.1f}"
                trend = TREND_EMOJI.get(str(p.get("trend", "flat")), TREND_EMOJI["flat"])
                qoq = p.get("qoq_change", 0)
                qoq_str = f"{qoq * 100:+.1f}pp"
                lines.append(f"{label_map.get(key, key)}: {value_pct}% {trend} ({qoq_str})")

    # Valuation ratios section
    if valuation_ratios:
        lines.append("")
        lines.append("<b>Valuation Ratios</b>")
        ratio_labels = {"pe": "P/E", "pb": "P/B", "ev_ebitda": "EV/EBITDA"}
        for key in ("pe", "pb", "ev_ebitda"):
            if key in valuation_ratios:
                val = valuation_ratios[key]
                lines.append(f"{ratio_labels.get(key, key)}: {val:.1f}")

    # Leverage section
    if leverage:
        lines.append("")
        lines.append("<b>Leverage</b>")
        lev_labels = {"debt_equity": "Debt/Equity"}
        for key in ("debt_equity",):
            if key in leverage:
                lv = leverage[key]
                val = lv.get("value", 0)
                trend = TREND_EMOJI.get(str(lv.get("trend", "flat")), TREND_EMOJI["flat"])
                qoq = lv.get("qoq_change", 0)
                qoq_str = f"{qoq * 100:+.1f}%"
                lines.append(f"{lev_labels.get(key, key)}: {val:.2f} {trend} ({qoq_str})")

    # Cash flow section
    if cash_flow:
        lines.append("")
        lines.append("<b>Cash Flow</b>")
        cf_labels = {"operating_cf": "Operating CF", "fcf": "Free Cash Flow", "capex": "Capex"}
        for key in ("operating_cf", "fcf", "capex"):
            if key in cash_flow:
                lines.append(f"{cf_labels.get(key, key)}: {format_idr(cash_flow[key])}")

    # Cross-validation warnings (D-09)
    if cross_validation_warnings:
        lines.append("")
        for warn in cross_validation_warnings:
            lines.append(f"{WARNING_EMOJI} <i>{html.escape(warn)}</i>")

    lines.append("")
    lines.append(f"<i>Source: {html.escape(source_label)}. Period: {html.escape(period)}.</i>")

    return "\n".join(lines)


def format_portfolio_risk_snapshot(snapshot: dict) -> str:
    """Format a compact portfolio risk snapshot card for the daily report.

    Args:
        snapshot: Dict with keys: concentration, correlation_alerts,
                  var_summary, sharpe_ratio, sortino_ratio.

    Returns:
        HTML string with compact risk summary.
    """
    lines = [f"<b>{CHART_EMOJI} Portfolio Risk</b>"]

    # Concentration
    conc = snapshot.get("concentration", {})
    if conc:
        sector_pct = conc.get("sector_pct", {})
        sorted_sectors = sorted(sector_pct.items(), key=lambda x: x[1], reverse=True)
        parts = [f"{s} {v:.0f}%" for s, v in sorted_sectors[:4]]
        lines.append(f"Concentration: {' | '.join(parts)}")

    # Correlation alerts
    alerts = snapshot.get("correlation_alerts", [])
    if alerts:
        alert_strs = [f"{a[0]}/{a[1]} {a[2]:.2f}" for a in alerts[:3]]
        lines.append(f"{WARNING_EMOJI} Corr alerts: {', '.join(alert_strs)}")
    else:
        lines.append("No high-correlation alerts")

    # VaR summary
    var_sum = snapshot.get("var_summary", {})
    if var_sum:
        d95 = var_sum.get("daily_var_95", 0)
        w95 = var_sum.get("weekly_var_95", 0)
        max_dd = var_sum.get("max_drawdown", 0)
        lines.append(f"VaR (95%): {d95 * 100:.1f}% daily | {w95 * 100:.1f}% weekly")
        lines.append(f"Max DD: {max_dd * 100:.1f}%")

    # Sharpe / Sortino
    sharpe = snapshot.get("sharpe_ratio")
    sortino = snapshot.get("sortino_ratio")
    if sharpe is not None and sortino is not None:
        lines.append(f"Sharpe: {sharpe:.2f} | Sortino: {sortino:.2f}")

    return "\n".join(lines)


def format_valuation_summary(
    stocks: list[dict],
) -> str:
    """Format daily report valuation summary section per UI-SPEC REPT-03.

    Args:
        stocks: List of dicts with keys: symbol, price, fair_value, margin, has_pdf, qoq_alerts.

    Returns:
        Formatted HTML string. Empty string if stocks list is empty.
    """
    if not stocks:
        return ""

    lines = ["<b>Valuation Summary</b>", ""]
    has_estimate = False

    for stock in stocks:
        symbol = stock["symbol"]
        price = stock["price"]
        fair_value = stock["fair_value"]
        margin = stock["margin"]
        has_pdf = stock.get("has_pdf", True)

        emoji = _margin_emoji(margin)
        margin_pct = f"{margin * 100:+.0f}"

        price_str = f"Rp {price:,.0f}"
        fv_str = f"Rp {fair_value:,.0f}"

        if not has_pdf:
            fv_str += "*"
            has_estimate = True

        lines.append(f"{symbol}: {price_str} | FV {fv_str} | {emoji} {margin_pct}% MoS")

        # QoQ alert lines (max 2 per stock)
        qoq_alerts = stock.get("qoq_alerts") or []
        for alert in qoq_alerts[:2]:
            lines.append(f"{WARNING_EMOJI} {html.escape(str(alert))}")

    if has_estimate:
        lines.append("")
        lines.append("<i>* Estimated from market data</i>")

    return "\n".join(lines)


def format_watchlist_message(assets: list[tuple[str, str, str]]) -> str:
    """Format watchlist display message.

    Per UI-SPEC /watchlist Display (WTCH-03).

    Args:
        assets: List of (symbol, name, exchange) tuples.

    Returns:
        Formatted HTML message string.
    """
    if not assets:
        return (
            "<b>Your Watchlist</b>\n"
            "\n"
            "No assets in your watchlist yet.\n"
            "\n"
            "Add assets with /add BBCA or /add BTC"
        )

    lines = [f"<b>Your Watchlist ({len(assets)} assets)</b>", ""]
    for i, (symbol, name, exchange) in enumerate(assets, start=1):
        escaped_symbol = html.escape(symbol)
        escaped_name = html.escape(name)
        escaped_exchange = html.escape(exchange)
        lines.append(f"{i}. <b>{escaped_symbol}</b> - {escaped_name} ({escaped_exchange})")

    return "\n".join(lines)


def format_discovery_card(candidate: dict) -> str:
    """Format a single discovery card for Telegram HTML.

    Args:
        candidate: Dict with keys: symbol, name, asset_type, composite_score,
                   triggers, current_price, price_change_pct, volume_ratio.

    Returns:
        HTML-formatted discovery card string.
    """
    symbol = html.escape(str(candidate.get("symbol", "")))
    name = html.escape(str(candidate.get("name", "")))
    asset_type = candidate.get("asset_type", "stock")
    score = candidate.get("composite_score", 0.0)
    price = candidate.get("current_price", 0.0)
    change_pct = candidate.get("price_change_pct", 0.0)
    triggers = candidate.get("triggers", [])

    # Price formatting: IDX stocks use Rp, crypto uses $
    if asset_type == "stock":
        price_str = f"Rp {price:,.0f}"
    else:
        price_str = f"${price:,.2f}"

    change_sign = "+" if change_pct >= 0 else ""
    change_str = f"{change_sign}{change_pct:.1f}%"

    # Normalize triggers: can be dict {"volume_spike": 0.8} or list of dicts
    if isinstance(triggers, dict):
        trigger_list = [{"type": k, "name": k.replace("_", " ").title(), "score": v} for k, v in triggers.items()]
    else:
        trigger_list = [t if isinstance(t, dict) else {"type": str(t), "name": str(t), "score": 0} for t in triggers]

    # Sort triggers by score descending, take top 3
    sorted_triggers = sorted(trigger_list, key=lambda t: t.get("score", 0), reverse=True)[:3]

    # Use the first trigger's emoji as the card header emoji
    first_trigger_type = sorted_triggers[0].get("type", "") if sorted_triggers else ""
    header_emoji = TRIGGER_ICONS.get(first_trigger_type, DISCOVERY_EMOJI)

    # Format trigger list
    trigger_parts = []
    for t in sorted_triggers:
        t_type = t.get("type", "unknown")
        t_name = t.get("name", t_type.replace("_", " ").title())
        t_emoji = TRIGGER_ICONS.get(t_type, DISCOVERY_EMOJI)
        trigger_parts.append(f"{t_emoji} {html.escape(t_name)}")
    triggers_str = ", ".join(trigger_parts) if trigger_parts else "none"

    return (
        f"{header_emoji} <b>{symbol}</b> ({name}) [{asset_type}]\n"
        f"   Score: {score:.2f} | Price: {price_str} ({change_str})\n"
        f"   Triggers: {triggers_str}"
    )


def format_discovery_section(candidates: list[dict]) -> str:
    """Format the New Opportunities section for the daily report.

    Takes top 5 candidates and formats as discovery cards.
    Returns empty string if no candidates (section omitted per UI-SPEC).

    Args:
        candidates: List of discovery candidate dicts.

    Returns:
        HTML-formatted section string, or empty string if no candidates.
    """
    if not candidates:
        return ""

    from datetime import date as date_type

    top = candidates[:5]
    scan_date = date_type.today().isoformat()

    lines = [f"<b>{DISCOVERY_EMOJI} New Opportunities</b>", scan_date]
    for candidate in top:
        lines.append("")
        lines.append(format_discovery_card(candidate))

    return "\n".join(lines)


def _sector_comparison_emoji(value: float, median: float, lower_is_better: bool = False) -> tuple[str, str]:
    """Return emoji and label for sector median comparison.

    Args:
        value: The metric value.
        median: The sector median.
        lower_is_better: If True, invert coloring (for D/E ratio).

    Returns:
        Tuple of (emoji, label).
    """
    if median == 0:
        return SECTOR_AT_EMOJI, "at median"
    ratio = value / median
    if ratio > 1.10:
        if lower_is_better:
            return SECTOR_BELOW_EMOJI, "above"
        return SECTOR_ABOVE_EMOJI, "above"
    if ratio < 0.90:
        if lower_is_better:
            return SECTOR_ABOVE_EMOJI, "below"
        return SECTOR_BELOW_EMOJI, "below"
    return SECTOR_AT_EMOJI, "at median"


def format_dd_report(symbol: str, name: str, dd_data: dict) -> str:
    """Format a full due diligence report per UI-SPEC /duediligence template.

    Args:
        symbol: Ticker symbol.
        name: Company name.
        dd_data: Dict with keys: sector, sector_rank, management_quality,
                 ownership_changes, competitive_position.

    Returns:
        HTML-formatted DD report string.
    """
    escaped_symbol = html.escape(symbol)
    escaped_name = html.escape(name)
    sector = dd_data.get("sector", "Unknown")

    lines = [
        f"<b>{CHART_EMOJI} Due Diligence: {escaped_symbol}</b>",
        f"{escaped_name} | Sector: {html.escape(sector)}",
    ]

    # Sector Ranking
    sector_rank = dd_data.get("sector_rank", {})
    if sector_rank:
        lines.append("")
        lines.append("<b>Sector Ranking</b>")
        metrics = [
            ("P/E", "pe", False),
            ("P/B", "pb", False),
            ("ROE", "roe", False),
            ("Net Margin", "net_margin", False),
            ("Debt/Equity", "debt_to_equity", True),
        ]
        for label, key, lower_better in metrics:
            metric_data = sector_rank.get(key, {})
            value = metric_data.get("value", 0)
            median = metric_data.get("median", 0)
            emoji, vs_label = _sector_comparison_emoji(value, median, lower_is_better=lower_better)
            if key in ("roe", "net_margin"):
                lines.append(f"  {label}: {value:.1f}% ({emoji} {vs_label})")
            else:
                lines.append(f"  {label}: {value:.1f} ({emoji} {vs_label})")

    # Management Quality
    mgmt = dd_data.get("management_quality", {})
    if mgmt:
        lines.append("")
        lines.append("<b>Management Quality</b>")
        quality_label = mgmt.get("label", "Insufficient data")
        quality_emoji = MGMT_EMOJI.get(quality_label, INFO_EMOJI)
        score = mgmt.get("score", 0)
        cagr = mgmt.get("revenue_cagr", 0)
        roe_trend = mgmt.get("roe_trend", "stable")
        lines.append(f"  {quality_emoji} {quality_label} ({score:.2f}/1.00)")
        lines.append(f"  Revenue CAGR: {cagr:.1f}%")
        lines.append(f"  ROE Trend: {html.escape(str(roe_trend))}")

    # Ownership
    ownership = dd_data.get("ownership_changes", {})
    if ownership:
        lines.append("")
        lines.append("<b>Ownership</b>")
        holders = ownership.get("holders", [])
        if holders:
            lines.append("  Top Holders:")
            for holder in holders[:5]:
                holder_name = html.escape(str(holder.get("name", "Unknown")))
                pct = holder.get("pct", 0)
                delta = holder.get("delta", 0)
                change_emoji = OWNERSHIP_UP if delta >= 0 else OWNERSHIP_DOWN
                delta_sign = "+" if delta >= 0 else ""
                lines.append(f"  - {holder_name}: {pct:.1f}% {change_emoji} ({delta_sign}{delta:.1f}%)")
        last_updated = ownership.get("last_updated", "")
        if last_updated:
            lines.append(f"  Last updated: {html.escape(str(last_updated))}")

    # Competitive Position
    comp = dd_data.get("competitive_position", {})
    if comp:
        lines.append("")
        lines.append("<b>Competitive Position</b>")
        rank = comp.get("rank", 0)
        total = comp.get("total", 0)
        metric = comp.get("metric", "composite score")
        moat = comp.get("moat_summary", "N/A")
        lines.append(f"  Sector rank: #{rank} of {total} ({html.escape(str(metric))})")
        lines.append(f"  Moat indicators: {html.escape(str(moat))}")

    return "\n".join(lines)


def format_compare_table(symbols: list[str], data: list[dict], sector: str) -> str:
    """Format side-by-side comparison per UI-SPEC /compare template.

    Args:
        symbols: List of ticker symbols.
        data: List of dicts with keys: symbol, pe, pb, roe,
              debt_to_equity, revenue_cagr.
        sector: Sector name for header.

    Returns:
        HTML-formatted comparison table string.
    """
    if not data:
        return ""

    escaped_sector = html.escape(sector)

    # Build data lookup
    by_symbol = {d["symbol"]: d for d in data}

    # Metrics config: (label, key, higher_is_better)
    metrics = [
        ("P/E", "pe", False),
        ("P/B", "pb", False),
        ("ROE %", "roe", True),
        ("D/E", "debt_to_equity", False),
        ("Rev CAGR %", "revenue_cagr", True),
    ]

    # Compute median for each metric
    medians: dict[str, float] = {}
    for _, key, _ in metrics:
        vals = [d.get(key, 0) for d in data if d.get(key) is not None]
        if vals:
            sorted_vals = sorted(vals)
            mid = len(sorted_vals) // 2
            if len(sorted_vals) % 2 == 0:
                medians[key] = (sorted_vals[mid - 1] + sorted_vals[mid]) / 2
            else:
                medians[key] = sorted_vals[mid]
        else:
            medians[key] = 0

    # Column width
    col_w = 8
    label_w = 10

    # Header
    header_cols = "".join(f" | {html.escape(s):>{col_w - 3}s}" for s in symbols)
    header_cols += f" | {'Median':>{col_w - 3}s}"
    sep_cols = "".join(f"|{'-' * col_w}" for _ in range(len(symbols) + 1))

    lines = [
        f"<b>{CHART_EMOJI} Sector Comparison</b>",
        f"Sector: {escaped_sector}",
        "",
        "<pre>",
        f"{'Metric':<{label_w}s}{header_cols}",
        f"{'-' * label_w}{sep_cols}",
    ]

    for label, key, higher_better in metrics:
        vals = [(s, by_symbol.get(s, {}).get(key, 0)) for s in symbols]

        # Find best value
        numeric_vals = [v for _, v in vals if v is not None]
        if numeric_vals:
            best_val = max(numeric_vals) if higher_better else min(numeric_vals)
        else:
            best_val = None

        row = f"{label:<{label_w}s}"
        for sym, val in vals:
            val_str = f"{val:.1f}" if val is not None else "N/A"
            crown = CROWN_EMOJI if val is not None and val == best_val else ""
            cell = f"{val_str}{crown}"
            row += f" | {cell:>{col_w - 3}s}"

        med_val = medians.get(key, 0)
        row += f" | {med_val:>{col_w - 3}.1f}"
        lines.append(row)

    lines.append("</pre>")
    lines.append("")
    lines.append(f"{CROWN_EMOJI} = best in row")

    return "\n".join(lines)
