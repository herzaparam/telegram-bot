"""Prompt construction for LLM decision maker.

Builds system and user messages for the trading verdict LLM call,
including contradiction detection sections and event stubs.
"""

from __future__ import annotations

from src.db.models import Asset, SignalRecord


_SYSTEM_PROMPT = """\
You are a concise financial analyst. Analyze the engine signals below and produce a trading verdict.

Output valid JSON with exactly these keys:
- verdict: one of "STRONG BUY", "BUY", "HOLD", "SELL", "STRONG SELL"
- score: float from -1.0 to 1.0 (negative = bearish, positive = bullish)
- confidence: float from 0.0 to 1.0
- reasoning: 100-200 words, data-driven, lead with verdict and key factors
- key_factors: list of 3-5 short strings identifying the main drivers
- risk_warning: string describing key risks, or null if none

Identify any contradictions between engine signals. When engines disagree, explain why and lower your confidence.

If lessons from past mistakes are provided, incorporate them into your analysis. Weight lessons with higher accuracy more heavily."""

_STRICT_RETRY_PREFIX = """\
IMPORTANT: Your previous response was not valid JSON or was missing required fields. \
You MUST output ONLY valid JSON with ALL of these keys: verdict, score, confidence, \
reasoning, key_factors, risk_warning. No other text.

"""


def _format_indicators(indicators: dict[str, object] | None) -> str:
    """Format top 6 indicator key=value pairs as a compact string."""
    if not indicators:
        return ""
    items = list(indicators.items())[:6]
    return ", ".join(f"{k}={v}" for k, v in items)


def _format_engine_data(
    asset: Asset,
    signals: list[SignalRecord],
    contradictions: list[str],
    lessons: list[dict[str, object]] | None = None,
    dd_flags: list[dict[str, str]] | None = None,
) -> str:
    """Build the user message content with engine data.

    Args:
        asset: The asset being analyzed.
        signals: List of signal records from engines.
        contradictions: List of contradiction description strings.
        lessons: Optional list of lesson dicts for injection.
        dd_flags: Optional list of due diligence flag dicts with severity/message.

    Returns:
        Formatted user message string.
    """
    lines: list[str] = []
    lines.append(f"Asset: {asset.symbol} ({asset.name or asset.asset_type})")
    lines.append("")

    for sig in signals:
        indicator_str = _format_indicators(sig.indicators)
        parts = [f"{sig.category.title()}: score={sig.score:+.2f}, conf={sig.confidence:.1f}"]
        if indicator_str:
            parts.append(indicator_str)
        lines.append(", ".join(parts))

    if contradictions:
        lines.append("")
        lines.append(f"Contradictions detected: {'; '.join(contradictions)}")

    if dd_flags:
        lines.append("")
        lines.append("DUE DILIGENCE FLAGS:")
        for flag in dd_flags:
            severity = flag.get("severity", "info")
            lines.append(f"  [{severity.upper()}] {flag['message']}")

    lines.append("")
    lines.append("Upcoming Events: No event data available yet.")

    if lessons:
        asset_lessons = [l for l in lessons if l.get("asset_type") != "all"]
        general_lessons = [l for l in lessons if l.get("asset_type") == "all"]

        if asset_lessons:
            lines.append("")
            lines.append("ASSET-SPECIFIC LESSONS:")
            for i, l in enumerate(asset_lessons, 1):
                accuracy = f"{l['accuracy']:.0%}" if l.get("accuracy") else "N/A"
                engines = ", ".join(l.get("engine_tags") or []) or "general"
                lines.append(
                    f"{i}. {l['lesson']} (engine: {engines}, accuracy: {accuracy} over {l.get('times_applied', 0)} uses)"
                )

        if general_lessons:
            lines.append("")
            lines.append("GENERAL LESSONS:")
            for i, l in enumerate(general_lessons, 1):
                accuracy = f"{l['accuracy']:.0%}" if l.get("accuracy") else "N/A"
                engines = ", ".join(l.get("engine_tags") or []) or "general"
                lines.append(
                    f"{i}. {l['lesson']} (engine: {engines}, accuracy: {accuracy} over {l.get('times_applied', 0)} uses)"
                )

    return "\n".join(lines)


def build_decision_prompt(
    asset: Asset,
    signals: list[SignalRecord],
    contradictions: list[str],
    lessons: list[dict[str, object]] | None = None,
    dd_flags: list[dict[str, str]] | None = None,
) -> list[dict[str, str]]:
    """Build the system + user messages for the LLM decision call.

    Args:
        asset: The asset being analyzed.
        signals: List of signal records from engines.
        contradictions: List of contradiction description strings.
        lessons: Optional list of lesson dicts for injection.
        dd_flags: Optional list of due diligence flag dicts.

    Returns:
        List of two message dicts (system, user).
    """
    return [
        {"role": "system", "content": _SYSTEM_PROMPT},
        {"role": "user", "content": _format_engine_data(asset, signals, contradictions, lessons, dd_flags=dd_flags)},
    ]


def build_strict_retry_prompt(
    asset: Asset,
    signals: list[SignalRecord],
) -> list[dict[str, str]]:
    """Build messages with stricter JSON instructions for retry.

    Args:
        asset: The asset being analyzed.
        signals: List of signal records from engines.

    Returns:
        List of two message dicts (system with strict prefix, user).
    """
    return [
        {"role": "system", "content": _STRICT_RETRY_PREFIX + _SYSTEM_PROMPT},
        {"role": "user", "content": _format_engine_data(asset, signals, [])},
    ]
