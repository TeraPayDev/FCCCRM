from __future__ import annotations

import uuid

from pydantic import BaseModel, Field, field_validator


class RoleResponse(BaseModel):
    id: uuid.UUID
    code: str
    name: str
    description: str | None = None


class UserAdminResponse(BaseModel):
    id: uuid.UUID
    username: str
    email: str
    is_active: bool
    organisation_id: uuid.UUID | None
    organisation_code: str | None
    organisation_name: str | None
    roles: list[str]
    created_at: str
    updated_at: str
    locked_until: str | None = None


class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=120)
    email: str = Field(min_length=5, max_length=320)
    password: str = Field(min_length=12, max_length=256)
    organisation_id: uuid.UUID | None = None
    role_codes: list[str] = Field(default_factory=list)

    @field_validator("email")
    @classmethod
    def valid_email(cls, value: str) -> str:
        normalized = value.strip().lower()
        if "@" not in normalized or normalized.startswith("@") or normalized.endswith("@"):
            raise ValueError("Enter a valid email address.")
        return normalized


class UserUpdate(BaseModel):
    email: str | None = Field(default=None, min_length=5, max_length=320)
    organisation_id: uuid.UUID | None = None
    role_codes: list[str] | None = None
    is_active: bool | None = None
    password: str | None = Field(default=None, min_length=12, max_length=256)

    @field_validator("email")
    @classmethod
    def valid_optional_email(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip().lower()
        if "@" not in normalized or normalized.startswith("@") or normalized.endswith("@"):
            raise ValueError("Enter a valid email address.")
        return normalized
