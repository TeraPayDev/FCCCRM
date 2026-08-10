from __future__ import annotations

import uuid

from app.models.identity import User
from app.services.auth import permission_codes


def organisation_scope_allows(
    user: User,
    *,
    permission_code: str,
    resource_organisation_id: uuid.UUID | None,
    allow_cross_organisation: bool = False,
) -> bool:
    """Evaluate a permission inside an organisation boundary.

    The helper is intentionally independent of role names so future approval and
    ownership workflows can reuse the same permission model. A caller may opt
    into cross-organisation access only when the workflow explicitly allows it.
    """
    if permission_code not in permission_codes(user):
        return False

    if allow_cross_organisation:
        return True

    if user.organisation_id is None or resource_organisation_id is None:
        return False

    return user.organisation_id == resource_organisation_id
