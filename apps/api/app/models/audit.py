from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UUIDPrimaryKeyMixin


class AuditLog(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "audit_logs"
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("cram.users.id", ondelete="RESTRICT"), nullable=True
    )
    organisation_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("cram.organisations.id", ondelete="RESTRICT"),
        nullable=True,
    )
    action: Mapped[str] = mapped_column(String(160), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(160), nullable=False)
    resource_id: Mapped[uuid.UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True)
    details: Mapped[dict[str, object]] = mapped_column(
        JSONB, nullable=False, default=dict, server_default="{}"
    )
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    __table_args__ = (
        Index("ix_audit_logs_actor_user_id", "actor_user_id"),
        Index("ix_audit_logs_organisation_id", "organisation_id"),
        Index("ix_audit_logs_resource", "resource_type", "resource_id"),
        Index("ix_audit_logs_occurred_at", "occurred_at"),
    )
