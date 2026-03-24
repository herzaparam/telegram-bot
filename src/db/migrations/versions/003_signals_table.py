"""Signals table for engine-generated trading signals.

Revision ID: 003
Revises: 002
Create Date: 2026-03-24

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "003"
down_revision: str | None = "002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "signals",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "asset_id",
            sa.Integer,
            sa.ForeignKey("assets.id"),
            nullable=False,
        ),
        sa.Column("date", sa.Date, nullable=False),
        sa.Column("category", sa.String(30), nullable=False),
        sa.Column("score", sa.Float, nullable=False),
        sa.Column("confidence", sa.Float, nullable=False),
        sa.Column("reasoning", sa.Text, nullable=False),
        sa.Column("indicators", sa.dialects.postgresql.JSONB, nullable=True),
        sa.Column("data_quality", sa.dialects.postgresql.JSONB, nullable=True),
        sa.Column("price_at_signal", sa.Float, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "asset_id", "date", "category", name="uq_signals_asset_date_category"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_signals"),
    )

    # Index for common query pattern: signals by asset and date
    op.create_index("ix_signals_asset_id_date", "signals", ["asset_id", "date"])


def downgrade() -> None:
    op.drop_index("ix_signals_asset_id_date", table_name="signals")
    op.drop_table("signals")
