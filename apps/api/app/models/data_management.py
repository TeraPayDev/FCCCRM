from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

DATASET_STATUSES = (
    "DRAFT",
    "ACTIVE",
    "ARCHIVED",
)

VERSION_STATUSES = (
    "DRAFT",
    "UPLOADED",
    "VALIDATING",
    "VALIDATION_FAILED",
    "VALIDATED",
    "PENDING_APPROVAL",
    "APPROVED",
    "PUBLISHED",
    "REJECTED",
    "SUPERSEDED",
    "ARCHIVED",
)


class Dataset(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "datasets"

    code: Mapped[str] = mapped_column(String(120), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(240), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    owner_organisation_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("cram.organisations.id", ondelete="RESTRICT"),
        nullable=False,
    )
    category: Mapped[str | None] = mapped_column(String(120), nullable=True)
    sensitivity: Mapped[str] = mapped_column(
        String(40), nullable=False, default="INTERNAL", server_default="INTERNAL"
    )
    expected_format: Mapped[str] = mapped_column(
        String(40), nullable=False, default="CSV", server_default="CSV"
    )
    update_frequency: Mapped[str | None] = mapped_column(String(120), nullable=True)
    status: Mapped[str] = mapped_column(
        String(40), nullable=False, default="DRAFT", server_default="DRAFT"
    )

    __table_args__ = (
        CheckConstraint(
            "status IN ('DRAFT','ACTIVE','ARCHIVED')",
            name="dataset_status_valid",
        ),
        Index("ix_datasets_owner_organisation_id", "owner_organisation_id"),
        Index("ix_datasets_name", "name"),
        Index("ix_datasets_category", "category"),
        Index("ix_datasets_status", "status"),
    )


class DatasetSource(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "dataset_sources"

    dataset_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("cram.datasets.id", ondelete="CASCADE"),
        nullable=False,
    )
    provider_organisation_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("cram.organisations.id", ondelete="SET NULL"),
        nullable=True,
    )
    name: Mapped[str] = mapped_column(String(240), nullable=False)
    source_type: Mapped[str] = mapped_column(String(50), nullable=False)
    source_reference: Mapped[str | None] = mapped_column(String(500), nullable=True)
    connection_secret_ref: Mapped[str | None] = mapped_column(String(300), nullable=True)
    update_method: Mapped[str | None] = mapped_column(String(120), nullable=True)

    __table_args__ = (
        Index("ix_dataset_sources_dataset_id", "dataset_id"),
        Index("ix_dataset_sources_provider_organisation_id", "provider_organisation_id"),
    )


class DatasetVersion(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "dataset_versions"

    dataset_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("cram.datasets.id", ondelete="CASCADE"),
        nullable=False,
    )
    source_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("cram.dataset_sources.id", ondelete="SET NULL"),
        nullable=True,
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(
        String(40), nullable=False, default="DRAFT", server_default="DRAFT"
    )
    checksum_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    row_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        UniqueConstraint(
            "dataset_id",
            "version_number",
            name="uq_dataset_versions_dataset_id_version_number",
        ),
        CheckConstraint("version_number > 0", name="version_number_positive"),
        CheckConstraint(
            "status IN ('DRAFT','UPLOADED','VALIDATING','VALIDATION_FAILED','VALIDATED',"
            "'PENDING_APPROVAL','APPROVED','PUBLISHED','REJECTED','SUPERSEDED','ARCHIVED')",
            name="dataset_version_status_valid",
        ),
        Index("ix_dataset_versions_dataset_id", "dataset_id"),
        Index("ix_dataset_versions_source_id", "source_id"),
        Index("ix_dataset_versions_status", "status"),
    )


