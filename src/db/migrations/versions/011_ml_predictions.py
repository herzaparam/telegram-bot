"""ML predictions cache table for XGBoost/LSTM ensemble results.

Revision ID: 011
Revises: 010
Create Date: 2026-03-25

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "011"
down_revision: str | None = "010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "ml_predictions",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("asset_id", sa.Integer, sa.ForeignKey("assets.id"), nullable=False),
        sa.Column("date", sa.Date, nullable=False),
        sa.Column("xgboost_pred", sa.Float, nullable=True),
        sa.Column("xgboost_prob", sa.Float, nullable=True),
        sa.Column("lstm_pred", sa.Float, nullable=True),
        sa.Column("lstm_prob", sa.Float, nullable=True),
        sa.Column("ensemble_score", sa.Float, nullable=True),
        sa.Column("features_hash", sa.String(32), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_ml_predictions"),
        sa.UniqueConstraint("asset_id", "date", name="uq_ml_predictions_asset_date"),
    )


def downgrade() -> None:
    op.drop_table("ml_predictions")
