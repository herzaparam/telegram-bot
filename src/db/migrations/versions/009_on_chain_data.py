"""On-chain data table for crypto metrics (TVL, exchange flows).

Revision ID: 009
Revises: 008
Create Date: 2026-03-25

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "009"
down_revision: str | None = "008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "on_chain_data",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("asset_id", sa.Integer, sa.ForeignKey("assets.id"), nullable=False),
        sa.Column("date", sa.Date, nullable=False),
        sa.Column("metric", sa.String(30), nullable=False),
        sa.Column("value", sa.Float, nullable=False),
        sa.Column("source", sa.String(20), nullable=False),
        sa.Column(
            "fetched_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_on_chain_data"),
        sa.UniqueConstraint("asset_id", "date", "metric", name="uq_onchain_asset_date_metric"),
    )
    op.create_index("ix_onchain_asset_date", "on_chain_data", ["asset_id", "date"])


def downgrade() -> None:
    op.drop_index("ix_onchain_asset_date", table_name="on_chain_data")
    op.drop_table("on_chain_data")
