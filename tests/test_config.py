"""Tests for src/config.py Settings class."""

from unittest.mock import patch

from pydantic import SecretStr


class TestSettings:
    """Test Settings class loads and validates configuration."""

    def test_default_database_url(self):
        """Settings loads DATABASE_URL with default async URL."""
        with patch.dict("os.environ", {}, clear=True):
            from src.config import Settings

            s = Settings()
        assert s.database_url == "postgresql+asyncpg://trade:trade_dev@localhost:5432/trade_agent"

    def test_database_url_from_env(self):
        """Settings reads DATABASE_URL from environment."""
        with patch.dict("os.environ", {"DATABASE_URL": "postgresql+asyncpg://custom:pw@host:5433/mydb"}, clear=True):
            from src.config import Settings

            s = Settings()
        assert s.database_url == "postgresql+asyncpg://custom:pw@host:5433/mydb"

    def test_openai_api_key_is_secret_str(self):
        """Settings validates OPENAI_API_KEY as SecretStr."""
        with patch.dict("os.environ", {"OPENAI_API_KEY": "sk-test-abc123"}, clear=True):
            from src.config import Settings

            s = Settings()
        assert isinstance(s.openai_api_key, SecretStr)
        assert s.openai_api_key.get_secret_value() == "sk-test-abc123"

    def test_default_log_level(self):
        """Settings reads LOG_LEVEL with default INFO."""
        with patch.dict("os.environ", {}, clear=True):
            from src.config import Settings

            s = Settings()
        assert s.log_level == "INFO"

    def test_log_level_from_env(self):
        """Settings reads LOG_LEVEL from environment."""
        with patch.dict("os.environ", {"LOG_LEVEL": "DEBUG"}, clear=True):
            from src.config import Settings

            s = Settings()
        assert s.log_level == "DEBUG"

    def test_default_llm_settings(self):
        """Settings has LLM defaults."""
        with patch.dict("os.environ", {}, clear=True):
            from src.config import Settings

            s = Settings()
        assert s.llm_primary_model == "gpt-4o-mini"
        assert s.llm_fallback_model == "gemini/gemini-2.0-flash"
        assert s.llm_max_retries == 3
        assert s.llm_timeout == 30

    def test_default_telegram_settings(self):
        """Settings has Telegram defaults."""
        with patch.dict("os.environ", {}, clear=True):
            from src.config import Settings

            s = Settings()
        assert isinstance(s.telegram_bot_token, SecretStr)
        assert s.telegram_chat_id == ""

    def test_default_timeout_settings(self):
        """Settings has pipeline timeout defaults."""
        with patch.dict("os.environ", {}, clear=True):
            from src.config import Settings

            s = Settings()
        assert s.timeout_fetch == 60
        assert s.timeout_analyze == 120
        assert s.timeout_llm == 30

    def test_module_level_singleton(self):
        """Module exposes a settings singleton."""
        from src.config import settings

        assert settings is not None
        assert hasattr(settings, "database_url")

    def test_database_url_sync_default(self):
        """Settings has a sync database URL for Alembic."""
        with patch.dict("os.environ", {}, clear=True):
            from src.config import Settings

            s = Settings()
        assert s.database_url_sync == "postgresql://trade:trade_dev@localhost:5432/trade_agent"
