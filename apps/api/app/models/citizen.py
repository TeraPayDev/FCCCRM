from __future__ import annotations

import uuid
from datetime import datetime

from geoalchemy2 import Geometry
from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class CitizenReport(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "citizen_reports"
    public_reference: Mapped[str] = mapped_column(String(40), nullable=False, unique=True)
    hazard_type: Mapped[str] = mapped_column(String(80), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    occurred_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    location: Mapped[object | None] = mapped_column(
        Geometry("POINT", srid=4326, spatial_index=False), nullable=True
    )
    status: Mapped[str] = mapped_column(
        String(40), nullable=False, default="SUBMITTED", server_default="SUBMITTED"
    )
    reporter_name: Mapped[str | None] = mapped_column(String(160), nullable=True)
    reporter_contact: Mapped[str | None] = mapped_column(String(240), nullable=True)
    consent_to_contact: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    is_public: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    moderation_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    __table_args__ = (
        Index("ix_citizen_reports_status", "status"),
        Index("ix_citizen_reports_location_gist", "location", postgresql_using="gist"),
    )


class CitizenReportAttachment(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "citizen_report_attachments"
    citizen_report_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("cram.citizen_reports.id", ondelete="CASCADE"),
        nullable=False,
    )
    object_key: Mapped[str] = mapped_column(String(700), nullable=False, unique=True)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(120), nullable=False)
    size_bytes: Mapped[int] = mapped_column(nullable=False)
    checksum_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    scan_status: Mapped[str] = mapped_column(
        String(30), nullable=False, default="ACCEPTED", server_default="ACCEPTED"
    )


class IncidentAssignment(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "incident_assignments"
    citizen_report_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("cram.citizen_reports.id", ondelete="CASCADE"),
        nullable=False,
    )
    organisation_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("cram.organisations.id", ondelete="RESTRICT"),
        nullable=False,
    )
    assigned_user_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("cram.users.id", ondelete="SET NULL"), nullable=True
    )
    assigned_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("cram.users.id", ondelete="SET NULL"), nullable=True
    )
    status: Mapped[str] = mapped_column(
        String(40), nullable=False, default="ASSIGNED", server_default="ASSIGNED"
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    assignment_metadata: Mapped[dict[str, object]] = mapped_column(
        "metadata", JSONB, nullable=False, default=dict, server_default="{}"
    )
