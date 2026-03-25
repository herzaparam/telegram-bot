"""News events, macro data, and stock fundamentals tables.

Revision ID: 007
Revises: 006
Create Date: 2026-03-25

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers, used by Alembic.
revision: str = "007"
down_revision: str | None = "006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "news_events",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("headline", sa.Text, nullable=False),
        sa.Column("source", sa.String(50), nullable=False),
        sa.Column("url", sa.Text, nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("impact_score", sa.Float, nullable=True),
        sa.Column("affected_assets", JSONB, nullable=True),
        sa.Column("category", sa.String(30), nullable=True),
        sa.Column("raw_summary", sa.Text, nullable=True),
        sa.Column(
            "fetched_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_news_events"),
        sa.UniqueConstraint("url", name="uq_news_events_url"),
    )
    op.create_index("ix_news_events_fetched_at", "news_events", ["fetched_at"])

    op.create_table(
        "macro_data",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("series_id", sa.String(30), nullable=False),
        sa.Column("observation_date", sa.Date, nullable=False),
        sa.Column("value", sa.Float, nullable=False),
        sa.Column(
            "fetched_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_macro_data"),
        sa.UniqueConstraint("series_id", "observation_date", name="uq_macro_data_series_date"),
    )
    op.create_index("ix_macro_data_series_id", "macro_data", ["series_id"])

    op.create_table(
        "stock_fundamentals",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("asset_id", sa.Integer, sa.ForeignKey("assets.id"), nullable=False),
        sa.Column("trailing_pe", sa.Float, nullable=True),
        sa.Column("forward_pe", sa.Float, nullable=True),
        sa.Column("price_to_book", sa.Float, nullable=True),
        sa.Column("return_on_equity", sa.Float, nullable=True),
        sa.Column("revenue_growth", sa.Float, nullable=True),
        sa.Column("dividend_yield", sa.Float, nullable=True),
        sa.Column("debt_to_equity", sa.Float, nullable=True),
        sa.Column(
            "fetched_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_stock_fundamentals"),
        sa.UniqueConstraint("asset_id", name="uq_stock_fundamentals_asset"),
    )


def downgrade() -> None:
    op.drop_table("stock_fundamentals")
    op.drop_index("ix_macro_data_series_id", table_name="macro_data")
    op.drop_table("macro_data")
    op.drop_index("ix_news_events_fetched_at", table_name="news_events")
    op.drop_table("news_events")
