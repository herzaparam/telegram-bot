"""LLM-powered news impact scorer.

Batch-scores news headlines against the watchlist, updating NewsEvent rows
with impact_score, affected_assets (JSONB), and category.
"""

from __future__ import annotations

import json

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import settings
from src.db.models import NewsEvent
from src.llm.client import LLM_UNAVAILABLE, llm_completion

logger = structlog.get_logger(__name__).bind(component="news_analyzer")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MAX_HEADLINES = 50
MAX_HEADLINE_CHARS = 200

NEWS_SCORING_SYSTEM_PROMPT = """\
You are a financial news analyst. Score each headline's impact on the listed assets.

Output valid JSON array where each element has:
- headline_index: int (0-based index matching input)
- impact_score: float from -1.0 (very bearish) to +1.0 (very bullish), 0.0 if irrelevant
- affected_assets: dict of asset_symbol -> relevance_score (0.0 to 1.0)
- category: one of "central_bank", "earnings", "regulation", "halving", "macro", "sector", "company", "market", "other"

Only include assets from the watchlist that are meaningfully affected.
"""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _build_news_scoring_prompt(
    headlines: list[tuple[int, str, str]],
    watchlist: list[str],
) -> str:
    """Format headlines as numbered list with watchlist.

    Args:
        headlines: List of (index, source, headline_text) tuples.
        watchlist: List of asset symbols.

    Returns:
        Formatted user message string.
    """
    lines: list[str] = ["Headlines to score:"]
    for idx, source, headline in headlines:
        lines.append(f"{idx}. [{source}] {headline}")

    lines.append("")
    lines.append(f"Watchlist: {', '.join(watchlist)}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main function
# ---------------------------------------------------------------------------


async def score_news_impact(
    session: AsyncSession,
    watchlist_symbols: list[str],
) -> None:
    """Batch-score unscored news headlines using LLM and update NewsEvent rows.

    Queries today's unscored NewsEvent rows (impact_score IS NULL), builds
    a numbered headline list, calls the LLM with JSON mode, and updates
    each row with impact_score, affected_assets, and category.

    Args:
        session: SQLAlchemy async session.
        watchlist_symbols: List of asset symbols to evaluate headlines against.
    """
    log = logger

    # Query unscored headlines
    stmt = select(NewsEvent).where(NewsEvent.impact_score.is_(None))
    result = await session.execute(stmt)
    unscored_rows = result.scalars().all()

    if not unscored_rows:
        log.debug("no_unscored_headlines")
        return

    # Cap at MAX_HEADLINES, truncate headlines to MAX_HEADLINE_CHARS
    rows_to_score = list(unscored_rows[:MAX_HEADLINES])
    headlines: list[tuple[int, str, str]] = []
    for i, row in enumerate(rows_to_score):
        headline_text = (row.headline or "")[:MAX_HEADLINE_CHARS]
        headlines.append((i, row.source, headline_text))

    log.info(
        "scoring_headlines",
        count=len(headlines),
        total_unscored=len(unscored_rows),
    )

    # Build messages
    system_msg = {"role": "system", "content": NEWS_SCORING_SYSTEM_PROMPT}
    user_msg = {
        "role": "user",
        "content": _build_news_scoring_prompt(headlines, watchlist_symbols),
    }
    messages = [system_msg, user_msg]

    # Call LLM with JSON mode
    llm_result = await llm_completion(
        messages=messages,
        response_format={"type": "json_object"},
        timeout=settings.timeout_decide_per_call,
    )

    if llm_result is LLM_UNAVAILABLE or llm_result.content == "":
        log.warning(
            "llm_unavailable_for_news_scoring",
            headlines_count=len(headlines),
        )
        return

    # Parse JSON response
    try:
        # LLM may return an object wrapper or direct array
        raw = llm_result.content.strip()
        parsed = json.loads(raw)

        # Unwrap if wrapped in a key
        if isinstance(parsed, dict):
            # Look for array value
            for v in parsed.values():
                if isinstance(v, list):
                    parsed = v
                    break
            else:
                parsed = []

        if not isinstance(parsed, list):
            log.warning("llm_response_not_list", content_preview=raw[:100])
            return

    except json.JSONDecodeError as exc:
        log.warning(
            "llm_json_parse_error",
            error=str(exc),
            content_preview=llm_result.content[:100],
        )
        return

    # Update each scored row
    updated_count = 0
    for item in parsed:
        if not isinstance(item, dict):
            continue

        try:
            idx = int(item.get("headline_index", -1))
        except (ValueError, TypeError):
            continue

        if idx < 0 or idx >= len(rows_to_score):
            continue

        row = rows_to_score[idx]

        impact = item.get("impact_score")
        affected = item.get("affected_assets")
        category = item.get("category")

        if impact is not None:
            try:
                row.impact_score = float(impact)
            except (ValueError, TypeError):
                pass

        if isinstance(affected, dict):
            row.affected_assets = affected

        if isinstance(category, str):
            row.category = category

        updated_count += 1

    if updated_count > 0:
        await session.commit()
        log.info("news_events_scored", updated=updated_count)
    else:
        log.warning("no_rows_updated_from_llm_response")
