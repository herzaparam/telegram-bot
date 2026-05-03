"""Async database engine and session factory."""

from collections.abc import AsyncGenerator
from typing import Any
from urllib.parse import unquote

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.config import settings


def asyncpg_connect_kwargs() -> dict[str, Any]:
    """Parse settings.database_url into kwargs for asyncpg.connect.

    Why: both asyncpg's URI parser and urllib.parse.urlsplit choke on passwords
    containing '/', '@', or ':' — they end up reading the password as the port.
    This parser is tolerant: it splits on the LAST '@' (hosts can't contain '@')
    and the FIRST ':' inside userinfo (usernames can't contain ':'), so the
    password can hold any of those chars unencoded.
    """
    raw = settings.database_url.replace("postgresql+asyncpg://", "postgresql://")
    if not raw.startswith("postgresql://"):
        raise ValueError(f"unsupported database URL scheme: {raw!r}")
    rest = raw[len("postgresql://") :]

    if "@" in rest:
        userinfo, hostpart = rest.rsplit("@", 1)
    else:
        userinfo, hostpart = "", rest

    if ":" in userinfo:
        user, password = userinfo.split(":", 1)
    else:
        user, password = userinfo, ""

    if "/" in hostpart:
        hostport, database = hostpart.split("/", 1)
        database = database.split("?", 1)[0]
    else:
        hostport, database = hostpart, ""

    if ":" in hostport:
        host, port_s = hostport.rsplit(":", 1)
        port = int(port_s) if port_s else None
    else:
        host, port = hostport, None

    return {
        "host": host or None,
        "port": port,
        "user": unquote(user) if user else None,
        "password": unquote(password) if password else None,
        "database": unquote(database) if database else None,
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
