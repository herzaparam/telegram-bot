"""Financial documents and parsed financial data tables.

Revision ID: 008
Revises: 007
Create Date: 2026-03-25

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "008"
down_revision: str | None = "007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "financial_docs",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("asset_id", sa.Integer, sa.ForeignKey("assets.id"), nullable=False),
        sa.Column("doc_type", sa.String(20), nullable=False),
        sa.Column("period", sa.String(10), nullable=False),
        sa.Column("file_path", sa.Text, nullable=True),
        sa.Column("source_url", sa.Text, nullable=True),
        sa.Column("parse_status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column(
            "downloaded_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("parsed_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_financial_docs"),
        sa.UniqueConstraint("asset_id", "doc_type", "period", name="uq_financial_docs_asset_period"),
    )
    op.create_index("ix_financial_docs_asset_id", "financial_docs", ["asset_id"])

    op.create_table(
        "financial_data",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("doc_id", sa.Integer, sa.ForeignKey("financial_docs.id"), nullable=False),
        sa.Column("asset_id", sa.Integer, sa.ForeignKey("assets.id"), nullable=False),
        sa.Column("metric_name", sa.String(50), nullable=False),
        sa.Column("metric_value", sa.Float, nullable=True),
        sa.Column("metric_text", sa.Text, nullable=True),
        sa.Column("period", sa.String(10), nullable=False),
        sa.Column("period_date", sa.Date, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_financial_data"),
        sa.UniqueConstraint("doc_id", "metric_name", name="uq_financial_data_doc_metric"),
    )
    op.create_index("ix_financial_data_asset_id", "financial_data", ["asset_id"])


def downgrade() -> None:
    op.drop_index("ix_financial_data_asset_id", table_name="financial_data")
    op.drop_table("financial_data")
    op.drop_index("ix_financial_docs_asset_id", table_name="financial_docs")
    op.drop_table("financial_docs")
