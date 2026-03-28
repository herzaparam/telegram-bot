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
    timeout_reflect: int = 120
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

    # External API keys (optional -- engines degrade gracefully when missing)
    fred_api_key: str = ""
    finnhub_api_key: str = ""
    reddit_client_id: str = ""
    reddit_client_secret: str = ""
    github_token: str = ""  # Optional -- 60 req/hr without, 5000 with

    # Fundamental engine ratio weights (sum to 1.0) -- per D-04
    weight_fundamental_pe: float = 0.25
    weight_fundamental_pb: float = 0.15
    weight_fundamental_roe: float = 0.25
    weight_fundamental_revenue_growth: float = 0.15
    weight_fundamental_dividend_yield: float = 0.10
    weight_fundamental_debt_to_equity: float = 0.10

    # Macro engine indicator weights (sum to 1.0)
    weight_macro_fed_rate: float = 0.25
    weight_macro_cpi: float = 0.25
    weight_macro_dxy: float = 0.25
    weight_macro_usd_idr: float = 0.25

    # Sentiment engine source weights
    weight_sentiment_fear_greed: float = 0.40
    weight_sentiment_reddit: float = 0.60

    # Monitoring
    prometheus_pushgateway_url: str = ""


settings = Settings()