class DatasetField(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "dataset_fields"

    dataset_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("cram.datasets.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    data_type: Mapped[str] = mapped_column(String(80), nullable=False)
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False)
    is_required: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    validation_rules: Mapped[dict[str, object]] = mapped_column(
        JSONB, nullable=False, default=dict, server_default="{}"
    )

    __table_args__ = (
        UniqueConstraint("dataset_id", "name", name="uq_dataset_fields_dataset_id_name"),
        UniqueConstraint("dataset_id", "ordinal", name="uq_dataset_fields_dataset_id_ordinal"),
        CheckConstraint("ordinal >= 0", name="ordinal_non_negative"),
        Index("ix_dataset_fields_dataset_id", "dataset_id"),
    )


class DatasetUpload(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "dataset_uploads"

    dataset_version_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("cram.dataset_versions.id", ondelete="CASCADE"),
        nullable=False,
    )
    uploaded_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("cram.users.id", ondelete="SET NULL"),
        nullable=True,
    )
    object_key: Mapped[str] = mapped_column(String(700), nullable=False, unique=True)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    mime_type: Mapped[str | None] = mapped_column(String(160), nullable=True)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    checksum_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)

    __table_args__ = (
        CheckConstraint("size_bytes >= 0", name="size_bytes_non_negative"),
        Index("ix_dataset_uploads_dataset_version_id", "dataset_version_id"),
        Index("ix_dataset_uploads_uploaded_by_user_id", "uploaded_by_user_id"),
    )


class DataValidationRun(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "data_validation_runs"

    dataset_version_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("cram.dataset_versions.id", ondelete="CASCADE"),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(40), nullable=False, default="PENDING", server_default="PENDING"
    )
    execution_mode: Mapped[str] = mapped_column(
        String(20), nullable=False, default="SYNC", server_default="SYNC"
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    total_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    error_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    warning_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )

    __table_args__ = (
        CheckConstraint(
            "status IN ('PENDING','RUNNING','PASSED','FAILED')",
            name="validation_run_status_valid",
        ),
        CheckConstraint(
            "execution_mode IN ('SYNC','BACKGROUND')",
            name="validation_execution_mode_valid",
        ),
        Index("ix_data_validation_runs_dataset_version_id", "dataset_version_id"),
        Index("ix_data_validation_runs_status", "status"),
    )


class ValidationError(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "validation_errors"

    validation_run_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("cram.data_validation_runs.id", ondelete="CASCADE"),
        nullable=False,
    )
    row_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    field_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    rule_code: Mapped[str] = mapped_column(String(120), nullable=False)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    value_excerpt: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        CheckConstraint(
            "severity IN ('ERROR','WARNING')",
            name="validation_error_severity_valid",
        ),
        Index("ix_validation_errors_validation_run_id", "validation_run_id"),
        Index("ix_validation_errors_severity", "severity"),
    )


class Approval(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "approvals"

    dataset_version_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("cram.dataset_versions.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    submitted_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("cram.users.id", ondelete="SET NULL"), nullable=True
    )
    reviewed_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("cram.users.id", ondelete="SET NULL"), nullable=True
    )
    status: Mapped[str] = mapped_column(
        String(30), nullable=False, default="PENDING", server_default="PENDING"
    )
    comments: Mapped[str | None] = mapped_column(Text, nullable=True)
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        CheckConstraint(
            "status IN ('PENDING','APPROVED','REJECTED')",
            name="approval_status_valid",
        ),
        Index("ix_approvals_status", "status"),
    )


class DatasetVersionStatusHistory(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "dataset_version_status_history"

    dataset_version_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("cram.dataset_versions.id", ondelete="CASCADE"),
        nullable=False,
    )
    from_status: Mapped[str | None] = mapped_column(String(40), nullable=True)
    to_status: Mapped[str] = mapped_column(String(40), nullable=False)
    changed_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("cram.users.id", ondelete="SET NULL"), nullable=True
    )
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        Index(
            "ix_dataset_version_status_history_dataset_version_id",
            "dataset_version_id",
        ),
        Index("ix_dataset_version_status_history_created_at", "created_at"),
    )
