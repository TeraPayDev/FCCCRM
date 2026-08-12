from __future__ import annotations

import uuid

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session, selectinload

from app.models.identity import Organisation, Role, User
from app.security.passwords import hash_password


class UserConflictError(ValueError):
    pass


class UserNotFoundError(ValueError):
    pass


class RoleNotFoundError(ValueError):
    pass


def _query() -> Select[tuple[User]]:
    return select(User).options(selectinload(User.roles), selectinload(User.organisation))


def list_users(session: Session) -> list[User]:
    return list(session.scalars(_query().order_by(User.username)).all())


def list_roles(session: Session) -> list[Role]:
    return list(session.scalars(select(Role).order_by(Role.name)).all())


def _roles(session: Session, codes: list[str]) -> list[Role]:
    normalized = sorted(set(code.strip() for code in codes if code.strip()))
    if not normalized:
        return []
    roles = list(session.scalars(select(Role).where(Role.code.in_(normalized))).all())
    found = {role.code for role in roles}
    missing = [code for code in normalized if code not in found]
    if missing:
        raise RoleNotFoundError(f"Unknown role(s): {', '.join(missing)}")
    return roles


def _ensure_unique(
    session: Session,
    username: str,
    email: str,
    exclude_id: uuid.UUID | None = None,
) -> None:
    query = select(User.id).where(
        (func.lower(User.username) == username.lower()) | (func.lower(User.email) == email.lower())
    )
    if exclude_id is not None:
        query = query.where(User.id != exclude_id)
    if session.scalar(query) is not None:
        raise UserConflictError("Username or email already exists.")


def create_user(
    session: Session,
    *,
    username: str,
    email: str,
    password: str,
    organisation_id: uuid.UUID | None,
    role_codes: list[str],
) -> User:
    username = username.strip()
    email = email.strip().lower()
    _ensure_unique(session, username, email)
    if organisation_id is not None and session.get(Organisation, organisation_id) is None:
        raise UserNotFoundError("Organisation does not exist.")
    user = User(
        username=username,
        email=email,
        password_hash=hash_password(password),
        organisation_id=organisation_id,
        is_active=True,
    )
    user.roles = _roles(session, role_codes)
    session.add(user)
    session.flush()
    session.refresh(user)
    return user


def update_user(
    session: Session,
    user_id: uuid.UUID,
    *,
    email: str | None,
    organisation_id: uuid.UUID | None,
    organisation_id_provided: bool,
    role_codes: list[str] | None,
    is_active: bool | None,
    password: str | None,
) -> User:
    user = session.scalar(_query().where(User.id == user_id))
    if user is None:
        raise UserNotFoundError("User not found.")
    next_email = email.strip().lower() if email is not None else user.email
    _ensure_unique(session, user.username, next_email, exclude_id=user.id)
    if (
        organisation_id_provided
        and organisation_id is not None
        and session.get(Organisation, organisation_id) is None
    ):
        raise UserNotFoundError("Organisation does not exist.")
    if email is not None:
        user.email = next_email
    if organisation_id_provided:
        user.organisation_id = organisation_id
    if role_codes is not None:
        user.roles = _roles(session, role_codes)
    if is_active is not None:
        user.is_active = is_active
        user.token_version += 1
    if password is not None:
        user.password_hash = hash_password(password)
        user.token_version += 1
    session.flush()
    return user
