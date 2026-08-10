from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status

from app.db.session import get_db_session
from app.models.identity import User
from app.schemas.auth import (
    CurrentUserResponse,
    LoginRequest,
    PermissionListResponse,
    RefreshRequest,
    TokenPair,
)
from app.security.dependencies import current_user, require_permission
from app.security.tokens import TokenError
from app.services.auth import (
    AccountDisabledError,
    AccountLockedError,
    AuthenticationError,
    authenticate_user,
    issue_token_pair,
    permission_codes,
    refresh_user,
    revoke_user_tokens,
)

router = APIRouter(prefix="/auth", tags=["authentication"])

CurrentUser = Annotated[User, Depends(current_user)]
UserReader = Annotated[
    User,
    Depends(require_permission("users.read")),
]


def _user_response(user: User) -> CurrentUserResponse:
    return CurrentUserResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        organisation_id=user.organisation_id,
        roles=sorted(role.code for role in user.roles),
        permissions=sorted(permission_codes(user)),
    )


@router.post("/login", response_model=TokenPair)
def login(payload: LoginRequest) -> TokenPair:
    session = get_db_session()

    try:
        user = authenticate_user(
            session,
            payload.username,
            payload.password,
        )

        access_token, refresh_token, expires_in = issue_token_pair(user)

        return TokenPair(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=expires_in,
        )

    except AccountDisabledError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc

    except AccountLockedError as exc:
        raise HTTPException(
            status_code=status.HTTP_423_LOCKED,
            detail=str(exc),
        ) from exc

    except AuthenticationError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials.",
        ) from exc

    finally:
        session.close()


@router.post("/refresh", response_model=TokenPair)
def refresh(payload: RefreshRequest) -> TokenPair:
    session = get_db_session()

    try:
        user = refresh_user(
            session,
            payload.refresh_token,
        )

        access_token, refresh_token, expires_in = issue_token_pair(user)

        return TokenPair(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=expires_in,
        )

    except (TokenError, AuthenticationError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token.",
        ) from exc

    finally:
        session.close()


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
)
def logout(user: CurrentUser) -> Response:
    session = get_db_session()

    try:
        managed_user = session.get(
            User,
            user.id,
        )

        if managed_user is not None:
            revoke_user_tokens(
                session,
                managed_user,
            )

    finally:
        session.close()

    return Response(
        status_code=status.HTTP_204_NO_CONTENT,
    )


@router.get(
    "/me",
    response_model=CurrentUserResponse,
)
def me(user: CurrentUser) -> CurrentUserResponse:
    return _user_response(user)


@router.get(
    "/permissions",
    response_model=PermissionListResponse,
)
def list_permissions(
    user: UserReader,
) -> PermissionListResponse:
    return PermissionListResponse(
        permissions=sorted(
            permission_codes(user),
        )
    )
