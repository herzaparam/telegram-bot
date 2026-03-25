"""Tests for sentiment fetcher (Fear & Greed + Reddit)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestFetchSentimentData:
    """Tests for fetch_sentiment_data() function."""

    @pytest.mark.asyncio
    async def test_fetch_sentiment_retrieves_fear_greed(self) -> None:
        """fetch_sentiment_data() retrieves Fear & Greed index value 0-100."""
        mock_session = AsyncMock()

        fear_greed_response = {
            "data": [{"value": "72", "value_classification": "Greed"}]
        }

        with (
            patch("src.data.sentiment_fetcher._fetch_fear_greed", return_value=(72, "Greed")),
            patch("src.data.sentiment_fetcher._fetch_reddit_posts", return_value=[]),
            patch("src.data.sentiment_fetcher.settings") as mock_settings,
        ):
            mock_settings.reddit_client_id = ""
            mock_settings.reddit_client_secret = ""

            from src.data.sentiment_fetcher import fetch_sentiment_data

            snapshot = await fetch_sentiment_data(mock_session)

        assert snapshot.fear_greed_value == 72
        assert snapshot.fear_greed_classification == "Greed"

    @pytest.mark.asyncio
    async def test_fetch_sentiment_retrieves_reddit_posts(self) -> None:
        """fetch_sentiment_data() fetches Reddit posts from r/cryptocurrency and r/finansial."""
        mock_session = AsyncMock()

        crypto_posts = [
            {"title": "Bitcoin ATH incoming", "selftext": "Analysis...", "score": 1500},
            {"title": "ETH upgrade success", "selftext": "Details...", "score": 800},
        ]
        finansial_posts = [
            {"title": "BBCA Q1 profit up", "selftext": "Results...", "score": 250},
        ]

        call_args: list[str] = []

        async def mock_reddit_posts(subreddit_name: str, limit: int = 20) -> list[dict]:
            call_args.append(subreddit_name)
            if subreddit_name == "cryptocurrency":
                return crypto_posts
            return finansial_posts

        with (
            patch("src.data.sentiment_fetcher._fetch_fear_greed", return_value=(55, "Neutral")),
            patch("src.data.sentiment_fetcher._fetch_reddit_posts", side_effect=mock_reddit_posts),
            patch("src.data.sentiment_fetcher.settings") as mock_settings,
        ):
            mock_settings.reddit_client_id = "test-client-id"
            mock_settings.reddit_client_secret = "test-client-secret"

            from src.data.sentiment_fetcher import fetch_sentiment_data

            snapshot = await fetch_sentiment_data(mock_session)

        assert "cryptocurrency" in call_args
        assert "finansial" in call_args
        assert len(snapshot.reddit_posts.get("cryptocurrency", [])) == 2
        assert len(snapshot.reddit_posts.get("finansial", [])) == 1

    @pytest.mark.asyncio
    async def test_fetch_sentiment_returns_fear_greed_only_when_reddit_missing(self) -> None:
        """fetch_sentiment_data() returns Fear & Greed only when Reddit keys missing."""
        mock_session = AsyncMock()

        with (
            patch("src.data.sentiment_fetcher._fetch_fear_greed", return_value=(30, "Fear")),
            patch("src.data.sentiment_fetcher.settings") as mock_settings,
        ):
            mock_settings.reddit_client_id = ""
            mock_settings.reddit_client_secret = ""

            from src.data.sentiment_fetcher import fetch_sentiment_data

            snapshot = await fetch_sentiment_data(mock_session)

        assert snapshot.fear_greed_value == 30
        assert snapshot.fear_greed_classification == "Fear"
        # Reddit posts should be empty dicts (no keys configured)
        assert snapshot.reddit_posts == {} or all(len(v) == 0 for v in snapshot.reddit_posts.values())

    @pytest.mark.asyncio
    async def test_fetch_sentiment_handles_errors_gracefully(self) -> None:
        """fetch_sentiment_data() handles httpx/asyncpraw errors gracefully."""
        mock_session = AsyncMock()

        with (
            patch("src.data.sentiment_fetcher._fetch_fear_greed", return_value=None),
            patch("src.data.sentiment_fetcher._fetch_reddit_posts", return_value=[]),
            patch("src.data.sentiment_fetcher.settings") as mock_settings,
        ):
            mock_settings.reddit_client_id = ""
            mock_settings.reddit_client_secret = ""

            from src.data.sentiment_fetcher import fetch_sentiment_data

            # Should not raise -- returns snapshot with None values
            snapshot = await fetch_sentiment_data(mock_session)

        assert snapshot.fear_greed_value is None
        assert snapshot.fear_greed_classification is None
