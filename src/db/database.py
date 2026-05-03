"""Async database engine and session factory."""

from collections.abc import AsyncGenerator
from typing import Any
from urllib.parse import urlsplit

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.config import settings


def asyncpg_connect_kwargs() -> dict[str, Any]:
    """Parse settings.database_url into kwargs for asyncpg.connect.

    Why: asyncpg's URI parser mishandles passwords containing characters like
    '/', causing 'invalid literal for int()' when it tries to parse the rest of
    the URL as a port. urlsplit decodes percent-encoded chars correctly, and
    asyncpg's kwargs interface bypasses the URI parser entirely.
    """
    parts = urlsplit(settings.database_url.replace("postgresql+asyncpg://", "postgresql://"))
    return {
        "host": parts.hostname,
        "port": parts.port,
        "user": parts.username,
        "password": parts.password,
        "database": parts.path.lstrip("/") or None,
    }

engine = create_async_engine(
    settings.database_url,
    echo=False,
    pool_size=5,
    max_overflow=10,
)

async_session_factory = async_sessionmaker(engine, expire_on_commit=False)


async def get_session() -> AsyncGenerator[AsyncSession]:
    """Yield an async database session."""
    async with async_session_factory() as session:
        yield session


async def init_db() -> None:
    """Initialize the database engine (used by pipeline/bot startup).

    Verifies database connectivity on startup.
    """
    async with engine.begin() as conn:
        await conn.execute(text("SELECT 1"))
