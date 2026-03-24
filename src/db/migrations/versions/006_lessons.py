"""Lessons table for self-evaluation feedback loop.

Revision ID: 006
Revises: 005
Create Date: 2026-03-24

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers, used by Alembic.
revision: str = "006"
down_revision: str | None = "005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "lessons",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("date", sa.Date, nullable=False),
        sa.Column("asset_type", sa.String(10), nullable=True),
        sa.Column("engine_tags", JSONB, nullable=True),
        sa.Column("topic", sa.String(30), nullable=True),
        sa.Column("lesson", sa.Text, nullable=False),
        sa.Column(
            "source_decision_id",
            sa.Integer,
            sa.ForeignKey("daily_decisions.id"),
            nullable=True,
        ),
        sa.Column("times_observed", sa.Integer, nullable=False, server_default="1"),
        sa.Column("times_applied", sa.Integer, nullable=False, server_default="0"),
        sa.Column("times_correct", sa.Integer, nullable=False, server_default="0"),
        sa.Column(
            "confidence_tier", sa.String(15), nullable=False, server_default="hypothesis"
        ),
        sa.Column("still_valid", sa.Boolean, nullable=False, server_default="true"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_lessons"),
    )
    op.create_index(
        "ix_lessons_valid_type", "lessons", ["still_valid", "asset_type"]
    )
    op.create_index(
        "ix_lessons_tier",
        "lessons",
        ["confidence_tier"],
        postgresql_where=sa.text("still_valid = TRUE"),
    )


def downgrade() -> None:
    op.drop_table("lessons")
