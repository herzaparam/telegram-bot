"""Evaluation tables: evaluations, accuracy_stats, idx_holidays.

Revision ID: 005
Revises: 004
Create Date: 2026-03-24

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers, used by Alembic.
revision: str = "005"
down_revision: str | None = "004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# IDX 2026 holiday calendar (static seed data)
IDX_HOLIDAYS_2026 = [
    ("2026-01-01", "New Year's Day"),
    ("2026-01-29", "Chinese New Year"),
    ("2026-02-17", "Isra Mi'raj"),
    ("2026-03-20", "Nyepi"),
    ("2026-03-29", "Eid al-Fitr"),
    ("2026-03-30", "Eid al-Fitr"),
    ("2026-03-31", "Eid al-Fitr"),
    ("2026-04-01", "Eid al-Fitr"),
    ("2026-04-02", "Eid al-Fitr"),
    ("2026-04-03", "Good Friday"),
    ("2026-05-01", "Labour Day"),
    ("2026-05-14", "Ascension of Christ"),
    ("2026-05-26", "Waisak"),
    ("2026-06-01", "Pancasila Day"),
    ("2026-06-05", "Eid al-Adha"),
    ("2026-06-26", "Islamic New Year"),
    ("2026-08-17", "Independence Day"),
    ("2026-09-05", "Prophet Muhammad's Birthday"),
    ("2026-12-25", "Christmas Day"),
]


def upgrade() -> None:
    # --- evaluations table ---
    op.create_table(
        "evaluations",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "decision_id",
            sa.Integer,
            sa.ForeignKey("daily_decisions.id"),
            nullable=False,
        ),
        sa.Column("window", sa.String(5), nullable=False),
        sa.Column("eval_price", sa.Numeric(20, 8), nullable=False),
        sa.Column("eval_price_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("change_pct", sa.Numeric(8, 4), nullable=False),
        sa.Column("was_correct", sa.Boolean, nullable=False),
        sa.Column("engine_results", JSONB, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_evaluations"),
        sa.UniqueConstraint("decision_id", "window", name="uq_evaluations_decision_window"),
    )
    op.create_index("ix_evaluations_decision_id", "evaluations", ["decision_id"])
    op.create_index(
        "ix_evaluations_created_at", "evaluations", [sa.text("created_at DESC")]
    )

    # --- accuracy_stats table ---
    op.create_table(
        "accuracy_stats",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "asset_id", sa.Integer, sa.ForeignKey("assets.id"), nullable=True
        ),
        sa.Column("engine_name", sa.String(30), nullable=True),
        sa.Column("window", sa.String(5), nullable=False),
        sa.Column("period", sa.String(10), nullable=False),
        sa.Column("total", sa.Integer, nullable=False, server_default="0"),
        sa.Column("correct", sa.Integer, nullable=False, server_default="0"),
        sa.Column("win_rate", sa.Numeric(5, 2), nullable=True),
        sa.Column(
            "computed_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_accuracy_stats"),
        sa.UniqueConstraint(
            "asset_id", "engine_name", "window", "period",
            name="uq_accuracy_stats_lookup",
        ),
    )
    op.create_index(
        "ix_accuracy_stats_lookup",
        "accuracy_stats",
        ["asset_id", "window", "period"],
    )

    # --- idx_holidays table ---
    op.create_table(
        "idx_holidays",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("holiday_date", sa.Date, unique=True, nullable=False),
        sa.Column("name", sa.String(100), nullable=True),
        sa.Column("year", sa.Integer, nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_idx_holidays"),
    )
    op.create_index("ix_idx_holidays_date", "idx_holidays", ["holiday_date"])

    # Seed IDX 2026 holidays
    for dt_str, name in IDX_HOLIDAYS_2026:
        year = int(dt_str[:4])
        op.execute(
            f"INSERT INTO idx_holidays (holiday_date, name, year) "
            f"VALUES ('{dt_str}', '{name}', {year})"
        )


def downgrade() -> None:
    op.drop_table("idx_holidays")
    op.drop_table("accuracy_stats")
    op.drop_table("evaluations")
