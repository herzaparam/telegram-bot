"""Watchlist and bot_settings tables for Telegram bot.

Revision ID: 004
Revises: 003
Create Date: 2026-03-24

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "004"
down_revision: str | None = "003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "watchlist",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "asset_id",
            sa.Integer,
            sa.ForeignKey("assets.id"),
            unique=True,
            nullable=False,
        ),
        sa.Column("added_by_chat_id", sa.String(30), nullable=True),
        sa.Column(
            "added_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_watchlist"),
    )

    op.create_table(
        "bot_settings",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("key", sa.String(50), unique=True, nullable=False),
        sa.Column("value", sa.String(200), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_bot_settings"),
    )

    # Insert default delivery time setting
    op.execute(
        "INSERT INTO bot_settings (key, value) VALUES ('delivery_time', '06:30')"
    )


def downgrade() -> None:
    op.drop_table("bot_settings")
    op.drop_table("watchlist")
