"""Retire legacy SLMET sandbox integration.

Revision ID: 20260812_0008
Revises: 20260811_0007
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260812_0008"
down_revision: str | None = "20260811_0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        sa.text(
            "UPDATE cram.integration_connectors SET is_active = false WHERE code = 'SLMET-SANDBOX'"
        )
    )
    op.execute(
        sa.text(
            "UPDATE cram.processing_schedules SET is_active = false "
            "WHERE code = 'SLMET-WEATHER-SCHEDULE'"
        )
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            "UPDATE cram.integration_connectors SET is_active = true WHERE code = 'SLMET-SANDBOX'"
        )
    )
    op.execute(
        sa.text(
            "UPDATE cram.processing_schedules SET is_active = true "
            "WHERE code = 'SLMET-WEATHER-SCHEDULE'"
        )
    )
