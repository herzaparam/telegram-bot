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
    db_password: str = "trade_dev"
    database_url: str = "postgresql+asyncpg://trade:trade_dev@localhost:5432/trade_agent"
    database_url_sync: str = "postgresql://trade:trade_dev@localhost:5432/trade_agent"

    # LLM
    openai_api_key: SecretStr = SecretStr("")
    llm_primary_model: str = "gpt-4o-mini"
    llm_fallback_model: str = "gemini/gemini-2.0-flash"
    llm_max_retries: int = 3
    llm_timeout: int = 30

    # Telegram
    telegram_bot_token: SecretStr = SecretStr("")
    telegram_chat_id: str = ""

    # Telegram webhook
    webhook_base_url: str = ""
    telegram_webhook_secret: str = ""

    # Logging
    log_level: str = "INFO"
    log_format: str = "json"

    # Pipeline timeouts (seconds)
    timeout_fetch: int = 60
    timeout_analyze: int = 120
    timeout_llm: int = 30
    timeout_decide_per_call: int = 12
    timeout_evaluate: int = 60
    timeout_report: int = 30

    # Technical engine indicator weights (sum to 1.0)
    weight_rsi: float = 0.20
    weight_macd: float = 0.20
    weight_bollinger: float = 0.15
    weight_ema: float = 0.20
    weight_volume: float = 0.10
    weight_overall_trend: float = 0.15

    # Quantitative engine component weights
    weight_momentum: float = 0.35
    weight_mean_reversion: float = 0.35
    weight_arima: float = 0.30


settings = Settings()
