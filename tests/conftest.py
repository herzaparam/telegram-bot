"""Shared test fixtures."""

from unittest.mock import patch

import pytest


@pytest.fixture()
def test_settings():
    """Return a Settings instance with test-specific values."""
    with patch.dict(
        "os.environ",
        {
            "DATABASE_URL": "postgresql+asyncpg://test:test@localhost:5432/test_db",
            "DATABASE_URL_SYNC": "postgresql://test:test@localhost:5432/test_db",
            "OPENAI_API_KEY": "sk-test-key-12345",
            "LOG_LEVEL": "DEBUG",
        },
    ):
        from src.config import Settings

        return Settings()
