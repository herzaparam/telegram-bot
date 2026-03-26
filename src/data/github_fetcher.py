"""GitHub activity fetcher for crypto project repos.

Fetches repo stats (stars, forks, commits) from GitHub API.
Graceful degradation: returns None on any failure.
"""

from __future__ import annotations

from datetime import UTC, date, datetime

import httpx
import structlog
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession
from tenacity import retry, stop_after_attempt, wait_fixed

from src.config import settings
from src.db.models import GitHubActivity

logger = structlog.get_logger(__name__)

GITHUB_API = "https://api.github.com"

CRYPTO_REPOS: dict[str, str] = {
    "BTC": "bitcoin/bitcoin",
    "ETH": "ethereum/go-ethereum",
    "SOL": "solana-labs/solana",
}


def _build_headers() -> dict[str, str]:
    """Build GitHub API request headers."""
    headers = {"Accept": "application/vnd.github.v3+json"}
    token = settings.github_token
    if token:
        headers["Authorization"] = f"token {token}"
    return headers


@retry(stop=stop_after_attempt(2), wait=wait_fixed(3))
async def _github_get(client: httpx.AsyncClient, url: str) -> httpx.Response:
    """GET from GitHub API with retry."""
    resp = await client.get(url)
    resp.raise_for_status()

    # Rate limit warning
    remaining = resp.headers.get("X-RateLimit-Remaining")
    if remaining is not None and int(remaining) < 10:
        logger.warning("github_rate_limit_low", remaining=remaining)

    return resp


async def fetch_github_activity(
    symbol: str,
    asset_id: int,
    session: AsyncSession,
) -> dict | None:
    """Fetch GitHub repo stats for a crypto project.

    Args:
        symbol: Crypto symbol (BTC, ETH, SOL). Returns None for non-crypto.
        asset_id: Database asset ID for storing GitHubActivity rows.
        session: SQLAlchemy async session.

    Returns:
        Dict with stars, forks, weekly_commits, open_issues. None if not found or error.
    """
    repo = CRYPTO_REPOS.get(symbol)
    if repo is None:
        return None

    try:
        headers = _build_headers()

        async with httpx.AsyncClient(timeout=15.0, headers=headers) as client:
            # Fetch repo info
            repo_resp = await _github_get(client, f"{GITHUB_API}/repos/{repo}")
            repo_data = repo_resp.json()

            stars = repo_data.get("stargazers_count", 0)
            forks = repo_data.get("forks_count", 0)
            open_issues = repo_data.get("open_issues_count", 0)

            # Fetch commit activity
            commits_resp = await _github_get(client, f"{GITHUB_API}/repos/{repo}/stats/commit_activity")
            commits_data = commits_resp.json()

            weekly_commits = 0
            if isinstance(commits_data, list) and commits_data:
                weekly_commits = commits_data[-1].get("total", 0)

        # Store GitHubActivity row via UPSERT
        today = date.today()
        stmt = pg_insert(GitHubActivity).values(
            asset_id=asset_id,
            date=today,
            repo=repo,
            stars=stars,
            forks=forks,
            weekly_commits=weekly_commits,
            contributors=0,  # Would require additional API call
            fetched_at=datetime.now(UTC),
        )
        stmt = stmt.on_conflict_do_update(
            constraint="uq_github_activity_asset_date",
            set_={
                "stars": stars,
                "forks": forks,
                "weekly_commits": weekly_commits,
                "fetched_at": datetime.now(UTC),
            },
        )
        await session.execute(stmt)

        return {
            "stars": stars,
            "forks": forks,
            "weekly_commits": weekly_commits,
            "open_issues": open_issues,
        }

    except Exception as exc:
        logger.warning("github_fetch_failed", symbol=symbol, repo=repo, error=str(exc))
        return None
