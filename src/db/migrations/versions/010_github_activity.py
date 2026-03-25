"""GitHub activity table for crypto project repo metrics.

Revision ID: 010
Revises: 009
Create Date: 2026-03-25

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "010"
down_revision: str | None = "009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "github_activity",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("asset_id", sa.Integer, sa.ForeignKey("assets.id"), nullable=False),
        sa.Column("date", sa.Date, nullable=False),
        sa.Column("repo", sa.String(100), nullable=False),
        sa.Column("stars", sa.Integer, server_default="0"),
        sa.Column("forks", sa.Integer, server_default="0"),
        sa.Column("weekly_commits", sa.Integer, server_default="0"),
        sa.Column("contributors", sa.Integer, server_default="0"),
        sa.Column(
            "fetched_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_github_activity"),
        sa.UniqueConstraint("asset_id", "date", name="uq_github_activity_asset_date"),
    )


def downgrade() -> None:
    op.drop_table("github_activity")
