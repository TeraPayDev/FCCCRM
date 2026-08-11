"""Engineering extension: schedules and integration adapters.

Revision ID: 20260811_0006
Revises: 20260811_0005
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260811_0006"
down_revision: str | None = "20260811_0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "processing_schedules",
        sa.Column("code", sa.String(160), nullable=False),
        sa.Column("job_type", sa.String(120), nullable=False),
        sa.Column("dataset_version_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("interval_minutes", sa.Integer(), nullable=False),
        sa.Column(
            "parameters", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False
        ),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("next_run_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_status", sa.String(30), nullable=True),
        sa.Column("consecutive_failures", sa.Integer(), server_default="0", nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["dataset_version_id"], ["cram.dataset_versions.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
        schema="cram",
    )
    op.create_index(
        "ix_processing_schedules_next_run",
        "processing_schedules",
        ["is_active", "next_run_at"],
        schema="cram",
    )
    op.create_table(
        "integration_connectors",
        sa.Column("code", sa.String(160), nullable=False),
        sa.Column("institution", sa.String(200), nullable=False),
        sa.Column("connector_type", sa.String(60), nullable=False),
        sa.Column("base_url", sa.String(700), nullable=True),
        sa.Column(
            "configuration",
            postgresql.JSONB(),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("sandbox_mode", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
        sa.UniqueConstraint("institution", "code", name="uq_connector_institution_code"),
        schema="cram",
    )
    op.create_table(
        "integration_runs",
        sa.Column("connector_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("records_received", sa.Integer(), server_default="0", nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "metadata", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False
        ),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["connector_id"], ["cram.integration_connectors.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        schema="cram",
    )
    op.create_index(
        "ix_integration_runs_connector_started",
        "integration_runs",
        ["connector_id", "started_at"],
        schema="cram",
    )


def downgrade() -> None:
    op.drop_index(
        "ix_integration_runs_connector_started", table_name="integration_runs", schema="cram"
    )
    op.drop_table("integration_runs", schema="cram")
    op.drop_table("integration_connectors", schema="cram")
    op.drop_index(
        "ix_processing_schedules_next_run", table_name="processing_schedules", schema="cram"
    )
    op.drop_table("processing_schedules", schema="cram")
