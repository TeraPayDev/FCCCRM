from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.db.session import get_db_session
from app.models.identity import User
from app.schemas.users import RoleResponse, UserAdminResponse, UserCreate, UserUpdate
from app.security.dependencies import require_permission
from app.services.audit import record_audit_event
from app.services.users import (
    RoleNotFoundError,
    UserConflictError,
    UserNotFoundError,
    create_user,
    list_roles,
    list_users,
    update_user,
)

router = APIRouter(prefix="/users", tags=["users"])
UserReader = Annotated[User, Depends(require_permission("users.read"))]
UserManager = Annotated[User, Depends(require_permission("users.manage"))]


def _response(user: User) -> UserAdminResponse:
    return UserAdminResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        is_active=user.is_active,
        organisation_id=user.organisation_id,
        organisation_code=user.organisation.code if user.organisation else None,
        organisation_name=user.organisation.name if user.organisation else None,
        roles=sorted(role.code for role in user.roles),
        created_at=user.created_at.isoformat(),
        updated_at=user.updated_at.isoformat(),
        locked_until=user.locked_until.isoformat() if user.locked_until else None,
    )


@router.get("", response_model=list[UserAdminResponse])
def users_list(_: UserReader) -> list[UserAdminResponse]:
    session = get_db_session()
    try:
        return [_response(user) for user in list_users(session)]
    finally:
        session.close()


@router.get("/roles", response_model=list[RoleResponse])
def roles_list(_: UserReader) -> list[RoleResponse]:
    session = get_db_session()
    try:
        return [
            RoleResponse.model_validate(role, from_attributes=True) for role in list_roles(session)
        ]
    finally:
        session.close()


@router.get("/{user_id}", response_model=UserAdminResponse)
def user_detail(user_id: uuid.UUID, _: UserReader) -> UserAdminResponse:
    session = get_db_session()
    try:
        user = next((item for item in list_users(session) if item.id == user_id), None)
        if user is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
        return _response(user)
    finally:
        session.close()


@router.post("", response_model=UserAdminResponse, status_code=status.HTTP_201_CREATED)
def users_create(payload: UserCreate, actor: UserManager) -> UserAdminResponse:
    session = get_db_session()
    try:
        try:
            user = create_user(
                session,
                username=payload.username,
                email=str(payload.email),
                password=payload.password,
                organisation_id=payload.organisation_id,
                role_codes=payload.role_codes,
            )
        except (UserConflictError, UserNotFoundError, RoleNotFoundError, ValueError) as exc:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
        record_audit_event(
            session,
            action="user.create",
            resource_type="user",
            actor=actor,
            resource_id=user.id,
            organisation_id=user.organisation_id,
            details={"roles": sorted(role.code for role in user.roles)},
        )
        session.commit()
        return _response(user)
    finally:
        session.close()


@router.patch("/{user_id}", response_model=UserAdminResponse)
def users_update(user_id: uuid.UUID, payload: UserUpdate, actor: UserManager) -> UserAdminResponse:
    if actor.id == user_id and payload.is_active is False:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You cannot deactivate your own account.",
        )
    session = get_db_session()
    try:
        try:
            user = update_user(
                session,
                user_id,
                email=str(payload.email) if payload.email is not None else None,
                organisation_id=payload.organisation_id,
                organisation_id_provided="organisation_id" in payload.model_fields_set,
                role_codes=payload.role_codes,
                is_active=payload.is_active,
                password=payload.password,
            )
        except (UserConflictError, UserNotFoundError, RoleNotFoundError, ValueError) as exc:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
        record_audit_event(
            session,
            action="user.update",
            resource_type="user",
            actor=actor,
            resource_id=user.id,
            organisation_id=user.organisation_id,
            details={
                "roles": sorted(role.code for role in user.roles),
                "is_active": user.is_active,
            },
        )
        session.commit()
        return _response(user)
    finally:
        session.close()
