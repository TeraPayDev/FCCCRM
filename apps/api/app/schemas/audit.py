from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel


class AuditEventResponse(BaseModel):
    id: uuid.UUID
    actor_user_id: uuid.UUID | None
    organisation_id: uuid.UUID | None
    action: str
    resource_type: str
    resource_id: uuid.UUID | None
    details: dict[str, object]
    occurred_at: datetime
