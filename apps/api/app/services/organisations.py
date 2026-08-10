from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.models.identity import Organisation, User


class OrganisationNotFoundError(LookupError):
    pass


class OrganisationConflictError(ValueError):
    pass


class InactiveOrganisationError(ValueError):
    pass


def list_organisations(session: Session) -> list[Organisation]:
    return list(session.scalars(select(Organisation).order_by(Organisation.code)).all())


def get_organisation(session: Session, organisation_id: uuid.UUID) -> Organisation:
    organisation = session.get(Organisation, organisation_id)
    if organisation is None:
        raise OrganisationNotFoundError("Organisation not found.")
    return organisation


def create_organisation(
    session: Session,
    *,
    code: str,
    name: str,
) -> Organisation:
    organisation = Organisation(code=code.strip(), name=name.strip(), is_active=True)
    session.add(organisation)
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise OrganisationConflictError("Organisation code already exists.") from exc
    session.refresh(organisation)
    return organisation


def update_organisation(
    session: Session,
    organisation: Organisation,
    *,
    name: str | None,
    is_active: bool | None,
) -> Organisation:
    if name is not None:
        organisation.name = name.strip()
    if is_active is not None:
        organisation.is_active = is_active
    session.commit()
    session.refresh(organisation)
    return organisation


def delete_organisation(session: Session, organisation: Organisation) -> None:
    session.delete(organisation)
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise OrganisationConflictError(
            "Organisation is referenced by protected records and cannot be deleted. Deactivate it instead."
        ) from exc


def list_users_with_organisations(session: Session) -> list[User]:
    return list(
        session.scalars(
            select(User).options(selectinload(User.organisation)).order_by(User.username)
        ).all()
    )


def assign_user_organisation(
    session: Session,
    *,
    user_id: uuid.UUID,
    organisation_id: uuid.UUID | None,
) -> User:
    user = session.scalar(
        select(User).options(selectinload(User.organisation)).where(User.id == user_id)
    )
    if user is None:
        raise OrganisationNotFoundError("User not found.")

    if organisation_id is not None:
        organisation = get_organisation(session, organisation_id)
        if not organisation.is_active:
            raise InactiveOrganisationError("Users cannot be assigned to an inactive organisation.")
        user.organisation_id = organisation.id
    else:
        user.organisation_id = None

    session.commit()
    return (
        session.scalar(
            select(User).options(selectinload(User.organisation)).where(User.id == user_id)
        )
        or user
    )
