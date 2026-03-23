"""Initial schema - Phase 1 tables.

Revision ID: 001
Revises:
Create Date: 2026-03-23

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

# revision identifiers, used by Alembic.
revision: str = "001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Enable TimescaleDB extension
    op.execute("CREATE EXTENSION IF NOT EXISTS timescaledb")

    # --- assets ---
    op.create_table(
        "assets",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("symbol", sa.String(20), nullable=False),
        sa.Column("name", sa.String(100), nullable=True),
        sa.Column("asset_type", sa.String(10), nullable=False),
        sa.Column("exchange", sa.String(20), nullable=True),
        sa.Column("yfinance_symbol", sa.String(20), nullable=True),
        sa.Column("ccxt_symbol", sa.String(30), nullable=True),
        sa.Column("is_active", sa.Boolean, default=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("symbol", "asset_type", name="uq_assets_symbol"),
        sa.PrimaryKeyConstraint("id", name="pk_assets"),
    )

    # --- pipeline_runs ---
    op.create_table(
        "pipeline_runs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("run_date", sa.Date, nullable=False),
        sa.Column("stage", sa.String(20), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata", JSONB, nullable=True),
        sa.UniqueConstraint("run_date", "stage", name="uq_pipeline_runs_run_date"),
        sa.PrimaryKeyConstraint("id", name="pk_pipeline_runs"),
    )

    # --- pipeline_asset_runs ---
    op.create_table(
        "pipeline_asset_runs",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("run_id", UUID(as_uuid=True), sa.ForeignKey("pipeline_runs.id"), nullable=False),
        sa.Column("asset_id", sa.Integer, sa.ForeignKey("assets.id"), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("retry_count", sa.Integer, server_default="0"),
        sa.UniqueConstraint("run_id", "asset_id", name="uq_pipeline_asset_runs_run_id"),
        sa.PrimaryKeyConstraint("id", name="pk_pipeline_asset_runs"),
    )

    # --- daily_decisions ---
    op.create_table(
        "daily_decisions",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("asset_id", sa.Integer, sa.ForeignKey("assets.id"), nullable=False),
        sa.Column("date", sa.Date, nullable=False),
        sa.Column("verdict", sa.String(15), nullable=False),
        sa.Column("score", sa.Numeric(4, 3), nullable=True),
        sa.Column("confidence", sa.Numeric(4, 3), nullable=True),
        sa.Column("decision_price", sa.Numeric(20, 8), nullable=True),
        sa.Column("decision_price_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("evaluation_price", sa.Numeric(20, 8), nullable=True),
        sa.Column("evaluation_price_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("all_signals", JSONB, nullable=True),
        sa.Column("reasoning", sa.Text, nullable=True),
        sa.Column("key_factors", JSONB, nullable=True),
        sa.Column("risk_warning", sa.Text, nullable=True),
        sa.Column("wait_for", sa.Text, nullable=True),
        sa.Column("lessons_applied", JSONB, nullable=True),
        sa.Column("model_used", sa.String(50), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("asset_id", "date", name="uq_daily_decisions_asset_id"),
        sa.PrimaryKeyConstraint("id", name="pk_daily_decisions"),
    )

    # --- Indexes ---
    op.create_index("idx_pipeline_runs_date", "pipeline_runs", [sa.text("run_date DESC")])
    op.create_index("idx_decisions_asset_date", "daily_decisions", ["asset_id", sa.text("date DESC")])

    # --- Seed assets ---
    assets_table = sa.table(
        "assets",
        sa.column("symbol", sa.String),
        sa.column("name", sa.String),
        sa.column("asset_type", sa.String),
        sa.column("exchange", sa.String),
        sa.column("yfinance_symbol", sa.String),
        sa.column("ccxt_symbol", sa.String),
    )
    op.bulk_insert(
        assets_table,
        [
            {
                "symbol": "BBCA",
                "name": "Bank Central Asia",
                "asset_type": "stock",
                "exchange": "IDX",
                "yfinance_symbol": "BBCA.JK",
                "ccxt_symbol": None,
            },
            {
                "symbol": "BBRI",
                "name": "Bank Rakyat Indonesia",
                "asset_type": "stock",
                "exchange": "IDX",
                "yfinance_symbol": "BBRI.JK",
                "ccxt_symbol": None,
            },
            {
                "symbol": "TLKM",
                "name": "Telkom Indonesia",
                "asset_type": "stock",
                "exchange": "IDX",
                "yfinance_symbol": "TLKM.JK",
                "ccxt_symbol": None,
            },
            {
                "symbol": "BTC",
                "name": "Bitcoin",
                "asset_type": "crypto",
                "exchange": "binance",
                "yfinance_symbol": None,
                "ccxt_symbol": "BTC/USDT",
            },
            {
                "symbol": "ETH",
                "name": "Ethereum",
                "asset_type": "crypto",
                "exchange": "binance",
                "yfinance_symbol": None,
                "ccxt_symbol": "ETH/USDT",
            },
            {
                "symbol": "SOL",
                "name": "Solana",
                "asset_type": "crypto",
                "exchange": "binance",
                "yfinance_symbol": None,
                "ccxt_symbol": "SOL/USDT",
            },
        ],
    )


def downgrade() -> None:
    op.drop_index("idx_decisions_asset_date", table_name="daily_decisions")
    op.drop_index("idx_pipeline_runs_date", table_name="pipeline_runs")
    op.drop_table("daily_decisions")
    op.drop_table("pipeline_asset_runs")
    op.drop_table("pipeline_runs")
    op.drop_table("assets")
