"""News fetcher from Indonesian RSS feeds and Finnhub REST API.

Fetches headlines from Kontan, CNBC Indonesia, and Bisnis RSS feeds,
plus Finnhub general news. Deduplicates by URL and stores new headlines
in the news_events table. Impact scoring (LLM) happens in Plan 03.

This is a SUPPLEMENTARY tier source -- all failures are caught and logged.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from time import struct_time
from typing import Any

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import settings
from src.db.models import NewsEvent

logger = structlog.get_logger(__name__)

# Indonesian financial news RSS feeds
RSS_FEEDS: dict[str, str] = {
    "kontan": "https://www.kontan.co.id/feed",
    "cnbc_id": "https://www.cnbcindonesia.com/news/rss",
    "bisnis": "https://kabar.bisnis.com/rss",
}

_FINNHUB_MAX_HEADLINES = 30


def _parse_rss_feed(feed_url: str, source_name: str) -> list[dict[str, Any]]:
    """Synchronous feedparser call returning list of headline dicts.

    Args:
        feed_url: RSS feed URL to parse.
        source_name: Logical source name for the `source` field.

    Returns:
        List of dicts with keys: headline, url, source, published_at.
        Returns empty list on any exception.
    """
    try:
        import feedparser  # noqa: PLC0415

        parsed = feedparser.parse(feed_url)
        results: list[dict[str, Any]] = []

        for entry in parsed.entries:
            headline = getattr(entry, "title", None)
            url = getattr(entry, "link", None)
            published_parsed: struct_time | None = getattr(entry, "published_parsed", None)

            if not headline or not url:
                continue

            published_at: datetime | None = None
            if published_parsed is not None:
                try:
                    published_at = datetime(*published_parsed[:6], tzinfo=timezone.utc)
                except (TypeError, ValueError):
                    published_at = None

            results.append({
                "headline": str(headline),
                "url": str(url),
                "source": source_name,
                "published_at": published_at,
            })

        return results
    except Exception as exc:  # noqa: BLE001
        log = logger.bind(component="news_fetcher")
        log.warning("rss_parse_failed", feed_url=feed_url, source=source_name, error=str(exc))
        return []


def _fetch_finnhub_news_sync(api_key: str) -> list[dict[str, Any]]:
    """Synchronous Finnhub general news fetch.

    Args:
        api_key: Finnhub API key.

    Returns:
        List of news dicts with headline, url, datetime fields.
        Returns empty list on any exception.
    """
    try:
        import finnhub  # noqa: PLC0415

        client = finnhub.Client(api_key=api_key)
        news = client.general_news("general", min_id=0)
        return news[:_FINNHUB_MAX_HEADLINES] if news else []
    except Exception as exc:  # noqa: BLE001
        log = logger.bind(component="news_fetcher")
        log.warning("finnhub_fetch_failed", error=str(exc))
        return []


async def _fetch_rss_news(session: AsyncSession) -> int:
    """Fetch headlines from all RSS sources and insert new ones.

    Args:
        session: Active SQLAlchemy async session.

    Returns:
        Number of new headlines inserted.
    """
    log = logger.bind(component="news_fetcher")
    loop = asyncio.get_event_loop()
    inserted = 0

    for source_name, feed_url in RSS_FEEDS.items():
        try:
            items = await loop.run_in_executor(None, _parse_rss_feed, feed_url, source_name)
        except Exception as exc:  # noqa: BLE001
            log.warning("rss_executor_failed", source=source_name, error=str(exc))
            continue

        for item in items:
            url = item["url"]

            # URL deduplication check
            result = await session.execute(
                select(NewsEvent).where(NewsEvent.url == url)
            )
            if result.scalar_one_or_none() is not None:
                continue

            news_event = NewsEvent(
                headline=item["headline"],
                source=item["source"],
                url=url,
                published_at=item.get("published_at"),
                impact_score=None,
                category=None,
            )
            session.add(news_event)
            inserted += 1

    return inserted


async def _fetch_finnhub_news(session: AsyncSession) -> int:
    """Fetch headlines from Finnhub and insert new ones.

    Skips entirely if FINNHUB_API_KEY is not configured.

    Args:
        session: Active SQLAlchemy async session.

    Returns:
        Number of new headlines inserted.
    """
    log = logger.bind(component="news_fetcher")

    if settings.finnhub_api_key == "":
        log.info("finnhub_api_key_missing", note="FINNHUB_API_KEY not configured, skipping")
        return 0

    loop = asyncio.get_event_loop()

    try:
        items = await loop.run_in_executor(
            None, _fetch_finnhub_news_sync, settings.finnhub_api_key
        )
    except Exception as exc:  # noqa: BLE001
        log.warning("finnhub_executor_failed", error=str(exc))
        return 0

    inserted = 0
    for item in items:
        url = item.get("url") or item.get("link") or ""
        headline = item.get("headline") or item.get("title") or ""

        if not url or not headline:
            continue

        # URL deduplication check
        result = await session.execute(
            select(NewsEvent).where(NewsEvent.url == url)
        )
        if result.scalar_one_or_none() is not None:
            continue

        published_at: datetime | None = None
        ts = item.get("datetime")
        if ts:
            try:
                published_at = datetime.fromtimestamp(int(ts), tz=timezone.utc)
            except (ValueError, TypeError, OSError):
                published_at = None

        news_event = NewsEvent(
            headline=headline,
            source="finnhub",
            url=url,
            published_at=published_at,
            impact_score=None,
            category=None,
        )
        session.add(news_event)
        inserted += 1

    return inserted


async def fetch_news(session: AsyncSession) -> None:
    """Fetch news from all sources (RSS + Finnhub) and store new headlines.

    This is a SUPPLEMENTARY tier operation -- all exceptions are caught at
    the top level and do not propagate to the pipeline.

    Args:
        session: Active SQLAlchemy async session.
    """
    log = logger.bind(component="news_fetcher")

    try:
        rss_count = await _fetch_rss_news(session)
        finnhub_count = await _fetch_finnhub_news(session)

        await session.commit()

        log.info(
            "news_fetch_complete",
            rss_inserted=rss_count,
            finnhub_inserted=finnhub_count,
            total_inserted=rss_count + finnhub_count,
        )
    except Exception as exc:  # noqa: BLE001
        log.warning("news_fetch_failed", error=str(exc))
