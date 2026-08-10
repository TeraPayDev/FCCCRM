from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status

from app.db.session import get_db_session
from app.models.identity import Organisation, User
from app.schemas.organisations import (
    OrganisationCreate,
    OrganisationResponse,
    OrganisationUpdate,
    UserOrganisationResponse,
    UserOrganisationUpdate,
)
from app.security.dependencies import require_permission
from app.services.organisations import (
    InactiveOrganisationError,
    OrganisationConflictError,
    OrganisationNotFoundError,
    assign_user_organisation,
    create_organisation,
    delete_organisation,
    get_organisation,
    list_organisations,
    list_users_with_organisations,
    update_organisation,
)

router = APIRouter(prefix="/organisations", tags=["organisations"])

OrganisationReader = Annotated[User, Depends(require_permission("users.read"))]
OrganisationManager = Annotated[User, Depends(require_permission("users.manage"))]


def _organisation_response(organisation: Organisation) -> OrganisationResponse:
    return OrganisationResponse.model_validate(organisation, from_attributes=True)


def _user_response(user: User) -> UserOrganisationResponse:
    return UserOrganisationResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        is_active=user.is_active,
        organisation_id=user.organisation_id,
        organisation_code=user.organisation.code if user.organisation else None,
        organisation_name=user.organisation.name if user.organisation else None,
    )


@router.get("", response_model=list[OrganisationResponse])
def organisations_list(_: OrganisationReader) -> list[OrganisationResponse]:
    session = get_db_session()
    try:
        return [_organisation_response(item) for item in list_organisations(session)]
    finally:
        session.close()


@router.post("", response_model=OrganisationResponse, status_code=status.HTTP_201_CREATED)
def organisations_create(
    payload: OrganisationCreate,
    _: OrganisationManager,
) -> OrganisationResponse:
    session = get_db_session()
    try:
        try:
            organisation = create_organisation(session, code=payload.code, name=payload.name)
        except OrganisationConflictError as exc:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
        return _organisation_response(organisation)
    finally:
        session.close()


@router.get("/users", response_model=list[UserOrganisationResponse])
def organisation_users(_: OrganisationReader) -> list[UserOrganisationResponse]:
    session = get_db_session()
    try:
        return [_user_response(user) for user in list_users_with_organisations(session)]
    finally:
        session.close()


@router.patch("/users/{user_id}", response_model=UserOrganisationResponse)
def organisation_user_update(
    user_id: uuid.UUID,
    payload: UserOrganisationUpdate,
    _: OrganisationManager,
) -> UserOrganisationResponse:
    session = get_db_session()
    try:
        try:
            user = assign_user_organisation(
                session,
                user_id=user_id,
                organisation_id=payload.organisation_id,
            )
        except OrganisationNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        except InactiveOrganisationError as exc:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
        return _user_response(user)
    finally:
        session.close()


@router.get("/{organisation_id}", response_model=OrganisationResponse)
def organisation_detail(
    organisation_id: uuid.UUID,
    _: OrganisationReader,
) -> OrganisationResponse:
    session = get_db_session()
    try:
        try:
            organisation = get_organisation(session, organisation_id)
        except OrganisationNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        return _organisation_response(organisation)
    finally:
        session.close()


@router.patch("/{organisation_id}", response_model=OrganisationResponse)
def organisation_update(
    organisation_id: uuid.UUID,
    payload: OrganisationUpdate,
    _: OrganisationManager,
) -> OrganisationResponse:
    session = get_db_session()
    try:
        try:
            organisation = get_organisation(session, organisation_id)
        except OrganisationNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        updated = update_organisation(
            session,
            organisation,
            name=payload.name,
            is_active=payload.is_active,
        )
        return _organisation_response(updated)
    finally:
        session.close()


@router.delete("/{organisation_id}", status_code=status.HTTP_204_NO_CONTENT)
def organisation_delete(
    organisation_id: uuid.UUID,
    _: OrganisationManager,
) -> Response:
    session = get_db_session()
    try:
        try:
            organisation = get_organisation(session, organisation_id)
            delete_organisation(session, organisation)
        except OrganisationNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        except OrganisationConflictError as exc:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    finally:
        session.close()
