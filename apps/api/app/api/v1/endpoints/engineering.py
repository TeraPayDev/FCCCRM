from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, Field
from sqlalchemy import func, select

from app.db.session import get_db_session
from app.models.citizen import CitizenReport
from app.models.engineering import IntegrationConnector, IntegrationRun, ProcessingSchedule
from app.models.identity import User
from app.models.outputs import Report
from app.models.processing import ProcessingJob
from app.security.dependencies import require_permission
from app.services.connectors import sandbox_pull
from app.services.object_storage import get_object
from app.services.predictive import (
    canopy_trend,
    flood_probability,
    heat_trend,
    vulnerability_scenario,
)
from app.services.processing import create_job, enqueue

router = APIRouter(tags=["engineering-extension"])
AnalyticsReader = Annotated[User, Depends(require_permission("analytics.read"))]
AnalyticsManager = Annotated[User, Depends(require_permission("analytics.manage"))]
AdminUser = Annotated[User, Depends(require_permission("users.manage"))]


class TrendRequest(BaseModel):
    values: list[float] = Field(min_length=2, max_length=500)
    periods: int = Field(default=7, ge=1, le=60)


class FloodRequest(BaseModel):
    features: dict[str, float]
    coefficients: dict[str, float]


class VulnerabilityRequest(BaseModel):
    indicators: dict[str, float]
    weights: dict[str, float]
    adjustments: dict[str, float] = Field(default_factory=dict)


class ScheduleCreate(BaseModel):
    code: str
    job_type: str
    dataset_version_id: uuid.UUID | None = None
    interval_minutes: int = Field(ge=5, le=525600)
    parameters: dict[str, object] = Field(default_factory=dict)
    next_run_at: datetime | None = None


class ConnectorCreate(BaseModel):
    code: str
    institution: str
    connector_type: str = "MOCK_API"
    base_url: str | None = None
    configuration: dict[str, object] = Field(default_factory=dict)
    sandbox_mode: bool = True


@router.post("/analytics/predict/heat")
def predict_heat(payload: TrendRequest, _: AnalyticsReader) -> dict[str, object]:
    return heat_trend(payload.values, payload.periods)


@router.post("/analytics/predict/canopy")
def predict_canopy(payload: TrendRequest, _: AnalyticsReader) -> dict[str, object]:
    return canopy_trend(payload.values, payload.periods)


@router.post("/analytics/predict/flood")
def predict_flood(payload: FloodRequest, _: AnalyticsReader) -> dict[str, object]:
    return flood_probability(payload.features, payload.coefficients)


@router.post("/analytics/scenarios/vulnerability")
def scenario_vulnerability(payload: VulnerabilityRequest, _: AnalyticsReader) -> dict[str, object]:
    return vulnerability_scenario(payload.indicators, payload.weights, payload.adjustments)


@router.post("/processing/schedules")
def create_schedule(payload: ScheduleCreate, _: AnalyticsManager) -> dict[str, object]:
    s = get_db_session()
    try:
        if s.scalar(select(ProcessingSchedule).where(ProcessingSchedule.code == payload.code)):
            raise HTTPException(409, "Processing schedule code already exists.")
        item = ProcessingSchedule(
            **payload.model_dump(exclude={"next_run_at"}),
            next_run_at=payload.next_run_at or datetime.now(UTC),
        )
        s.add(item)
        s.commit()
        s.refresh(item)
        return {
            "id": item.id,
            "code": item.code,
            "job_type": item.job_type,
            "next_run_at": item.next_run_at,
            "is_active": item.is_active,
        }
    finally:
        s.close()


@router.get("/processing/schedules")
def schedules(_: AnalyticsReader) -> list[dict[str, object]]:
    s = get_db_session()
    try:
        rows = s.scalars(select(ProcessingSchedule).order_by(ProcessingSchedule.code)).all()
        return [
            {
                "id": x.id,
                "code": x.code,
                "job_type": x.job_type,
                "interval_minutes": x.interval_minutes,
                "next_run_at": x.next_run_at,
                "last_run_at": x.last_run_at,
                "last_status": x.last_status,
                "consecutive_failures": x.consecutive_failures,
                "is_active": x.is_active,
            }
            for x in rows
        ]
    finally:
        s.close()


@router.post("/processing/schedules/run-due")
def run_due(_: AnalyticsManager) -> dict[str, object]:
    now = datetime.now(UTC)
    queued = 0
    s = get_db_session()
    try:
        rows = s.scalars(
            select(ProcessingSchedule)
            .where(ProcessingSchedule.is_active.is_(True), ProcessingSchedule.next_run_at <= now)
            .with_for_update(skip_locked=True)
        ).all()
        for item in rows:
            key = f"schedule:{item.id}:{item.next_run_at.isoformat()}"
            job = create_job(
                s,
                job_type=item.job_type,
                dataset_version_id=item.dataset_version_id,
                parameters=item.parameters,
                idempotency_key=key,
            )
            item.last_run_at = now
            item.last_status = "QUEUED"
            item.next_run_at = now + timedelta(minutes=item.interval_minutes)
            enqueue(job)
            queued += 1
        s.commit()
        return {"queued": queued, "checked_at": now}
    finally:
        s.close()


