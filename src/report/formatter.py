"""Shared report formatting for Telegram messages (HTML parse_mode).

Placed in src/report/ so both the bot process and pipeline report stage
can import without crossing the two-process boundary.

Uses HTML parse_mode per D-06 research recommendation to avoid
MarkdownV2 escape issues with financial data.
"""

from __future__ import annotations

import html

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
