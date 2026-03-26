"""Ownership snapshots and due diligence reports tables.

Revision ID: 013
Revises: 012
Create Date: 2026-03-26

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers, used by Alembic.
revision: str = "013"
down_revision: str | None = "012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "ownership_snapshots",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("asset_id", sa.Integer, sa.ForeignKey("assets.id"), nullable=False),
        sa.Column("snapshot_date", sa.Date, nullable=False),
        sa.Column("shareholders", JSONB, nullable=False),
        sa.Column("total_shares", sa.Float, nullable=True),
        sa.Column("public_float_pct", sa.Float, nullable=True),
        sa.Column(
            "fetched_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_ownership_snapshots"),
        sa.UniqueConstraint("asset_id", "snapshot_date", name="uq_ownership_asset_date"),
    )

    op.create_table(
        "due_diligence_reports",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("asset_id", sa.Integer, sa.ForeignKey("assets.id"), nullable=False),
        sa.Column("report_date", sa.Date, nullable=False),
        sa.Column("sector", sa.String(50), nullable=True),
        sa.Column("sector_rank", JSONB, nullable=True),
        sa.Column("management_quality", JSONB, nullable=True),
        sa.Column("ownership_changes", JSONB, nullable=True),
        sa.Column("competitive_position", JSONB, nullable=True),
        sa.Column("dd_flags", JSONB, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_due_diligence_reports"),
        sa.UniqueConstraint("asset_id", "report_date", name="uq_dd_asset_date"),
    )


def downgrade() -> None:
    op.drop_table("due_diligence_reports")
    op.drop_table("ownership_snapshots")
