"""Harden audit immutability and add GIS area metadata.

Revision ID: 20260810_0003
Revises: 20260810_0002
Create Date: 2026-08-10
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260810_0003"
down_revision: str | None = "20260810_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "cram"


def upgrade() -> None:
    op.add_column(
        "geographic_areas",
        sa.Column(
            "area_metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        schema=SCHEMA,
    )

    # Audit records are immutable. Their actor/organisation references therefore
    # must not use ON DELETE SET NULL because that would mutate historical rows.
    op.drop_constraint(
        "fk_audit_logs_actor_user_id_users",
        "audit_logs",
        schema=SCHEMA,
        type_="foreignkey",
    )
    op.create_foreign_key(
        "fk_audit_logs_actor_user_id_users",
        "audit_logs",
        "users",
        ["actor_user_id"],
        ["id"],
        source_schema=SCHEMA,
        referent_schema=SCHEMA,
        ondelete="RESTRICT",
    )

    op.drop_constraint(
        "fk_audit_logs_organisation_id_organisations",
        "audit_logs",
        schema=SCHEMA,
        type_="foreignkey",
    )
    op.create_foreign_key(
        "fk_audit_logs_organisation_id_organisations",
        "audit_logs",
        "organisations",
        ["organisation_id"],
        ["id"],
        source_schema=SCHEMA,
        referent_schema=SCHEMA,
        ondelete="RESTRICT",
    )

    op.execute(
        sa.text(
            """
            CREATE OR REPLACE FUNCTION cram.prevent_audit_log_mutation()
            RETURNS trigger AS $$
            BEGIN
                RAISE EXCEPTION 'audit_logs is append-only';
            END;
            $$ LANGUAGE plpgsql;
            """
        )
    )

    op.execute(sa.text("DROP TRIGGER IF EXISTS audit_logs_append_only ON cram.audit_logs"))

    op.execute(
        sa.text(
            """
            CREATE TRIGGER audit_logs_append_only
            BEFORE UPDATE OR DELETE ON cram.audit_logs
            FOR EACH ROW
            EXECUTE FUNCTION cram.prevent_audit_log_mutation();
            """
        )
    )


def downgrade() -> None:
    op.execute(sa.text("DROP TRIGGER IF EXISTS audit_logs_append_only ON cram.audit_logs"))
    op.execute(sa.text("DROP FUNCTION IF EXISTS cram.prevent_audit_log_mutation()"))

    op.drop_constraint(
        "fk_audit_logs_actor_user_id_users",
        "audit_logs",
        schema=SCHEMA,
        type_="foreignkey",
    )
    op.create_foreign_key(
        "fk_audit_logs_actor_user_id_users",
        "audit_logs",
        "users",
        ["actor_user_id"],
        ["id"],
        source_schema=SCHEMA,
        referent_schema=SCHEMA,
        ondelete="SET NULL",
    )

    op.drop_constraint(
        "fk_audit_logs_organisation_id_organisations",
        "audit_logs",
        schema=SCHEMA,
        type_="foreignkey",
    )
    op.create_foreign_key(
        "fk_audit_logs_organisation_id_organisations",
        "audit_logs",
        "organisations",
        ["organisation_id"],
        ["id"],
        source_schema=SCHEMA,
        referent_schema=SCHEMA,
        ondelete="SET NULL",
    )

    op.drop_column(
        "geographic_areas",
        "area_metadata",
        schema=SCHEMA,
    )