@router.get("/processing/monitoring")
def processing_monitoring(_: AnalyticsReader) -> dict[str, object]:
    s = get_db_session()
    try:
        counts: dict[str, int] = {
            status: int(count)
            for status, count in s.execute(
                select(ProcessingJob.status, func.count()).group_by(ProcessingJob.status)
            ).tuples()
        }
        failed = s.scalars(
            select(ProcessingJob)
            .where(ProcessingJob.status == "FAILED")
            .order_by(ProcessingJob.updated_at.desc())
            .limit(10)
        ).all()
        return {
            "counts": counts,
            "recent_failures": [
                {
                    "id": x.id,
                    "job_type": x.job_type,
                    "attempts": x.attempts,
                    "error": x.error_message,
                    "updated_at": x.updated_at,
                }
                for x in failed
            ],
        }
    finally:
        s.close()


@router.post("/integrations/connectors")
def create_connector(payload: ConnectorCreate, _: AdminUser) -> dict[str, object]:
    if not payload.sandbox_mode and not payload.base_url:
        raise HTTPException(422, "A base_url is required when sandbox_mode is false.")
    s = get_db_session()
    try:
        item = IntegrationConnector(**payload.model_dump())
        s.add(item)
        s.commit()
        s.refresh(item)
        return {
            "id": item.id,
            "code": item.code,
            "institution": item.institution,
            "sandbox_mode": item.sandbox_mode,
            "is_active": item.is_active,
        }
    finally:
        s.close()


@router.get("/integrations/connectors")
def connectors(_: AdminUser) -> list[dict[str, object]]:
    s = get_db_session()
    try:
        rows = s.scalars(
            select(IntegrationConnector).order_by(IntegrationConnector.institution)
        ).all()
        return [
            {
                "id": x.id,
                "code": x.code,
                "institution": x.institution,
                "connector_type": x.connector_type,
                "base_url": x.base_url,
                "sandbox_mode": x.sandbox_mode,
                "is_active": x.is_active,
            }
            for x in rows
        ]
    finally:
        s.close()


@router.post("/integrations/connectors/{connector_id}/test")
def test_connector(connector_id: uuid.UUID, _: AdminUser) -> dict[str, object]:
    s = get_db_session()
    try:
        connector = s.get(IntegrationConnector, connector_id)
        if connector is None:
            raise HTTPException(404, "Connector not found.")
        if not connector.sandbox_mode:
            raise HTTPException(
                409,
                "Live connector execution is disabled until institution credentials/contracts are approved.",
            )
        started = datetime.now(UTC)
        result = sandbox_pull(connector.institution, connector.configuration)
        run = IntegrationRun(
            connector_id=connector.id,
            status="SUCCEEDED",
            records_received=int(str(result["record_count"])),
            started_at=started,
            completed_at=datetime.now(UTC),
            run_metadata={"mode": "sandbox"},
        )
        s.add(run)
        s.commit()
        return result
    finally:
        s.close()


@router.get("/dashboards/executive-summary")
def executive_summary(_: AnalyticsReader) -> dict[str, object]:
    s = get_db_session()
    try:
        jobs: dict[str, int] = {
            status: int(count)
            for status, count in s.execute(
                select(ProcessingJob.status, func.count()).group_by(ProcessingJob.status)
            ).tuples()
        }
        citizens: dict[str, int] = {
            status: int(count)
            for status, count in s.execute(
                select(CitizenReport.status, func.count()).group_by(CitizenReport.status)
            ).tuples()
        }
        report_count = int(s.scalar(select(func.count()).select_from(Report)) or 0)
        connector_count = int(
            s.scalar(
                select(func.count())
                .select_from(IntegrationConnector)
                .where(IntegrationConnector.is_active.is_(True))
            )
            or 0
        )
        return {
            "processing_jobs": jobs,
            "citizen_reports": citizens,
            "reports": report_count,
            "active_connectors": connector_count,
            "generated_at": datetime.now(UTC),
        }
    finally:
        s.close()


@router.get("/reports/{report_id}/download")
def download_report(report_id: uuid.UUID, _: AnalyticsReader) -> Response:
    s = get_db_session()
    try:
        report = s.get(Report, report_id)
        if report is None:
            raise HTTPException(404, "Report not found.")
        if report.status != "COMPLETED" or not report.file_reference:
            raise HTTPException(409, "Report output is not ready.")
        body = get_object(report.file_reference)
        return Response(
            content=body,
            media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="cram-report-{report.id}.csv"'},
        )
    finally:
        s.close()
