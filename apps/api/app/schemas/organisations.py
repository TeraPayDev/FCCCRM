from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class OrganisationCreate(BaseModel):
    code: str = Field(min_length=2, max_length=64, pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
    name: str = Field(min_length=2, max_length=200)


class OrganisationUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=200)
    is_active: bool | None = None


class OrganisationResponse(BaseModel):
    id: uuid.UUID
    code: str
    name: str
    is_active: bool
    created_at: datetime
    updated_at: datetime


class UserOrganisationUpdate(BaseModel):
    organisation_id: uuid.UUID | None


class UserOrganisationResponse(BaseModel):
    id: uuid.UUID
    username: str
    email: str
    is_active: bool
    organisation_id: uuid.UUID | None
    organisation_code: str | None
    organisation_name: str | None
