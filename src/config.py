"""Centralized pydantic-settings configuration."""

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables and .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Database
    database_url: str = "postgresql+asyncpg://trade:trade@localhost:5432/trade_agent"
    database_url_sync: str = "postgresql://trade:trade@localhost:5432/trade_agent"

    # LLM
    openai_api_key: SecretStr = SecretStr("")
    llm_primary_model: str = "gpt-4o-mini"
    llm_fallback_model: str = "gemini/gemini-2.0-flash"
    llm_max_retries: int = 3
    llm_timeout: int = 30

    # Telegram
    telegram_bot_token: SecretStr = SecretStr("")
    telegram_chat_id: str = ""

    # Logging
    log_level: str = "INFO"
    log_format: str = "json"

    # Pipeline timeouts (seconds)
    timeout_fetch: int = 60
    timeout_analyze: int = 120
    timeout_llm: int = 30


settings = Settings()
