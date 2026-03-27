"""Portfolio risk snapshots and backtest results tables.

Revision ID: 014
Revises: 013
Create Date: 2026-03-27

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers, used by Alembic.
revision: str = "014"
down_revision: str | None = "013"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "portfolio_risk_snapshots",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("snapshot_date", sa.Date, nullable=False),
        sa.Column("concentration", JSONB, nullable=False),
        sa.Column("correlation_alerts", JSONB, nullable=False),
        sa.Column("var_summary", JSONB, nullable=False),
        sa.Column("sharpe_ratio", sa.Float, nullable=True),
        sa.Column("sortino_ratio", sa.Float, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_portfolio_risk_snapshots"),
        sa.UniqueConstraint("snapshot_date", name="uq_risk_snapshot_date"),
    )

    op.create_table(
        "backtest_results",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("asset_id", sa.Integer, sa.ForeignKey("assets.id"), nullable=False),
        sa.Column("period", sa.String(5), nullable=False),
        sa.Column("run_date", sa.Date, nullable=False),
        sa.Column("win_rate", sa.Float, nullable=False),
        sa.Column("total_return", sa.Float, nullable=False),
        sa.Column("buy_hold_return", sa.Float, nullable=False),
        sa.Column("max_drawdown", sa.Float, nullable=False),
        sa.Column("sharpe_ratio", sa.Float, nullable=True),
        sa.Column("daily_results", JSONB, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_backtest_results"),
        sa.UniqueConstraint("asset_id", "period", "run_date", name="uq_backtest_asset_period_date"),
    )


def downgrade() -> None:
    op.drop_table("backtest_results")
    op.drop_table("portfolio_risk_snapshots")
