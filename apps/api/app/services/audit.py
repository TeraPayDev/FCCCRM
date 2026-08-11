from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from app.models.audit import AuditLog
from app.models.identity import User

SENSITIVE_KEYS = {
    "password",
    "password_hash",
    "secret",
    "token",
    "access_token",
    "refresh_token",
    "authorization",
    "api_key",
}


def _sanitize(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            str(k): "[REDACTED]" if str(k).lower() in SENSITIVE_KEYS else _sanitize(v)
            for k, v in value.items()
        }
    if isinstance(value, list):
        return [_sanitize(item) for item in value]
    if isinstance(value, tuple):
        return [_sanitize(item) for item in value]
    return value


def record_audit_event(
    session: Session,
    *,
    action: str,
    resource_type: str,
    actor: User | None = None,
    resource_id: uuid.UUID | None = None,
    organisation_id: uuid.UUID | None = None,
    details: dict[str, object] | None = None,
) -> AuditLog:
    event = AuditLog(
        actor_user_id=actor.id if actor else None,
        organisation_id=organisation_id
        if organisation_id is not None
        else (actor.organisation_id if actor else None),
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        details=_sanitize(details or {}),
    )
    session.add(event)
    session.flush()
    return event


def audit_query(
    *,
    actor_user_id: uuid.UUID | None = None,
    organisation_id: uuid.UUID | None = None,
    action: str | None = None,
    resource_type: str | None = None,
    resource_id: uuid.UUID | None = None,
    occurred_from: datetime | None = None,
    occurred_to: datetime | None = None,
) -> Select[tuple[AuditLog]]:
    query = select(AuditLog)
    if actor_user_id is not None:
        query = query.where(AuditLog.actor_user_id == actor_user_id)
    if organisation_id is not None:
        query = query.where(AuditLog.organisation_id == organisation_id)
    if action:
        query = query.where(AuditLog.action == action)
    if resource_type:
        query = query.where(AuditLog.resource_type == resource_type)
    if resource_id is not None:
        query = query.where(AuditLog.resource_id == resource_id)
    if occurred_from is not None:
        query = query.where(AuditLog.occurred_at >= occurred_from)
    if occurred_to is not None:
        query = query.where(AuditLog.occurred_at <= occurred_to)
    return query.order_by(AuditLog.occurred_at.desc())


def list_audit_events(
    session: Session,
    *,
    actor_user_id: uuid.UUID | None = None,
    organisation_id: uuid.UUID | None = None,
    action: str | None = None,
    resource_type: str | None = None,
    resource_id: uuid.UUID | None = None,
    occurred_from: datetime | None = None,
    occurred_to: datetime | None = None,
    limit: int = 100,
) -> list[AuditLog]:
    query = audit_query(
        actor_user_id=actor_user_id,
        organisation_id=organisation_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        occurred_from=occurred_from,
        occurred_to=occurred_to,
    )
    return list(session.scalars(query.limit(limit)).all())
