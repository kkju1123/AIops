"""add guest accounts and drill requester

Revision ID: 202611100001
Revises: 202611070001
Create Date: 2026-11-10 10:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision = "202611100001"
down_revision: str | None = "202611070001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("users") as batch:
        batch.add_column(
            sa.Column(
                "account_kind",
                sa.String(length=16),
                nullable=False,
                server_default="member",
            )
        )
    op.create_index("ix_users_account_kind_created", "users", ["account_kind", "created_at"])
    with op.batch_alter_table("live_demo_runs") as batch:
        batch.add_column(sa.Column("requester_user_id", sa.String(length=80), nullable=True))
    op.create_index(
        "ix_live_demo_runs_requester_created",
        "live_demo_runs",
        ["requester_user_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_live_demo_runs_requester_created", table_name="live_demo_runs")
    with op.batch_alter_table("live_demo_runs") as batch:
        batch.drop_column("requester_user_id")
    op.drop_index("ix_users_account_kind_created", table_name="users")
    with op.batch_alter_table("users") as batch:
        batch.drop_column("account_kind")
