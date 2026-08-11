from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class ProcessingSchedule(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "processing_schedules"
    code: Mapped[str] = mapped_column(String(160), nullable=False, unique=True)
    job_type: Mapped[str] = mapped_column(String(120), nullable=False)
    dataset_version_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("cram.dataset_versions.id", ondelete="SET NULL"),
        nullable=True,
    )
    interval_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    parameters: Mapped[dict[str, object]] = mapped_column(
        JSONB, nullable=False, default=dict, server_default="{}"
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )
    next_run_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_status: Mapped[str | None] = mapped_column(String(30), nullable=True)
    consecutive_failures: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    __table_args__ = (Index("ix_processing_schedules_next_run", "is_active", "next_run_at"),)


class IntegrationConnector(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "integration_connectors"
    code: Mapped[str] = mapped_column(String(160), nullable=False, unique=True)
    institution: Mapped[str] = mapped_column(String(200), nullable=False)
    connector_type: Mapped[str] = mapped_column(String(60), nullable=False)
    base_url: Mapped[str | None] = mapped_column(String(700), nullable=True)
    configuration: Mapped[dict[str, object]] = mapped_column(
        JSONB, nullable=False, default=dict, server_default="{}"
    )
    sandbox_mode: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )
    __table_args__ = (
        UniqueConstraint("institution", "code", name="uq_connector_institution_code"),
    )


class IntegrationRun(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "integration_runs"
    connector_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("cram.integration_connectors.id", ondelete="CASCADE"),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(String(30), nullable=False)
    records_received: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    run_metadata: Mapped[dict[str, object]] = mapped_column(
        "metadata", JSONB, nullable=False, default=dict, server_default="{}"
    )
    __table_args__ = (Index("ix_integration_runs_connector_started", "connector_id", "started_at"),)
