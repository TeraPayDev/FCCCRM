"""Add server timestamp defaults to engineering tables.

Revision ID: 20260811_0007
Revises: 20260811_0006
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260811_0007"
down_revision: str | None = "20260811_0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


TABLES = (
    "processing_schedules",
    "integration_connectors",
    "integration_runs",
)


def upgrade() -> None:
    for table in TABLES:
        op.alter_column(
            table,
            "created_at",
            schema="cram",
            existing_type=sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        )
        op.alter_column(
            table,
            "updated_at",
            schema="cram",
            existing_type=sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        )


def downgrade() -> None:
    for table in reversed(TABLES):
        op.alter_column(
            table,
            "updated_at",
            schema="cram",
            existing_type=sa.DateTime(timezone=True),
            nullable=False,
            server_default=None,
        )
        op.alter_column(
            table,
            "created_at",
            schema="cram",
            existing_type=sa.DateTime(timezone=True),
            nullable=False,
            server_default=None,
        )
