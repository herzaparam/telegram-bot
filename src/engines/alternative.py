"""AlternativeDataEngine: GitHub activity scoring for crypto projects."""

from __future__ import annotations

import pandas as pd
import structlog

from src.engines.base import BaseEngine, Signal

logger = structlog.get_logger(__name__)


class AlternativeDataEngine(BaseEngine):
    """Alternative data engine using GitHub repo activity.

    Scores crypto assets based on development activity metrics.
    Returns score=0/confidence=0 for stock assets or when no data available.
    Supplementary signal with low base confidence (0.25).
    """

    def __init__(self, github_data: dict[str, int | float] | None = None) -> None:
        """Initialize with optional pre-fetched GitHub data.

        Args:
            github_data: Dict with keys weekly_commits, stars, forks, open_issues.
                Optionally: weekly_commits_prev for trend detection.
                Pass None when data is unavailable.
        """
        self._data = github_data

    @property
    def category(self) -> str:
        """Return engine category."""
        return "alternative"

    @property
    def supports_stocks(self) -> bool:
        return False

    @property
    def supports_crypto(self) -> bool:
        return True

    def analyze(self, asset_id: int, asset_symbol: str, df: pd.DataFrame) -> Signal:
        """Run alternative data analysis. Never raises."""
        try:
            return self._analyze_impl(asset_id, asset_symbol, df)
        except Exception as exc:
            logger.warning(
                "alternative_engine_error",
                asset_id=asset_id,
                asset_symbol=asset_symbol,
                error=str(exc),
            )
            return Signal(
                category="alternative",
                score=0.0,
                confidence=0.0,
                reasoning=f"Alternative data analysis failed: {exc}",
                indicators={},
                data_quality={"error": str(exc)},
            )

    def _analyze_impl(self, asset_id: int, asset_symbol: str, df: pd.DataFrame) -> Signal:
        """Internal analysis implementation."""
        if not self._data:
            return Signal(
                category="alternative",
                score=0.0,
                confidence=0.0,
                reasoning="No alternative data available",
                indicators={},
                data_quality={"available_metrics": 0},
            )

        data = self._data
        score = 0.0

        # --- Weekly commits scoring ---
        weekly_commits = int(data.get("weekly_commits", 0))
        if weekly_commits > 50:
            score += 0.3  # Strong activity
        elif weekly_commits >= 20:
            score += 0.1  # Moderate activity
        elif weekly_commits < 10 and weekly_commits > 0:
            score -= 0.1  # Low activity
        elif weekly_commits == 0:
            score -= 0.3  # Stale project

        # --- Stars scoring ---
        stars = int(data.get("stars", 0))
        if stars > 50000:
            score += 0.1  # Established project
        elif stars < 1000:
            score -= 0.1  # Risky / unknown

        # --- Open issues relative to stars ---
        open_issues = int(data.get("open_issues", 0))
        if stars > 0:
            issue_ratio = open_issues / stars
            if issue_ratio > 0.05:
                score -= 0.1  # Concerning issue count
            elif issue_ratio < 0.01:
                score += 0.1  # Healthy project

        # --- Activity trend ---
        weekly_prev = data.get("weekly_commits_prev")
        if weekly_prev is not None:
            prev = float(weekly_prev)
            if prev > 0:
                if weekly_commits > prev * 1.1:
                    score += 0.2  # Rising commits
                elif weekly_commits < prev * 0.8:
                    score -= 0.2  # Falling commits

        # Cap score
        score = max(-1.0, min(1.0, score))

        # Confidence is always 0.25 (supplementary data)
        confidence = 0.25

        # --- Reasoning ---
        parts = []
        if weekly_commits > 50:
            parts.append(f"strong dev activity ({weekly_commits} commits/week)")
        elif weekly_commits >= 20:
            parts.append(f"moderate dev activity ({weekly_commits} commits/week)")
        elif weekly_commits == 0:
            parts.append("no recent commits (stale)")
        else:
            parts.append(f"low dev activity ({weekly_commits} commits/week)")

        if stars > 50000:
            parts.append(f"{stars:,} stars (established)")
        elif stars < 1000:
            parts.append(f"{stars:,} stars (low visibility)")

        if weekly_prev is not None and float(weekly_prev) > 0:
            if weekly_commits > float(weekly_prev) * 1.1:
                parts.append("rising activity trend")
            elif weekly_commits < float(weekly_prev) * 0.8:
                parts.append("declining activity trend")

        reasoning = ". ".join(parts) if parts else "GitHub data available but neutral"

        indicators: dict[str, object] = {
            "weekly_commits": weekly_commits,
            "stars": stars,
            "forks": int(data.get("forks", 0)),
            "open_issues": open_issues,
            "source": "github",
        }

        data_quality: dict[str, object] = {
            "has_commit_data": weekly_commits > 0,
            "has_trend_data": weekly_prev is not None,
        }

        return Signal(
            category="alternative",
            score=round(score, 6),
            confidence=round(confidence, 4),
            reasoning=reasoning,
            indicators=indicators,
            data_quality=data_quality,
        )
