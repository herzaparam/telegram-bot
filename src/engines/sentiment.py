"""SentimentEngine: Fear & Greed Index + Reddit sentiment analysis."""

from __future__ import annotations

import pandas as pd
import structlog

from src.config import settings
from src.engines.base import BaseEngine, Signal

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Zone-mapping functions (module-level, private)
# ---------------------------------------------------------------------------


def _fear_greed_to_score(value: float) -> float:
    """Map Fear & Greed Index value to contrarian sub-score.

    Contrarian interpretation: extreme fear = bullish opportunity.

    0-25 (Extreme Fear) -> +0.7 (contrarian bullish)
    25-45 (Fear) -> +0.3
    45-55 (Neutral) -> 0.0
    55-75 (Greed) -> -0.3
    75-100 (Extreme Greed) -> -0.7 (contrarian bearish)
    """
    if value < 25:
        return 0.7
    if value < 45:
        return 0.3
    if value <= 55:
        return 0.0
    if value <= 75:
        return -0.3
    return -0.7


def _reddit_posts_to_score(reddit_posts: list[object]) -> float:
    """Derive rough sentiment score from Reddit post list.

    Uses post scores (upvotes) as a simple sentiment proxy.
    High positive scores -> bullish crowd sentiment.
    Per D-10: LLM Reddit analysis happens in analyze_stage, not here.
    This provides a simple heuristic based on post engagement.
    """
    if not reddit_posts:
        return 0.0

    # Extract numeric scores from post dicts
    numeric_scores: list[float] = []
    for post in reddit_posts:
        if isinstance(post, dict):
            score = post.get("score")
            if score is not None:
                try:
                    numeric_scores.append(float(score))
                except (ValueError, TypeError):
                    pass

    if not numeric_scores:
        return 0.0

    avg_score = sum(numeric_scores) / len(numeric_scores)

    # Map average score to sentiment sub-score
    # High engagement (>500 avg) -> sentiment signal
    if avg_score > 1000:
        return 0.3
    if avg_score > 500:
        return 0.2
    if avg_score > 100:
        return 0.1
    if avg_score > 0:
        return 0.05
    if avg_score < -100:
        return -0.2
    if avg_score < 0:
        return -0.1
    return 0.0


# ---------------------------------------------------------------------------
# SentimentEngine
# ---------------------------------------------------------------------------


class SentimentEngine(BaseEngine):
    """Sentiment analysis engine using Fear & Greed Index and Reddit.

    Constructor accepts a SentimentSnapshot (duck-typed) to avoid circular imports.
    Accesses .fear_greed_value, .fear_greed_classification, .reddit_posts.

    Per D-12: confidence reduced 40% when Reddit data unavailable.
    """

    def __init__(
        self,
        sentiment_data: object | None = None,
    ) -> None:
        """Initialize with optional sentiment snapshot.

        Args:
            sentiment_data: SentimentSnapshot-like object with fear_greed_value,
                fear_greed_classification, and reddit_posts attributes.
                Pass None when no sentiment data is available.
        """
        self._sentiment_data = sentiment_data

    @property
    def category(self) -> str:
        """Return engine category."""
        return "sentiment"

    @property
    def supports_stocks(self) -> bool:
        return True

    @property
    def supports_crypto(self) -> bool:
        return True

    def analyze(
        self, asset_id: int, asset_symbol: str, df: pd.DataFrame
    ) -> Signal:
        """Run sentiment analysis.

        Never raises -- returns score=0/confidence=0 on failure.
        """
        try:
            return self._analyze_impl(asset_id, asset_symbol, df)
        except Exception as exc:
            logger.warning(
                "sentiment_engine_error",
                asset_id=asset_id,
                asset_symbol=asset_symbol,
                error=str(exc),
            )
            return Signal(
                category="sentiment",
                score=0.0,
                confidence=0.0,
                reasoning=f"Sentiment analysis failed: {exc}",
                indicators={},
                data_quality={"error": str(exc)},
            )

    def _analyze_impl(
        self, asset_id: int, asset_symbol: str, df: pd.DataFrame
    ) -> Signal:
        """Internal analysis implementation."""
        if self._sentiment_data is None:
            return Signal(
                category="sentiment",
                score=0.0,
                confidence=0.0,
                reasoning="No sentiment data available",
                indicators={},
                data_quality={"reason": "no_data"},
            )

        data = self._sentiment_data

        # Access duck-typed attributes
        fear_greed_value: float | None = getattr(data, "fear_greed_value", None)
        fear_greed_classification: str = getattr(
            data, "fear_greed_classification", "Unknown"
        )
        reddit_posts: list[object] | None = getattr(data, "reddit_posts", None)

        if fear_greed_value is None:
            return Signal(
                category="sentiment",
                score=0.0,
                confidence=0.0,
                reasoning="No Fear & Greed data available",
                indicators={},
                data_quality={"reason": "no_fear_greed"},
            )

        fg_value = float(fear_greed_value)
        fg_score = _fear_greed_to_score(fg_value)

        has_reddit = reddit_posts is not None and len(reddit_posts) > 0  # type: ignore[arg-type]
        reddit_score = 0.0
        if has_reddit:
            reddit_score = _reddit_posts_to_score(reddit_posts)  # type: ignore[arg-type]

        # Weighted average
        if has_reddit:
            composite = (
                fg_score * settings.weight_sentiment_fear_greed
                + reddit_score * settings.weight_sentiment_reddit
            )
            confidence_multiplier = 1.0
        else:
            # Per D-12: use Fear & Greed only with confidence reduced by 40%
            composite = fg_score
            confidence_multiplier = 0.6

        composite = max(-1.0, min(1.0, composite))

        # Base confidence from Fear & Greed signal strength (absolute value)
        base_confidence = min(1.0, abs(fg_score) / 0.7 + 0.2)
        confidence = base_confidence * confidence_multiplier
        confidence = max(0.0, min(1.0, confidence))

        # Reasoning
        fg_label = fear_greed_classification
        contrarian_label = "contrarian bullish" if fg_score > 0 else "contrarian bearish" if fg_score < 0 else "neutral"
        reasoning_parts = [
            f"Fear&Greed={fg_value:.0f} ({fg_label}) -> {contrarian_label}"
        ]
        if has_reddit:
            reddit_count = len(reddit_posts) if reddit_posts else 0  # type: ignore[arg-type]
            reasoning_parts.append(f"Reddit posts={reddit_count}")
        else:
            reasoning_parts.append("Reddit unavailable (confidence reduced)")

        if composite > 0.1:
            bias = "Bullish"
        elif composite < -0.1:
            bias = "Bearish"
        else:
            bias = "Neutral"
        reasoning_parts.append(f"{bias} sentiment bias.")

        reasoning = ", ".join(reasoning_parts[:-1]) + ". " + reasoning_parts[-1]

        indicators: dict[str, object] = {
            "fear_greed_value": fg_value,
            "fear_greed_classification": fg_label,
            "fear_greed_score": round(fg_score, 4),
            "reddit_score": round(reddit_score, 4),
            "has_reddit": has_reddit,
        }

        data_quality: dict[str, object] = {
            "has_reddit": has_reddit,
            "reddit_posts_count": len(reddit_posts) if reddit_posts is not None else 0,  # type: ignore[arg-type]
        }

        return Signal(
            category="sentiment",
            score=round(composite, 6),
            confidence=round(confidence, 4),
            reasoning=reasoning,
            indicators=indicators,
            data_quality=data_quality,
        )
