from __future__ import annotations

import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.db.session import get_db_session
from app.models.identity import User
from app.schemas.audit import AuditEventResponse
from app.security.dependencies import require_permission
from app.services.audit import list_audit_events

router = APIRouter(prefix="/audit", tags=["audit"])
AuditReader = Annotated[User, Depends(require_permission("audit.read"))]


@router.get("", response_model=list[AuditEventResponse])
def audit_list(
    _: AuditReader,
    actor_user_id: uuid.UUID | None = None,
    organisation_id: uuid.UUID | None = None,
    action: str | None = None,
    resource_type: str | None = None,
    resource_id: uuid.UUID | None = None,
    occurred_from: datetime | None = None,
    occurred_to: datetime | None = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
) -> list[AuditEventResponse]:
    session = get_db_session()
    try:
        events = list_audit_events(
            session,
            actor_user_id=actor_user_id,
            organisation_id=organisation_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            occurred_from=occurred_from,
            occurred_to=occurred_to,
            limit=limit,
        )
        return [AuditEventResponse.model_validate(event, from_attributes=True) for event in events]
    finally:
        session.close()
