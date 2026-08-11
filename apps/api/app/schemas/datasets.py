from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field, model_validator


class DatasetCreate(BaseModel):
    code: str = Field(min_length=1, max_length=120)
    name: str = Field(min_length=1, max_length=240)
    description: str | None = None
    owner_organisation_id: uuid.UUID
    category: str | None = Field(default=None, max_length=120)
    sensitivity: str = Field(default="INTERNAL", max_length=40)
    expected_format: str = Field(default="CSV", max_length=40)
    update_frequency: str | None = Field(default=None, max_length=120)


class DatasetUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=240)
    description: str | None = None
    owner_organisation_id: uuid.UUID | None = None
    category: str | None = Field(default=None, max_length=120)
    sensitivity: str | None = Field(default=None, max_length=40)
    expected_format: str | None = Field(default=None, max_length=40)
    update_frequency: str | None = Field(default=None, max_length=120)
    status: str | None = Field(default=None, max_length=40)


class DatasetResponse(BaseModel):
    id: uuid.UUID
    code: str
    name: str
    description: str | None
    owner_organisation_id: uuid.UUID
    category: str | None
    sensitivity: str
    expected_format: str
    update_frequency: str | None
    status: str
    created_at: datetime
    updated_at: datetime


class DatasetPage(BaseModel):
    items: list[DatasetResponse]
    total: int
    offset: int
    limit: int


class DatasetSourceCreate(BaseModel):
    provider_organisation_id: uuid.UUID | None = None
    name: str = Field(min_length=1, max_length=240)
    source_type: str = Field(min_length=1, max_length=50)
    source_reference: str | None = Field(default=None, max_length=500)
    connection_secret_ref: str | None = Field(default=None, max_length=300)
    update_method: str | None = Field(default=None, max_length=120)

    @model_validator(mode="after")
    def reject_embedded_credentials(self) -> DatasetSourceCreate:
        reference = (self.source_reference or "").lower()
        forbidden = ("password=", "secret=", "token=", "api_key=", "apikey=")
        if any(marker in reference for marker in forbidden):
            raise ValueError(
                "Dataset source metadata must not contain credentials; use connection_secret_ref."
            )
        if "://" in reference and "@" in reference.split("://", 1)[1].split("/", 1)[0]:
            raise ValueError("Dataset source URL must not contain user-info credentials.")
        return self


class DatasetSourceResponse(BaseModel):
    id: uuid.UUID
    dataset_id: uuid.UUID
    provider_organisation_id: uuid.UUID | None
    name: str
    source_type: str
    source_reference: str | None
    connection_secret_ref: str | None
    update_method: str | None
    created_at: datetime
    updated_at: datetime


class DatasetFieldCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    data_type: str = Field(min_length=1, max_length=80)
    ordinal: int = Field(ge=0)
    is_required: bool = False
    description: str | None = None
    validation_rules: dict[str, object] = Field(default_factory=dict)


class DatasetFieldResponse(BaseModel):
    id: uuid.UUID
    dataset_id: uuid.UUID
    name: str
    data_type: str
    ordinal: int
    is_required: bool
    description: str | None
    validation_rules: dict[str, object]
    created_at: datetime
    updated_at: datetime


class DatasetVersionResponse(BaseModel):
    id: uuid.UUID
    dataset_id: uuid.UUID
    source_id: uuid.UUID | None
    version_number: int
    status: str
    checksum_sha256: str | None
    row_count: int | None
    published_at: datetime | None
    created_at: datetime
    updated_at: datetime


class DatasetUploadResponse(BaseModel):
    id: uuid.UUID
    dataset_version_id: uuid.UUID
    uploaded_by_user_id: uuid.UUID | None
    object_key: str
    original_filename: str
    mime_type: str | None
    size_bytes: int
    checksum_sha256: str | None
    created_at: datetime
    updated_at: datetime


class ValidationErrorResponse(BaseModel):
    id: uuid.UUID
    validation_run_id: uuid.UUID
    row_number: int | None
    field_name: str | None
    rule_code: str
    severity: str
    message: str
    value_excerpt: str | None
    created_at: datetime


class ValidationRunResponse(BaseModel):
    id: uuid.UUID
    dataset_version_id: uuid.UUID
    status: str
    execution_mode: str
    started_at: datetime | None
    completed_at: datetime | None
    total_rows: int
    error_count: int
    warning_count: int
    created_at: datetime
    updated_at: datetime
    errors: list[ValidationErrorResponse] = Field(default_factory=list)


class ApprovalAction(BaseModel):
    comments: str | None = None


class ApprovalResponse(BaseModel):
    id: uuid.UUID
    dataset_version_id: uuid.UUID
    submitted_by_user_id: uuid.UUID | None
    reviewed_by_user_id: uuid.UUID | None
    status: str
    comments: str | None
    submitted_at: datetime
    reviewed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class VersionStatusHistoryResponse(BaseModel):
    id: uuid.UUID
    dataset_version_id: uuid.UUID
    from_status: str | None
    to_status: str
    changed_by_user_id: uuid.UUID | None
    comment: str | None
    created_at: datetime
