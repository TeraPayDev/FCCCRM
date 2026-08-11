from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class ProcessingJob(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "processing_jobs"
    job_type: Mapped[str] = mapped_column(String(120), nullable=False)
    dataset_version_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("cram.dataset_versions.id", ondelete="SET NULL"),
        nullable=True,
    )
    status: Mapped[str] = mapped_column(
        String(30), nullable=False, default="PENDING", server_default="PENDING"
    )
    stage: Mapped[str] = mapped_column(
        String(40), nullable=False, default="RAW", server_default="RAW"
    )
    parameters: Mapped[dict[str, object]] = mapped_column(
        JSONB, nullable=False, default=dict, server_default="{}"
    )
    idempotency_key: Mapped[str] = mapped_column(String(220), nullable=False)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    max_attempts: Mapped[int] = mapped_column(
        Integer, nullable=False, default=3, server_default="3"
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    output_reference: Mapped[str | None] = mapped_column(String(700), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    __table_args__ = (
        UniqueConstraint("idempotency_key", name="uq_processing_jobs_idempotency_key"),
        CheckConstraint(
            "status IN ('PENDING','RUNNING','SUCCEEDED','FAILED','CANCELLED')",
            name="processing_job_status_valid",
        ),
        CheckConstraint(
            "stage IN ('RAW','VALIDATED','NORMALIZED','DOMAIN_TRANSFORM','PUBLISHED_OUTPUT')",
            name="processing_job_stage_valid",
        ),
        Index("ix_processing_jobs_dataset_version_id", "dataset_version_id"),
        Index("ix_processing_jobs_status", "status"),
        Index("ix_processing_jobs_job_type", "job_type"),
    )


class ProcessingJobLog(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "processing_job_logs"
    processing_job_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("cram.processing_jobs.id", ondelete="CASCADE"),
        nullable=False,
    )
    level: Mapped[str] = mapped_column(String(20), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    details: Mapped[dict[str, object]] = mapped_column(
        JSONB, nullable=False, default=dict, server_default="{}"
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    __table_args__ = (Index("ix_processing_job_logs_processing_job_id", "processing_job_id"),)
