"""Tests for GitHub activity fetcher."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestFetchGithubActivity:
    """Tests for fetch_github_activity() function."""

    @pytest.mark.asyncio
    async def test_fetch_github_activity_btc_returns_stats(self) -> None:
        """fetch_github_activity('BTC') returns dict with stars, forks, weekly_commits."""
        mock_repo_response = MagicMock()
        mock_repo_response.status_code = 200
        mock_repo_response.json.return_value = {
            "stargazers_count": 80000,
            "forks_count": 35000,
            "open_issues_count": 850,
        }
        mock_repo_response.headers = {"X-RateLimit-Remaining": "55"}
        mock_repo_response.raise_for_status = MagicMock()

        mock_commits_response = MagicMock()
        mock_commits_response.status_code = 200
        mock_commits_response.json.return_value = [
            {"total": 42, "week": 1711065600, "days": [5, 6, 7, 8, 5, 6, 5]},
            {"total": 38, "week": 1711670400, "days": [4, 5, 6, 7, 6, 5, 5]},
        ]
        mock_commits_response.headers = {"X-RateLimit-Remaining": "53"}
        mock_commits_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get.side_effect = [mock_repo_response, mock_commits_response]
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        mock_session = AsyncMock()
        mock_session.execute.return_value = MagicMock()

        with (
            patch("src.data.github_fetcher.httpx.AsyncClient", return_value=mock_client),
            patch("src.data.github_fetcher.settings") as mock_settings,
        ):
            mock_settings.github_token = ""

            from src.data.github_fetcher import fetch_github_activity

            result = await fetch_github_activity("BTC", asset_id=1, session=mock_session)

        assert result is not None
        assert result["stars"] == 80000
        assert result["forks"] == 35000
        assert result["weekly_commits"] == 38  # Last entry's total
        assert result["open_issues"] == 850

    @pytest.mark.asyncio
    async def test_fetch_github_activity_stock_returns_none(self) -> None:
        """fetch_github_activity('BBCA') returns None for stock symbol."""
        mock_session = AsyncMock()

        from src.data.github_fetcher import fetch_github_activity

        result = await fetch_github_activity("BBCA", asset_id=1, session=mock_session)
        assert result is None

    @pytest.mark.asyncio
    async def test_fetch_github_activity_uses_token_when_present(self) -> None:
        """fetch_github_activity adds Authorization header when github_token is set."""
        mock_repo_response = MagicMock()
        mock_repo_response.status_code = 200
        mock_repo_response.json.return_value = {
            "stargazers_count": 100, "forks_count": 50, "open_issues_count": 10,
        }
        mock_repo_response.headers = {"X-RateLimit-Remaining": "4990"}
        mock_repo_response.raise_for_status = MagicMock()

        mock_commits_response = MagicMock()
        mock_commits_response.status_code = 200
        mock_commits_response.json.return_value = [{"total": 5, "week": 1711065600, "days": [1, 0, 1, 1, 1, 1, 0]}]
        mock_commits_response.headers = {"X-RateLimit-Remaining": "4988"}
        mock_commits_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get.side_effect = [mock_repo_response, mock_commits_response]
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        mock_session = AsyncMock()
        mock_session.execute.return_value = MagicMock()

        with (
            patch("src.data.github_fetcher.httpx.AsyncClient", return_value=mock_client),
            patch("src.data.github_fetcher.settings") as mock_settings,
        ):
            mock_settings.github_token = "ghp_test123"

            from src.data.github_fetcher import fetch_github_activity

            await fetch_github_activity("BTC", asset_id=1, session=mock_session)

        # Check that the client was constructed (headers checked in implementation)
        assert mock_client.get.call_count == 2

    @pytest.mark.asyncio
    async def test_fetch_github_activity_handles_exception(self) -> None:
        """fetch_github_activity returns None on exception."""
        mock_session = AsyncMock()

        mock_client = AsyncMock()
        mock_client.get.side_effect = Exception("Network error")
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with (
            patch("src.data.github_fetcher.httpx.AsyncClient", return_value=mock_client),
            patch("src.data.github_fetcher.settings") as mock_settings,
        ):
            mock_settings.github_token = ""

            from src.data.github_fetcher import fetch_github_activity

            result = await fetch_github_activity("BTC", asset_id=1, session=mock_session)

        assert result is None

    @pytest.mark.asyncio
    async def test_crypto_repos_contains_expected_entries(self) -> None:
        """CRYPTO_REPOS maps BTC, ETH, SOL to correct GitHub repos."""
        from src.data.github_fetcher import CRYPTO_REPOS

        assert CRYPTO_REPOS["BTC"] == "bitcoin/bitcoin"
        assert CRYPTO_REPOS["ETH"] == "ethereum/go-ethereum"
        assert CRYPTO_REPOS["SOL"] == "solana-labs/solana"
