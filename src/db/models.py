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
