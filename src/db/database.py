"""Async database engine and session factory."""

from collections.abc import AsyncGenerator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.config import settings

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
