"""add live incident drill runs

Revision ID: 202611070001
Revises: 202607110007
Create Date: 2026-11-07 17:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision = "202611070001"
down_revision: str | None = "202607110007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "live_demo_runs",
        sa.Column("id", sa.String(length=80), primary_key=True),
        sa.Column("owner_user_id", sa.String(length=80), nullable=False),
        sa.Column("diagnostic_task_id", sa.String(length=80), nullable=False),
        sa.Column("scenario_id", sa.String(length=120), nullable=False),
        sa.Column("visitor_key_hash", sa.String(length=64), nullable=False),
        sa.Column("access_token_hash", sa.String(length=64), nullable=False),
        sa.Column("alert_published", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("diagnostic_task_id", name="uq_live_demo_runs_diagnostic_task_id"),
        sa.UniqueConstraint("access_token_hash", name="uq_live_demo_runs_access_token_hash"),
    )
    op.create_index("ix_live_demo_runs_owner_user_id", "live_demo_runs", ["owner_user_id"])
    op.create_index("ix_live_demo_runs_created_at", "live_demo_runs", ["created_at"])
    op.create_index(
        "ix_live_demo_runs_visitor_created",
        "live_demo_runs",
        ["visitor_key_hash", "created_at"],
    )


def downgrade() -> None:
    op.drop_table("live_demo_runs")
