"""Price history hypertables with compression and retention policies.

Revision ID: 002
Revises: 001
Create Date: 2026-03-23

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "002"
down_revision: str | None = "001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # --- price_history (daily OHLCV candles) ---
    op.create_table(
        "price_history",
        sa.Column("time", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "asset_id",
            sa.Integer,
            sa.ForeignKey("assets.id"),
            nullable=False,
        ),
        sa.Column("open", sa.Float, nullable=False),
        sa.Column("high", sa.Float, nullable=False),
        sa.Column("low", sa.Float, nullable=False),
        sa.Column("close", sa.Float, nullable=False),
        sa.Column("volume", sa.Float, nullable=False),
        sa.Column(
            "source", sa.String(20), nullable=False, server_default="unknown"
        ),
        sa.UniqueConstraint("asset_id", "time", name="uq_price_history_asset_time"),
    )

    # Convert to TimescaleDB hypertable
    op.execute("SELECT create_hypertable('price_history', 'time')")

    # Enable compression: segment by asset, order by time descending
    op.execute(
        """
        ALTER TABLE price_history SET (
            timescaledb.compress,
            timescaledb.compress_segmentby = 'asset_id',
            timescaledb.compress_orderby = 'time DESC'
        )
        """
    )

    # Auto-compress chunks older than 30 days
    op.execute(
        "SELECT add_compression_policy('price_history', INTERVAL '30 days')"
    )

    # --- price_history_hourly (crypto hourly candles, 7-day rolling) ---
    op.create_table(
        "price_history_hourly",
        sa.Column("time", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "asset_id",
            sa.Integer,
            sa.ForeignKey("assets.id"),
            nullable=False,
        ),
        sa.Column("open", sa.Float, nullable=False),
        sa.Column("high", sa.Float, nullable=False),
        sa.Column("low", sa.Float, nullable=False),
        sa.Column("close", sa.Float, nullable=False),
        sa.Column("volume", sa.Float, nullable=False),
        sa.Column(
            "source", sa.String(20), nullable=False, server_default="unknown"
        ),
        sa.UniqueConstraint(
            "asset_id", "time", name="uq_price_history_hourly_asset_time"
        ),
    )

    # Convert to TimescaleDB hypertable
    op.execute("SELECT create_hypertable('price_history_hourly', 'time')")

    # Auto-drop hourly chunks older than 7 days
    op.execute(
        "SELECT add_retention_policy('price_history_hourly', INTERVAL '7 days')"
    )

    # --- backoff_state (adaptive retry persistence) ---
    op.create_table(
        "backoff_state",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("source", sa.String(30), unique=True, nullable=False),
        sa.Column(
            "consecutive_failures", sa.Integer, nullable=False, server_default="0"
        ),
        sa.Column(
            "last_failure_at", sa.DateTime(timezone=True), nullable=True
        ),
        sa.Column(
            "last_success_at", sa.DateTime(timezone=True), nullable=True
        ),
        sa.Column(
            "current_delay_seconds",
            sa.Float,
            nullable=False,
            server_default="1.0",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_backoff_state"),
    )


def downgrade() -> None:
    op.drop_table("backoff_state")
    op.drop_table("price_history_hourly")
    op.drop_table("price_history")
