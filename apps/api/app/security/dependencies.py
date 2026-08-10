from __future__ import annotations

from collections.abc import Callable
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.db.session import get_db_session
from app.models.identity import User
from app.security.tokens import TokenError, decode_token
from app.services.auth import AuthenticationError, permission_codes, user_from_claims

bearer_scheme = HTTPBearer(auto_error=False)

BearerCredentials = Annotated[
    HTTPAuthorizationCredentials | None,
    Depends(bearer_scheme),
]


def _unauthorized(detail: str = "Invalid or expired credentials.") -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def current_user(
    credentials: BearerCredentials,
) -> User:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise _unauthorized()

    session = get_db_session()
    try:
        claims = decode_token(
            credentials.credentials,
            expected_type="access",
        )
        return user_from_claims(session, claims)
    except (TokenError, AuthenticationError) as exc:
        raise _unauthorized() from exc
    finally:
        session.close()


CurrentUser = Annotated[User, Depends(current_user)]


def require_permission(permission_code: str) -> Callable[[CurrentUser], User]:
    def dependency(user: CurrentUser) -> User:
        if permission_code not in permission_codes(user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permission denied.",
            )

        return user

    return dependency
