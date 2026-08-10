"""Add identity authentication and account-state fields.

Revision ID: 20260810_0002
Revises: 20260810_0001
Create Date: 2026-08-10
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260810_0002"
down_revision: str | None = "20260810_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "cram"


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("password_hash", sa.String(length=500), nullable=True),
        schema=SCHEMA,
    )
    op.add_column(
        "users",
        sa.Column(
            "failed_login_attempts",
            sa.Integer(),
            server_default=sa.text("0"),
            nullable=False,
        ),
        schema=SCHEMA,
    )
    op.add_column(
        "users",
        sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True),
        schema=SCHEMA,
    )
    op.add_column(
        "users",
        sa.Column(
            "token_version",
            sa.Integer(),
            server_default=sa.text("0"),
            nullable=False,
        ),
        schema=SCHEMA,
    )
    op.create_index("ix_users_is_active", "users", ["is_active"], schema=SCHEMA)


def downgrade() -> None:
    op.drop_index("ix_users_is_active", table_name="users", schema=SCHEMA)
    op.drop_column("users", "token_version", schema=SCHEMA)
    op.drop_column("users", "locked_until", schema=SCHEMA)
    op.drop_column("users", "failed_login_attempts", schema=SCHEMA)
    op.drop_column("users", "password_hash", schema=SCHEMA)
