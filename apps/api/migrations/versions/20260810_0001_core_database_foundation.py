"""Create CRAM core database foundation.

Revision ID: 20260810_0001
Revises:
Create Date: 2026-08-10

Milestone 4 scope only:
- organisations, users, roles, permissions, user_roles, role_permissions
- datasets, dataset_sources, dataset_versions, dataset_fields, dataset_uploads
- audit_logs
- geographic_areas, spatial_layers
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from geoalchemy2 import Geometry
from sqlalchemy.dialects import postgresql

revision: str = "20260810_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "cram"


def upgrade() -> None:
    op.execute(sa.text(f"CREATE SCHEMA IF NOT EXISTS {SCHEMA}"))
    op.execute(sa.text("CREATE EXTENSION IF NOT EXISTS postgis WITH SCHEMA public"))
    op.execute(sa.text("CREATE EXTENSION IF NOT EXISTS pgcrypto WITH SCHEMA public"))

    op.create_table(
        "organisations",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_organisations"),
        sa.UniqueConstraint("code", name="uq_organisations_code"),
        schema=SCHEMA,
    )
    op.create_index("ix_organisations_name", "organisations", ["name"], schema=SCHEMA)

    op.create_table(
        "users",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("organisation_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("username", sa.String(length=120), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["organisation_id"],
            [f"{SCHEMA}.organisations.id"],
            name="fk_users_organisation_id_organisations",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_users"),
        sa.UniqueConstraint("username", name="uq_users_username"),
        sa.UniqueConstraint("email", name="uq_users_email"),
        schema=SCHEMA,
    )
    op.create_index("ix_users_organisation_id", "users", ["organisation_id"], schema=SCHEMA)

    op.create_table(
        "roles",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("code", sa.String(length=100), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("description", sa.String(length=500), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_roles"),
        sa.UniqueConstraint("code", name="uq_roles_code"),
        schema=SCHEMA,
    )

    op.create_table(
        "permissions",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("code", sa.String(length=160), nullable=False),
        sa.Column("description", sa.String(length=500), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_permissions"),
        sa.UniqueConstraint("code", name="uq_permissions_code"),
        schema=SCHEMA,
    )

    op.create_table(
        "user_roles",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("role_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            [f"{SCHEMA}.users.id"],
            name="fk_user_roles_user_id_users",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["role_id"],
            [f"{SCHEMA}.roles.id"],
            name="fk_user_roles_role_id_roles",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("user_id", "role_id", name="pk_user_roles"),
        schema=SCHEMA,
    )
    op.create_index("ix_user_roles_role_id", "user_roles", ["role_id"], schema=SCHEMA)

    op.create_table(
        "role_permissions",
        sa.Column("role_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("permission_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["role_id"],
            [f"{SCHEMA}.roles.id"],
            name="fk_role_permissions_role_id_roles",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["permission_id"],
            [f"{SCHEMA}.permissions.id"],
            name="fk_role_permissions_permission_id_permissions",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("role_id", "permission_id", name="pk_role_permissions"),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_role_permissions_permission_id",
        "role_permissions",
        ["permission_id"],
        schema=SCHEMA,
    )

    op.create_table(
        "datasets",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("code", sa.String(length=120), nullable=False),
        sa.Column("name", sa.String(length=240), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("owner_organisation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["owner_organisation_id"],
            [f"{SCHEMA}.organisations.id"],
            name="fk_datasets_owner_organisation_id_organisations",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_datasets"),
        sa.UniqueConstraint("code", name="uq_datasets_code"),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_datasets_owner_organisation_id",
        "datasets",
        ["owner_organisation_id"],
        schema=SCHEMA,
    )
    op.create_index("ix_datasets_name", "datasets", ["name"], schema=SCHEMA)

    op.create_table(
        "dataset_sources",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("dataset_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("provider_organisation_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("name", sa.String(length=240), nullable=False),
        sa.Column("source_type", sa.String(length=50), nullable=False),
        sa.Column("source_reference", sa.String(length=500), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["dataset_id"],
            [f"{SCHEMA}.datasets.id"],
            name="fk_dataset_sources_dataset_id_datasets",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["provider_organisation_id"],
            [f"{SCHEMA}.organisations.id"],
            name="fk_dataset_sources_provider_organisation_id_organisations",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_dataset_sources"),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_dataset_sources_dataset_id",
        "dataset_sources",
        ["dataset_id"],
        schema=SCHEMA,
    )
    op.create_index(
        "ix_dataset_sources_provider_organisation_id",
        "dataset_sources",
        ["provider_organisation_id"],
        schema=SCHEMA,
    )

    op.create_table(
        "dataset_versions",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("dataset_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("checksum_sha256", sa.String(length=64), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "version_number > 0",
            name="ck_dataset_versions_version_number_positive",
        ),
        sa.ForeignKeyConstraint(
            ["dataset_id"],
            [f"{SCHEMA}.datasets.id"],
            name="fk_dataset_versions_dataset_id_datasets",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["source_id"],
            [f"{SCHEMA}.dataset_sources.id"],
            name="fk_dataset_versions_source_id_dataset_sources",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_dataset_versions"),
        sa.UniqueConstraint(
            "dataset_id",
            "version_number",
            name="uq_dataset_versions_dataset_id_version_number",
        ),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_dataset_versions_dataset_id",
        "dataset_versions",
        ["dataset_id"],
        schema=SCHEMA,
    )
    op.create_index(
        "ix_dataset_versions_source_id",
        "dataset_versions",
        ["source_id"],
        schema=SCHEMA,
    )

    op.create_table(
        "dataset_fields",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("dataset_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("data_type", sa.String(length=80), nullable=False),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("is_required", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "ordinal >= 0",
            name="ck_dataset_fields_ordinal_non_negative",
        ),
        sa.ForeignKeyConstraint(
            ["dataset_id"],
            [f"{SCHEMA}.datasets.id"],
            name="fk_dataset_fields_dataset_id_datasets",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_dataset_fields"),
        sa.UniqueConstraint(
            "dataset_id",
            "name",
            name="uq_dataset_fields_dataset_id_name",
        ),
        sa.UniqueConstraint(
            "dataset_id",
            "ordinal",
            name="uq_dataset_fields_dataset_id_ordinal",
        ),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_dataset_fields_dataset_id",
        "dataset_fields",
        ["dataset_id"],
        schema=SCHEMA,
    )

    op.create_table(
        "dataset_uploads",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("dataset_version_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("uploaded_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("object_key", sa.String(length=700), nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("mime_type", sa.String(length=160), nullable=True),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("checksum_sha256", sa.String(length=64), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "size_bytes >= 0",
            name="ck_dataset_uploads_size_bytes_non_negative",
        ),
        sa.ForeignKeyConstraint(
            ["dataset_version_id"],
            [f"{SCHEMA}.dataset_versions.id"],
            name="fk_dataset_uploads_dataset_version_id_dataset_versions",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["uploaded_by_user_id"],
            [f"{SCHEMA}.users.id"],
            name="fk_dataset_uploads_uploaded_by_user_id_users",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_dataset_uploads"),
        sa.UniqueConstraint("object_key", name="uq_dataset_uploads_object_key"),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_dataset_uploads_dataset_version_id",
        "dataset_uploads",
        ["dataset_version_id"],
        schema=SCHEMA,
    )
    op.create_index(
        "ix_dataset_uploads_uploaded_by_user_id",
        "dataset_uploads",
        ["uploaded_by_user_id"],
        schema=SCHEMA,
    )

    op.create_table(
        "audit_logs",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("actor_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("organisation_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("action", sa.String(length=160), nullable=False),
        sa.Column("resource_type", sa.String(length=160), nullable=False),
        sa.Column("resource_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "details",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "occurred_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["actor_user_id"],
            [f"{SCHEMA}.users.id"],
            name="fk_audit_logs_actor_user_id_users",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["organisation_id"],
            [f"{SCHEMA}.organisations.id"],
            name="fk_audit_logs_organisation_id_organisations",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_audit_logs"),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_audit_logs_actor_user_id",
        "audit_logs",
        ["actor_user_id"],
        schema=SCHEMA,
    )
    op.create_index(
        "ix_audit_logs_organisation_id",
        "audit_logs",
        ["organisation_id"],
        schema=SCHEMA,
    )
    op.create_index(
        "ix_audit_logs_resource",
        "audit_logs",
        ["resource_type", "resource_id"],
        schema=SCHEMA,
    )
    op.create_index(
        "ix_audit_logs_occurred_at",
        "audit_logs",
        ["occurred_at"],
        schema=SCHEMA,
    )

    op.create_table(
        "geographic_areas",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("parent_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("code", sa.String(length=120), nullable=False),
        sa.Column("name", sa.String(length=240), nullable=False),
        sa.Column("area_type", sa.String(length=100), nullable=False),
        sa.Column(
            "geometry",
            Geometry("MULTIPOLYGON", srid=4326, spatial_index=False),
            nullable=True,
        ),
        sa.Column(
            "centroid",
            Geometry("POINT", srid=4326, spatial_index=False),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["parent_id"],
            [f"{SCHEMA}.geographic_areas.id"],
            name="fk_geographic_areas_parent_id_geographic_areas",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_geographic_areas"),
        sa.UniqueConstraint("code", name="uq_geographic_areas_code"),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_geographic_areas_parent_id",
        "geographic_areas",
        ["parent_id"],
        schema=SCHEMA,
    )
    op.create_index(
        "ix_geographic_areas_area_type",
        "geographic_areas",
        ["area_type"],
        schema=SCHEMA,
    )
    op.create_index(
        "ix_geographic_areas_geometry_gist",
        "geographic_areas",
        ["geometry"],
        schema=SCHEMA,
        postgresql_using="gist",
    )

    op.create_table(
        "spatial_layers",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("dataset_version_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("name", sa.String(length=240), nullable=False),
        sa.Column("workspace", sa.String(length=160), nullable=True),
        sa.Column("store_name", sa.String(length=160), nullable=True),
        sa.Column("layer_name", sa.String(length=240), nullable=True),
        sa.Column("geometry_type", sa.String(length=80), nullable=True),
        sa.Column("srid", sa.Integer(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["dataset_version_id"],
            [f"{SCHEMA}.dataset_versions.id"],
            name="fk_spatial_layers_dataset_version_id_dataset_versions",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_spatial_layers"),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_spatial_layers_dataset_version_id",
        "spatial_layers",
        ["dataset_version_id"],
        schema=SCHEMA,
    )
    op.create_index("ix_spatial_layers_name", "spatial_layers", ["name"], schema=SCHEMA)


def downgrade() -> None:
    op.drop_index("ix_spatial_layers_name", table_name="spatial_layers", schema=SCHEMA)
    op.drop_index(
        "ix_spatial_layers_dataset_version_id",
        table_name="spatial_layers",
        schema=SCHEMA,
    )
    op.drop_table("spatial_layers", schema=SCHEMA)

    op.drop_index(
        "ix_geographic_areas_geometry_gist",
        table_name="geographic_areas",
        schema=SCHEMA,
    )
    op.drop_index(
        "ix_geographic_areas_area_type",
        table_name="geographic_areas",
        schema=SCHEMA,
    )
    op.drop_index(
        "ix_geographic_areas_parent_id",
        table_name="geographic_areas",
        schema=SCHEMA,
    )
    op.drop_table("geographic_areas", schema=SCHEMA)

    op.drop_index(
        "ix_audit_logs_occurred_at",
        table_name="audit_logs",
        schema=SCHEMA,
    )
    op.drop_index("ix_audit_logs_resource", table_name="audit_logs", schema=SCHEMA)
    op.drop_index(
        "ix_audit_logs_organisation_id",
        table_name="audit_logs",
        schema=SCHEMA,
    )
    op.drop_index(
        "ix_audit_logs_actor_user_id",
        table_name="audit_logs",
        schema=SCHEMA,
    )
    op.drop_table("audit_logs", schema=SCHEMA)

    op.drop_index(
        "ix_dataset_uploads_uploaded_by_user_id",
        table_name="dataset_uploads",
        schema=SCHEMA,
    )
    op.drop_index(
        "ix_dataset_uploads_dataset_version_id",
        table_name="dataset_uploads",
        schema=SCHEMA,
    )
    op.drop_table("dataset_uploads", schema=SCHEMA)

    op.drop_index(
        "ix_dataset_fields_dataset_id",
        table_name="dataset_fields",
        schema=SCHEMA,
    )
    op.drop_table("dataset_fields", schema=SCHEMA)

    op.drop_index(
        "ix_dataset_versions_source_id",
        table_name="dataset_versions",
        schema=SCHEMA,
    )
    op.drop_index(
        "ix_dataset_versions_dataset_id",
        table_name="dataset_versions",
        schema=SCHEMA,
    )
    op.drop_table("dataset_versions", schema=SCHEMA)

    op.drop_index(
        "ix_dataset_sources_provider_organisation_id",
        table_name="dataset_sources",
        schema=SCHEMA,
    )
    op.drop_index(
        "ix_dataset_sources_dataset_id",
        table_name="dataset_sources",
        schema=SCHEMA,
    )
    op.drop_table("dataset_sources", schema=SCHEMA)

    op.drop_index("ix_datasets_name", table_name="datasets", schema=SCHEMA)
    op.drop_index(
        "ix_datasets_owner_organisation_id",
        table_name="datasets",
        schema=SCHEMA,
    )
    op.drop_table("datasets", schema=SCHEMA)

    op.drop_index(
        "ix_role_permissions_permission_id",
        table_name="role_permissions",
        schema=SCHEMA,
    )
    op.drop_table("role_permissions", schema=SCHEMA)

    op.drop_index(
        "ix_user_roles_role_id",
        table_name="user_roles",
        schema=SCHEMA,
    )
    op.drop_table("user_roles", schema=SCHEMA)

    op.drop_table("permissions", schema=SCHEMA)
    op.drop_table("roles", schema=SCHEMA)

    op.drop_index("ix_users_organisation_id", table_name="users", schema=SCHEMA)
    op.drop_table("users", schema=SCHEMA)

    op.drop_index(
        "ix_organisations_name",
        table_name="organisations",
        schema=SCHEMA,
    )
    op.drop_table("organisations", schema=SCHEMA)

    op.execute(sa.text("ALTER EXTENSION pgcrypto SET SCHEMA public"))
    op.execute(sa.text("ALTER EXTENSION postgis SET SCHEMA public"))
    op.execute(sa.text(f"DROP SCHEMA IF EXISTS {SCHEMA}"))
