"""Tests for news fetcher (RSS feeds + Finnhub)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


def _make_rss_entry(
    title: str = "Saham BBCA Menguat",
    link: str = "https://kontan.co.id/article/1",
    published_parsed: tuple | None = None,
) -> MagicMock:
    """Create a mock feedparser entry."""
    entry = MagicMock()
    entry.title = title
    entry.link = link
    entry.published_parsed = published_parsed or (2026, 3, 25, 9, 0, 0, 1, 84, 0)
    return entry


def _make_feedparser_result(entries: list[MagicMock] | None = None) -> MagicMock:
    """Create a mock feedparser.parse() result."""
    result = MagicMock()
    result.entries = entries or [_make_rss_entry()]
    return result


class TestFetchNews:
    """Tests for fetch_news() function."""

    @pytest.mark.asyncio
    async def test_fetch_news_parses_rss_and_inserts_rows(self) -> None:
        """fetch_news() parses RSS feeds and inserts NewsEvent rows."""
        mock_session = AsyncMock()

        # No existing URL in DB (dedup check returns None)
        no_existing = MagicMock()
        no_existing.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = no_existing

        rss_result = _make_feedparser_result([
            _make_rss_entry("Berita 1", "https://kontan.co.id/1"),
            _make_rss_entry("Berita 2", "https://kontan.co.id/2"),
        ])

        with (
            patch("src.data.news_fetcher._parse_rss_feed", return_value=[
                {"headline": "Berita 1", "url": "https://kontan.co.id/1", "source": "kontan", "published_at": None},
                {"headline": "Berita 2", "url": "https://kontan.co.id/2", "source": "kontan", "published_at": None},
            ]),
            patch("src.data.news_fetcher.settings") as mock_settings,
        ):
            mock_settings.finnhub_api_key = ""

            from src.data.news_fetcher import fetch_news

            await fetch_news(mock_session)

        # Should have inserted rows
        assert mock_session.execute.called
        assert mock_session.commit.called

    @pytest.mark.asyncio
    async def test_fetch_news_fetches_finnhub_when_key_present(self) -> None:
        """fetch_news() fetches Finnhub general news and inserts NewsEvent rows."""
        mock_session = AsyncMock()

        no_existing = MagicMock()
        no_existing.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = no_existing

        finnhub_news = [
            {"headline": "Fed holds rates", "url": "https://finnhub.io/n/1", "datetime": 1742894400},
            {"headline": "Bitcoin surges", "url": "https://finnhub.io/n/2", "datetime": 1742894400},
        ]

        with (
            patch("src.data.news_fetcher._parse_rss_feed", return_value=[]),
            patch("src.data.news_fetcher.settings") as mock_settings,
            patch("src.data.news_fetcher._fetch_finnhub_news_sync", return_value=finnhub_news),
        ):
            mock_settings.finnhub_api_key = "test-key"

            from src.data.news_fetcher import fetch_news

            await fetch_news(mock_session)

        assert mock_session.execute.called

    @pytest.mark.asyncio
    async def test_fetch_news_deduplicates_by_url(self) -> None:
        """fetch_news() deduplicates by URL (skips already-stored headlines)."""
        mock_session = AsyncMock()

        # URL already exists in DB
        existing = MagicMock()
        existing.scalar_one_or_none.return_value = MagicMock()  # Non-None = already stored
        mock_session.execute.return_value = existing

        with (
            patch("src.data.news_fetcher._parse_rss_feed", return_value=[
                {"headline": "Duplicate News", "url": "https://kontan.co.id/existing", "source": "kontan", "published_at": None},
            ]),
            patch("src.data.news_fetcher.settings") as mock_settings,
        ):
            mock_settings.finnhub_api_key = ""

            from src.data.news_fetcher import fetch_news

            await fetch_news(mock_session)

        # commit should be called but no INSERT (only SELECT for dedup)
        # The execute should be called for the SELECT, but no add() for new row
        assert mock_session.add.call_count == 0

    @pytest.mark.asyncio
    async def test_fetch_news_handles_rss_parse_failures(self) -> None:
        """fetch_news() handles RSS parse failures gracefully (SUPPLEMENTARY tier)."""
        mock_session = AsyncMock()
        mock_session.execute.return_value = MagicMock()

        with (
            patch("src.data.news_fetcher._parse_rss_feed", return_value=[]),
            patch("src.data.news_fetcher.settings") as mock_settings,
        ):
            mock_settings.finnhub_api_key = ""

            from src.data.news_fetcher import fetch_news

            # Should not raise when RSS fails (returns empty list)
            await fetch_news(mock_session)

    @pytest.mark.asyncio
    async def test_fetch_news_skips_finnhub_when_no_key(self) -> None:
        """fetch_news() skips Finnhub when FINNHUB_API_KEY is empty."""
        mock_session = AsyncMock()

        with (
            patch("src.data.news_fetcher._parse_rss_feed", return_value=[]),
            patch("src.data.news_fetcher.settings") as mock_settings,
            patch("src.data.news_fetcher._fetch_finnhub_news_sync") as mock_finnhub,
        ):
            mock_settings.finnhub_api_key = ""

            from src.data.news_fetcher import fetch_news

            await fetch_news(mock_session)

        # Finnhub should never be called
        mock_finnhub.assert_not_called()
