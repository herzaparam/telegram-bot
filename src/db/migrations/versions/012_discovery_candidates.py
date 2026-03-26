"""Discovery candidates table for asset scanning results.

Revision ID: 012
Revises: 011
Create Date: 2026-03-26

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers, used by Alembic.
revision: str = "012"
down_revision: str | None = "011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "discovery_candidates",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("scan_date", sa.Date, nullable=False),
        sa.Column("symbol", sa.String(20), nullable=False),
        sa.Column("name", sa.String(100), nullable=True),
        sa.Column("asset_type", sa.String(10), nullable=False),
        sa.Column("composite_score", sa.Float, nullable=False),
        sa.Column("triggers", JSONB, nullable=False),
        sa.Column("current_price", sa.Float, nullable=True),
        sa.Column("price_change_pct", sa.Float, nullable=True),
        sa.Column("volume_ratio", sa.Float, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_discovery_candidates"),
        sa.UniqueConstraint("scan_date", "symbol", name="uq_discovery_date_symbol"),
    )
    op.create_index("ix_discovery_scan_date", "discovery_candidates", ["scan_date"])


def downgrade() -> None:
    op.drop_index("ix_discovery_scan_date", table_name="discovery_candidates")
    op.drop_table("discovery_candidates")
