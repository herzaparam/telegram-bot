"""SQLAlchemy ORM models for Phase 1 tables."""

import uuid
from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    MetaData,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

# Naming conventions for constraints (required for Alembic reversible migrations)
convention = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    """Base class for all ORM models."""

    metadata = MetaData(naming_convention=convention)


class Asset(Base):
    """Tracked assets (stocks and crypto)."""

    __tablename__ = "assets"
    __table_args__ = (UniqueConstraint("symbol", "asset_type"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    symbol: Mapped[str] = mapped_column(String(20), nullable=False)
    name: Mapped[str | None] = mapped_column(String(100))
    asset_type: Mapped[str] = mapped_column(String(10), nullable=False)
    exchange: Mapped[str | None] = mapped_column(String(20))
    yfinance_symbol: Mapped[str | None] = mapped_column(String(20))
    ccxt_symbol: Mapped[str | None] = mapped_column(String(30))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class PipelineRun(Base):
    """Pipeline execution tracking per (run_date, stage)."""

    __tablename__ = "pipeline_runs"
    __table_args__ = (UniqueConstraint("run_date", "stage"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_date: Mapped[date] = mapped_column(Date, nullable=False)
    stage: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    metadata_: Mapped[dict[str, object] | None] = mapped_column("metadata", JSONB, nullable=True)


class PipelineAssetRun(Base):
    """Per-asset tracking within a pipeline stage run."""

    __tablename__ = "pipeline_asset_runs"
    __table_args__ = (UniqueConstraint("run_id", "asset_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("pipeline_runs.id"), nullable=False)
    asset_id: Mapped[int] = mapped_column(Integer, ForeignKey("assets.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)


class DailyDecision(Base):
    """Daily trading decision per asset with look-ahead bias prevention."""

    __tablename__ = "daily_decisions"
    __table_args__ = (UniqueConstraint("asset_id", "date"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    asset_id: Mapped[int] = mapped_column(Integer, ForeignKey("assets.id"), nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    verdict: Mapped[str] = mapped_column(String(15), nullable=False)
    score: Mapped[float | None] = mapped_column(Numeric(4, 3), nullable=True)
    confidence: Mapped[float | None] = mapped_column(Numeric(4, 3), nullable=True)

    # Look-ahead bias prevention: record price and time at decision and evaluation separately
    decision_price: Mapped[float | None] = mapped_column(Numeric(20, 8), nullable=True)
    decision_price_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    evaluation_price: Mapped[float | None] = mapped_column(Numeric(20, 8), nullable=True)
    evaluation_price_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Signal and reasoning data
    all_signals: Mapped[dict[str, object] | None] = mapped_column(JSONB, nullable=True)
    reasoning: Mapped[str | None] = mapped_column(Text, nullable=True)
    key_factors: Mapped[dict[str, object] | None] = mapped_column(JSONB, nullable=True)
    risk_warning: Mapped[str | None] = mapped_column(Text, nullable=True)
    wait_for: Mapped[str | None] = mapped_column(Text, nullable=True)
    lessons_applied: Mapped[dict[str, object] | None] = mapped_column(JSONB, nullable=True)
    model_used: Mapped[str | None] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class PriceHistory(Base):
    """Daily OHLCV candle data stored in a TimescaleDB hypertable."""

    __tablename__ = "price_history"
    __table_args__ = (UniqueConstraint("asset_id", "time"),)

    time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), primary_key=True
    )
    asset_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("assets.id"), primary_key=True
    )
    open: Mapped[float] = mapped_column(Float, nullable=False)
    high: Mapped[float] = mapped_column(Float, nullable=False)
    low: Mapped[float] = mapped_column(Float, nullable=False)
    close: Mapped[float] = mapped_column(Float, nullable=False)
    volume: Mapped[float] = mapped_column(Float, nullable=False)
    source: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default="unknown"
    )


class PriceHistoryHourly(Base):
    """Hourly OHLCV candle data for crypto (7-day rolling retention)."""

    __tablename__ = "price_history_hourly"
    __table_args__ = (UniqueConstraint("asset_id", "time"),)

    time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), primary_key=True
    )
    asset_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("assets.id"), primary_key=True
    )
    open: Mapped[float] = mapped_column(Float, nullable=False)
    high: Mapped[float] = mapped_column(Float, nullable=False)
    low: Mapped[float] = mapped_column(Float, nullable=False)
    close: Mapped[float] = mapped_column(Float, nullable=False)
    volume: Mapped[float] = mapped_column(Float, nullable=False)
    source: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default="unknown"
    )


class BackoffState(Base):
    """Adaptive retry backoff state persisted across pipeline runs."""

    __tablename__ = "backoff_state"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source: Mapped[str] = mapped_column(String(30), unique=True, nullable=False)
    consecutive_failures: Mapped[int] = mapped_column(Integer, default=0)
    last_failure_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_success_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    current_delay_seconds: Mapped[float] = mapped_column(Float, default=1.0)


class SignalRecord(Base):
    """Engine-generated trading signal stored per asset per date per category."""

    __tablename__ = "signals"
    __table_args__ = (
        UniqueConstraint("asset_id", "date", "category", name="uq_signals_asset_date_category"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    asset_id: Mapped[int] = mapped_column(Integer, ForeignKey("assets.id"), nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    category: Mapped[str] = mapped_column(String(30), nullable=False)
    score: Mapped[float] = mapped_column(Float, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    reasoning: Mapped[str] = mapped_column(Text, nullable=False)
    indicators: Mapped[dict[str, object] | None] = mapped_column(JSONB, nullable=True)
    data_quality: Mapped[dict[str, object] | None] = mapped_column(JSONB, nullable=True)
    price_at_signal: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class Watchlist(Base):
    """Shared watchlist linking assets to the Telegram report filter (D-09)."""

    __tablename__ = "watchlist"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    asset_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("assets.id"), unique=True, nullable=False
    )
    added_by_chat_id: Mapped[str | None] = mapped_column(String(30), nullable=True)
    added_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class BotSettings(Base):
    """Bot configuration stored in DB for runtime updates via /settings (D-17)."""

    __tablename__ = "bot_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    key: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    value: Mapped[str] = mapped_column(String(200), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class Evaluation(Base):
    """Evaluation of a prior decision against actual prices at a specific window."""

    __tablename__ = "evaluations"
    __table_args__ = (
        UniqueConstraint("decision_id", "window", name="uq_evaluations_decision_window"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    decision_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("daily_decisions.id"), nullable=False
    )
    window: Mapped[str] = mapped_column(String(5), nullable=False)  # '24h','3d','7d','30d'
    eval_price: Mapped[float] = mapped_column(Numeric(20, 8), nullable=False)
    eval_price_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    change_pct: Mapped[float] = mapped_column(Numeric(8, 4), nullable=False)
    was_correct: Mapped[bool] = mapped_column(Boolean, nullable=False)
    engine_results: Mapped[dict[str, object] | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class AccuracyStats(Base):
    """Pre-computed accuracy statistics for scorecard display."""

    __tablename__ = "accuracy_stats"
    __table_args__ = (
        UniqueConstraint(
            "asset_id", "engine_name", "window", "period",
            name="uq_accuracy_stats_lookup",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    asset_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("assets.id"), nullable=True
    )
    engine_name: Mapped[str | None] = mapped_column(String(30), nullable=True)
    window: Mapped[str] = mapped_column(String(5), nullable=False)
    period: Mapped[str] = mapped_column(String(10), nullable=False)  # '7d','30d','90d','all'
    total: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    correct: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    win_rate: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class IDXHoliday(Base):
    """Indonesian stock exchange (IDX) holiday calendar."""

    __tablename__ = "idx_holidays"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    holiday_date: Mapped[date] = mapped_column(Date, unique=True, nullable=False)
    name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    year: Mapped[int] = mapped_column(Integer, nullable=False)


class Lesson(Base):
    """Learned lesson from self-evaluation feedback loop."""

    __tablename__ = "lessons"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    asset_type: Mapped[str | None] = mapped_column(String(10), nullable=True)  # "stock","crypto","all"
    engine_tags: Mapped[dict[str, object] | None] = mapped_column(JSONB, nullable=True)  # e.g. ["technical","quantitative"]
    topic: Mapped[str | None] = mapped_column(String(30), nullable=True)  # "momentum","volatility", etc.
    lesson: Mapped[str] = mapped_column(Text, nullable=False)
    source_decision_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("daily_decisions.id"), nullable=True
    )
    times_observed: Mapped[int] = mapped_column(Integer, default=1)
    times_applied: Mapped[int] = mapped_column(Integer, default=0)
    times_correct: Mapped[int] = mapped_column(Integer, default=0)
    confidence_tier: Mapped[str] = mapped_column(String(15), nullable=False, default="hypothesis")
    still_valid: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class NewsEvent(Base):
    """News headline from RSS feeds or Finnhub with optional LLM-scored impact."""

    __tablename__ = "news_events"
    __table_args__ = (UniqueConstraint("url", name="uq_news_events_url"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    headline: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str] = mapped_column(String(30), nullable=False)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    impact_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    affected_assets: Mapped[dict[str, object] | None] = mapped_column(JSONB, nullable=True)
    category: Mapped[str | None] = mapped_column(String(30), nullable=True)
    raw_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class MacroData(Base):
    """Cached FRED macro data series observations."""

    __tablename__ = "macro_data"
    __table_args__ = (
        UniqueConstraint("series_id", "observation_date", name="uq_macro_data_series_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    series_id: Mapped[str] = mapped_column(String(30), nullable=False)
    observation_date: Mapped[date] = mapped_column(Date, nullable=False)
    value: Mapped[float] = mapped_column(Float, nullable=False)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class StockFundamental(Base):
    """Cached yfinance fundamental data per stock asset (weekly refresh)."""

    __tablename__ = "stock_fundamentals"
    __table_args__ = (
        UniqueConstraint("asset_id", name="uq_stock_fundamentals_asset"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    asset_id: Mapped[int] = mapped_column(Integer, ForeignKey("assets.id"), nullable=False)
    trailing_pe: Mapped[float | None] = mapped_column(Float, nullable=True)
    forward_pe: Mapped[float | None] = mapped_column(Float, nullable=True)
    price_to_book: Mapped[float | None] = mapped_column(Float, nullable=True)
    return_on_equity: Mapped[float | None] = mapped_column(Float, nullable=True)
    revenue_growth: Mapped[float | None] = mapped_column(Float, nullable=True)
    dividend_yield: Mapped[float | None] = mapped_column(Float, nullable=True)
    debt_to_equity: Mapped[float | None] = mapped_column(Float, nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


# Seed data for the assets table
SEED_ASSETS: list[dict[str, str | None]] = [
    # IDX stocks
    {
        "symbol": "BBCA",
        "name": "Bank Central Asia",
        "asset_type": "stock",
        "exchange": "IDX",
        "yfinance_symbol": "BBCA.JK",
    },
    {
        "symbol": "BBRI",
        "name": "Bank Rakyat Indonesia",
        "asset_type": "stock",
        "exchange": "IDX",
        "yfinance_symbol": "BBRI.JK",
    },
    {
        "symbol": "TLKM",
        "name": "Telkom Indonesia",
        "asset_type": "stock",
        "exchange": "IDX",
        "yfinance_symbol": "TLKM.JK",
    },
    # Crypto
    {
        "symbol": "BTC",
        "name": "Bitcoin",
        "asset_type": "crypto",
        "exchange": "binance",
        "ccxt_symbol": "BTC/USDT",
    },
    {
        "symbol": "ETH",
        "name": "Ethereum",
        "asset_type": "crypto",
        "exchange": "binance",
        "ccxt_symbol": "ETH/USDT",
    },
    {
        "symbol": "SOL",
        "name": "Solana",
        "asset_type": "crypto",
        "exchange": "binance",
        "ccxt_symbol": "SOL/USDT",
    },
]
