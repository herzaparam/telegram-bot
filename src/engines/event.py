"""EventEngine: News events analysis by category and asset relevance."""

from __future__ import annotations

import pandas as pd
import structlog

from src.engines.base import BaseEngine, Signal

logger = structlog.get_logger(__name__)

# Valid event categories that have market impact
VALID_CATEGORIES = frozenset(
    ["central_bank", "earnings", "regulation", "halving", "macro"]
)


# ---------------------------------------------------------------------------
# EventEngine
# ---------------------------------------------------------------------------


class EventEngine(BaseEngine):
    """Event analysis engine that surfaces relevant news by category.

    Filters events to:
    1. Valid categories (central_bank, earnings, regulation, halving, macro)
    2. Events affecting the current asset (via affected_assets dict)

    Score = average impact_score of relevant events.
    Confidence = min(0.8, 0.2 * number_of_relevant_events).
    """

    def __init__(
        self,
        news_events: list[dict[str, object]] | None = None,
    ) -> None:
        """Initialize with optional news events list.

        Args:
            news_events: List of dicts with keys: headline, category,
                impact_score, affected_assets (dict of symbol -> relevance_score).
        """
        self._news_events = news_events

    @property
    def category(self) -> str:
        """Return engine category."""
        return "event"

    @property
    def supports_stocks(self) -> bool:
        return True

    @property
    def supports_crypto(self) -> bool:
        return True

    def analyze(
        self, asset_id: int, asset_symbol: str, df: pd.DataFrame
    ) -> Signal:
        """Run event analysis.

        Never raises -- returns score=0/confidence=0 on failure.
        """
        try:
            return self._analyze_impl(asset_id, asset_symbol, df)
        except Exception as exc:
            logger.warning(
                "event_engine_error",
                asset_id=asset_id,
                asset_symbol=asset_symbol,
                error=str(exc),
            )
            return Signal(
                category="event",
                score=0.0,
                confidence=0.0,
                reasoning=f"Event analysis failed: {exc}",
                indicators={},
                data_quality={"error": str(exc)},
            )

    def _analyze_impl(
        self, asset_id: int, asset_symbol: str, df: pd.DataFrame
    ) -> Signal:
        """Internal analysis implementation."""
        if not self._news_events:
            return Signal(
                category="event",
                score=0.0,
                confidence=0.0,
                reasoning="No events detected",
                indicators={},
                data_quality={"total_events": 0, "relevant_events": 0},
            )

        # Filter by valid category
        category_filtered = [
            e for e in self._news_events
            if isinstance(e, dict) and e.get("category") in VALID_CATEGORIES
        ]

        # Filter to events affecting current asset
        relevant_events = []
        for event in category_filtered:
            affected_assets = event.get("affected_assets")
            if isinstance(affected_assets, dict) and asset_symbol in affected_assets:
                relevant_events.append(event)

        if not relevant_events:
            return Signal(
                category="event",
                score=0.0,
                confidence=0.0,
                reasoning="No relevant events for this asset",
                indicators={},
                data_quality={
                    "total_events": len(self._news_events),
                    "relevant_events": 0,
                },
            )

        # Aggregate impact scores
        impact_scores = []
        for event in relevant_events:
            score = event.get("impact_score")
            if score is not None:
                try:
                    impact_scores.append(float(score))
                except (ValueError, TypeError):
                    pass

        if not impact_scores:
            return Signal(
                category="event",
                score=0.0,
                confidence=0.0,
                reasoning="Events found but no impact scores available",
                indicators={},
                data_quality={
                    "total_events": len(self._news_events),
                    "relevant_events": len(relevant_events),
                },
            )

        composite = sum(impact_scores) / len(impact_scores)
        composite = max(-1.0, min(1.0, composite))

        # Confidence scales with number of relevant events
        n_relevant = len(relevant_events)
        confidence = min(0.8, 0.2 * n_relevant)

        # Reasoning: top 3 headlines
        top_events = relevant_events[:3]
        headline_parts = []
        for evt in top_events:
            headline = evt.get("headline", "Unknown event")
            cat = evt.get("category", "unknown")
            headline_parts.append(f"[{cat}] {headline}")

        reasoning = f"{n_relevant} relevant event(s). " + "; ".join(headline_parts)

        indicators: dict[str, object] = {
            "total_events": len(self._news_events),
            "relevant_events": n_relevant,
            "avg_impact_score": round(composite, 4),
        }

        data_quality: dict[str, object] = {
            "total_events": len(self._news_events),
            "relevant_events": n_relevant,
            "category_filtered": len(category_filtered),
        }

        return Signal(
            category="event",
            score=round(composite, 6),
            confidence=round(confidence, 4),
            reasoning=reasoning,
            indicators=indicators,
            data_quality=data_quality,
        )
