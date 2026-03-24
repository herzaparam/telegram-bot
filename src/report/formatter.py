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


def format_scorecard_error() -> str:
    """Format scorecard error message per UI-SPEC copywriting."""
    return "\u26a0\ufe0f Failed to load scorecard data. Try again in a few minutes."


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
