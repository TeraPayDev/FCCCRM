from __future__ import annotations

import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class JobCreate(BaseModel):
    job_type: str
    dataset_version_id: uuid.UUID | None = None
    parameters: dict[str, object] = Field(default_factory=dict)
    idempotency_key: str
    max_attempts: int = 3


class JobOut(ORMModel):
    id: uuid.UUID
    job_type: str
    dataset_version_id: uuid.UUID | None
    status: str
    stage: str
    parameters: dict[str, object]
    idempotency_key: str
    attempts: int
    max_attempts: int
    started_at: datetime | None
    completed_at: datetime | None
    output_reference: str | None
    error_message: str | None
    created_at: datetime
    updated_at: datetime


class ObservationOut(ORMModel):
    id: uuid.UUID
    dataset_version_id: uuid.UUID
    observed_at: datetime
    station_code: str | None
    geographic_area_id: uuid.UUID | None
    temperature_c: float | None
    humidity_pct: float | None
    heat_index_c: float | None
    methodology_version: str | None
    created_at: datetime


class IndicatorCreate(BaseModel):
    dataset_version_id: uuid.UUID
    geographic_area_id: uuid.UUID | None = None
    period_start: date
    period_end: date
    indicator_code: str
    value: float
    unit: str
    classification: str | None = None
    methodology_version: str
    methodology_metadata: dict[str, object] = Field(default_factory=dict)


class HeatIndicatorOut(ORMModel):
    id: uuid.UUID
    dataset_version_id: uuid.UUID
    geographic_area_id: uuid.UUID | None
    period_start: date
    period_end: date
    indicator_code: str
    value: float
    unit: str
    classification: str | None
    methodology_version: str | None
    methodology_metadata: dict[str, object]


class GenericCreate(BaseModel):
    data: dict[str, object]


class CitizenCreate(BaseModel):
    hazard_type: str
    description: str
    latitude: float | None = None
    longitude: float | None = None
    occurred_at: datetime | None = None
    reporter_name: str | None = None
    reporter_contact: str | None = None
    consent_to_contact: bool = False


class CitizenOut(ORMModel):
    id: uuid.UUID
    public_reference: str
    hazard_type: str
    description: str
    occurred_at: datetime | None
    submitted_at: datetime
    status: str
    is_public: bool
    created_at: datetime


class CitizenModerate(BaseModel):
    status: str
    is_public: bool = False
    notes: str | None = None


class AlertCreate(BaseModel):
    alert_type: str
    severity: str
    title: str
    message: str
    resource_type: str | None = None
    resource_id: uuid.UUID | None = None
    recipient_user_ids: list[uuid.UUID] = Field(default_factory=list)


class NotificationOut(ORMModel):
    id: uuid.UUID
    alert_id: uuid.UUID
    recipient_user_id: uuid.UUID
    channel: str
    status: str
    delivered_at: datetime | None
    read_at: datetime | None
    created_at: datetime


class ReportCreate(BaseModel):
    report_type: str
    parameters: dict[str, object] = Field(default_factory=dict)
    source_dataset_version_ids: list[uuid.UUID] = Field(default_factory=list)
    format: str = "CSV"


class ReportOut(ORMModel):
    id: uuid.UUID
    report_type: str
    parameters: dict[str, object]
    source_dataset_version_ids: list[uuid.UUID]
    status: str
    file_reference: str | None
    processing_job_id: uuid.UUID | None
    completed_at: datetime | None
    created_at: datetime


class KnowledgeCreate(BaseModel):
    title: str
    content_type: str
    organisation_id: uuid.UUID | None = None
    visibility: str = "RESTRICTED"
    summary: str | None = None
    file_reference: str | None = None
    tags: list[str] = Field(default_factory=list)
    version_label: str | None = None
    related_dataset_id: uuid.UUID | None = None
    related_report_id: uuid.UUID | None = None


class KnowledgeOut(ORMModel):
    id: uuid.UUID
    title: str
    content_type: str
    organisation_id: uuid.UUID | None
    visibility: str
    summary: str | None
    file_reference: str | None
    tags: list[str]
    version_label: str | None
    related_dataset_id: uuid.UUID | None
    related_report_id: uuid.UUID | None
    created_at: datetime


class MethodologyCreate(BaseModel):
    code: str
    version: str
    domain: str
    description: str
    assumptions: dict[str, object] = Field(default_factory=dict)


class MethodologyOut(ORMModel):
    id: uuid.UUID
    code: str
    version: str
    domain: str
    status: str
    description: str
    assumptions: dict[str, object]
    validation_summary: str | None
    approved_by: str | None
    approved_at: datetime | None


class SettingCreate(BaseModel):
    key: str
    value: dict[str, object] = Field(default_factory=dict)
    description: str | None = None
