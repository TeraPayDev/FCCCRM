from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session, selectinload

from app.core.config import get_settings
from app.models.identity import Role, User
from app.security.passwords import verify_password
from app.security.tokens import TokenClaims, TokenError, create_token, decode_token


class AuthenticationError(ValueError):
    pass


class AccountDisabledError(AuthenticationError):
    pass


class AccountLockedError(AuthenticationError):
    pass


def _user_query() -> Select[tuple[User]]:
    return select(User).options(
        selectinload(User.roles).selectinload(Role.permissions),
    )


def get_user_with_permissions(session: Session, user_id: uuid.UUID) -> User | None:
    return session.scalar(_user_query().where(User.id == user_id))


def get_user_by_login(session: Session, login: str) -> User | None:
    normalized = login.strip().lower()
    return session.scalar(
        _user_query().where(
            (func.lower(User.username) == normalized) | (func.lower(User.email) == normalized)
        )
    )


def permission_codes(user: User) -> set[str]:
    return {permission.code for role in user.roles for permission in role.permissions}


def authenticate_user(session: Session, login: str, password: str) -> User:
    settings = get_settings()
    user = get_user_by_login(session, login)

    if user is None or user.password_hash is None:
        raise AuthenticationError("Invalid credentials.")

    now = datetime.now(UTC)
    if not user.is_active:
        raise AccountDisabledError("Account is disabled.")
    if user.locked_until is not None and user.locked_until > now:
        raise AccountLockedError("Account is temporarily locked.")

    if not verify_password(password, user.password_hash):
        user.failed_login_attempts += 1
        if user.failed_login_attempts >= settings.auth_failed_login_limit:
            user.locked_until = now + timedelta(minutes=settings.auth_lock_minutes)
            user.failed_login_attempts = 0
        session.commit()
        raise AuthenticationError("Invalid credentials.")

    user.failed_login_attempts = 0
    user.locked_until = None
    session.commit()
    return user


def issue_token_pair(user: User) -> tuple[str, str, int]:
    settings = get_settings()
    access_minutes = settings.auth_access_token_minutes
    access_token = create_token(
        subject=user.id,
        token_type="access",
        token_version=user.token_version,
        lifetime=timedelta(minutes=access_minutes),
    )
    refresh_token = create_token(
        subject=user.id,
        token_type="refresh",
        token_version=user.token_version,
        lifetime=timedelta(minutes=settings.auth_refresh_token_minutes),
    )
    return access_token, refresh_token, access_minutes * 60


def user_from_claims(session: Session, claims: TokenClaims) -> User:
    user = get_user_with_permissions(session, claims.subject)
    if user is None or not user.is_active:
        raise AuthenticationError("User is unavailable.")
    if user.token_version != claims.token_version:
        raise TokenError("Token has been revoked.")
    now = datetime.now(UTC)
    if user.locked_until is not None and user.locked_until > now:
        raise AccountLockedError("Account is temporarily locked.")
    return user


def refresh_user(session: Session, refresh_token: str) -> User:
    claims = decode_token(refresh_token, expected_type="refresh")
    return user_from_claims(session, claims)


def revoke_user_tokens(session: Session, user: User) -> None:
    user.token_version += 1
    session.commit()
