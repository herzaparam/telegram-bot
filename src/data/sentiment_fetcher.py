"""Sentiment data fetcher using Fear & Greed index and Reddit.

Fetches the Crypto Fear & Greed index from alternative.me and Reddit posts
from r/cryptocurrency and r/finansial. Returns a SentimentSnapshot dataclass
that is passed directly to the SentimentEngine (not stored in DB).

This is a SUPPLEMENTARY tier source -- all failures degrade gracefully.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any

import structlog

from src.config import settings

logger = structlog.get_logger(__name__)

_FEAR_GREED_URL = "https://api.alternative.me/fng/?limit=1"
_REDDIT_SUBREDDITS = ["cryptocurrency", "finansial"]


@dataclass
class SentimentSnapshot:
    """Snapshot of sentiment data retrieved from Fear & Greed + Reddit.

    Attributes:
        fear_greed_value: Fear & Greed index (0=Extreme Fear, 100=Extreme Greed).
        fear_greed_classification: Human-readable label (e.g. "Greed", "Fear").
        reddit_posts: Mapping of subreddit name to list of post dicts.
    """

    fear_greed_value: int | None = None
    fear_greed_classification: str | None = None
    reddit_posts: dict[str, list[dict[str, str]]] = field(default_factory=dict)


async def _fetch_fear_greed() -> tuple[int, str] | None:
    """Fetch the current Crypto Fear & Greed index value.

    Returns:
        Tuple of (value 0-100, classification string) or None on failure.
    """
    log = logger.bind(component="sentiment_fetcher")
    try:
        import httpx  # noqa: PLC0415

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(_FEAR_GREED_URL)
            response.raise_for_status()
            data = response.json()
            entry = data["data"][0]
            return (int(entry["value"]), str(entry["value_classification"]))
    except Exception as exc:  # noqa: BLE001
        log.warning("fear_greed_fetch_failed", error=str(exc))
        return None


async def _fetch_reddit_posts(
    subreddit_name: str, limit: int = 20
) -> list[dict[str, str]]:
    """Fetch top hot posts from a subreddit via asyncpraw.

    Returns empty list when Reddit credentials are not configured or on
    any exception (graceful degradation).

    Args:
        subreddit_name: Name of the subreddit (without r/ prefix).
        limit: Maximum number of posts to retrieve.

    Returns:
        List of dicts with keys: title, selftext, score.
    """
    log = logger.bind(component="sentiment_fetcher", subreddit=subreddit_name)

    if settings.reddit_client_id == "" or settings.reddit_client_secret == "":
        log.debug("reddit_credentials_missing", note="Skipping Reddit fetch")
        return []

    try:
        import asyncpraw  # noqa: PLC0415

        reddit = asyncpraw.Reddit(
            client_id=settings.reddit_client_id,
            client_secret=settings.reddit_client_secret,
            user_agent="trade-agent-sentiment/1.0",
        )

        posts: list[dict[str, str]] = []
        async with reddit:
            subreddit = await reddit.subreddit(subreddit_name)
            async for post in subreddit.hot(limit=limit):
                selftext = post.selftext[:200] if post.selftext else ""
                posts.append({
                    "title": str(post.title),
                    "selftext": selftext,
                    "score": str(post.score),
                })

        return posts
    except Exception as exc:  # noqa: BLE001
        log.warning("reddit_fetch_failed", subreddit=subreddit_name, error=str(exc))
        return []


async def fetch_sentiment_data(session: Any) -> SentimentSnapshot:
    """Fetch Fear & Greed index and Reddit posts concurrently.

    Reddit is only fetched when credentials are configured. This function
    always returns a SentimentSnapshot -- never raises.

    The `session` parameter is accepted for consistency with other fetcher
    signatures but is not used (sentiment data is not stored in DB).

    Args:
        session: Async DB session (unused -- sentiment data not persisted).

    Returns:
        SentimentSnapshot with all available data populated.
    """
    log = logger.bind(component="sentiment_fetcher")

    try:
        # Determine which subreddits to fetch
        if settings.reddit_client_id and settings.reddit_client_secret:
            tasks = [
                _fetch_fear_greed(),
                *[_fetch_reddit_posts(sub) for sub in _REDDIT_SUBREDDITS],
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            fg_result = results[0]
            reddit_results = results[1:]

            fear_greed_value: int | None = None
            fear_greed_classification: str | None = None
            if isinstance(fg_result, tuple):
                fear_greed_value, fear_greed_classification = fg_result

            reddit_posts: dict[str, list[dict[str, str]]] = {}
            for sub, result in zip(_REDDIT_SUBREDDITS, reddit_results):
                if isinstance(result, list):
                    reddit_posts[sub] = result
                else:
                    reddit_posts[sub] = []
        else:
            # No Reddit credentials -- only fetch Fear & Greed
            fg_result = await _fetch_fear_greed()
            fear_greed_value = None
            fear_greed_classification = None
            if isinstance(fg_result, tuple):
                fear_greed_value, fear_greed_classification = fg_result
            reddit_posts = {}

        log.info(
            "sentiment_fetch_complete",
            fear_greed_value=fear_greed_value,
            reddit_subreddits=list(reddit_posts.keys()),
        )

        return SentimentSnapshot(
            fear_greed_value=fear_greed_value,
            fear_greed_classification=fear_greed_classification,
            reddit_posts=reddit_posts,
        )

    except Exception as exc:  # noqa: BLE001
        log.warning("sentiment_fetch_failed", error=str(exc))
        return SentimentSnapshot()
