from __future__ import annotations

import secrets
import uuid
from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from geoalchemy2.elements import WKTElement
from sqlalchemy import or_, select

from app.db.session import get_db_session
from app.models.citizen import CitizenReport, CitizenReportAttachment, IncidentAssignment
from app.models.climate import (
    FloodIncident,
    FloodRiskIndicator,
    FloodZone,
    HeatIndicator,
    SocioEconomicIndicator,
    Tree,
    TreeCatchment,
    TreeInspection,
    TreePlantingBatch,
    TreeSpecies,
    VulnerabilityIndicator,
    WeatherObservation,
)
from app.models.identity import User
from app.models.operations import Alert, DashboardDefinition, Notification
from app.models.outputs import AnalyticsMethodology, KnowledgeItem, Report, SystemSetting
from app.models.processing import ProcessingJob
from app.schemas.roadmap import (
    AlertCreate,
    CitizenCreate,
    CitizenModerate,
    CitizenOut,
    GenericCreate,
    HeatIndicatorOut,
    IndicatorCreate,
    JobCreate,
    JobOut,
    KnowledgeCreate,
    KnowledgeOut,
    MethodologyCreate,
    MethodologyOut,
    NotificationOut,
    ObservationOut,
    ReportCreate,
    ReportOut,
    SettingCreate,
)
from app.security.dependencies import CurrentUser, require_permission
from app.services.audit import record_audit_event
from app.services.object_storage import put_object
from app.services.processing import create_job, enqueue

router = APIRouter(tags=["roadmap-modules"])
AnalyticsReader = Annotated[User, Depends(require_permission("analytics.read"))]
AnalyticsManager = Annotated[User, Depends(require_permission("analytics.manage"))]
CitizenManager = Annotated[User, Depends(require_permission("citizen_reports.manage"))]
ReportsReader = Annotated[User, Depends(require_permission("reports.read"))]
ReportsManager = Annotated[User, Depends(require_permission("reports.manage"))]
AdminUser = Annotated[User, Depends(require_permission("users.manage"))]


def _commit(session: object) -> None:
    session.commit()  # type: ignore[attr-defined]


@router.post("/processing/jobs", response_model=JobOut)
def submit_job(payload: JobCreate, user: AnalyticsManager) -> JobOut:
    s = get_db_session()
    try:
        j = create_job(
            s,
            job_type=payload.job_type,
            dataset_version_id=payload.dataset_version_id,
            parameters=payload.parameters,
            idempotency_key=payload.idempotency_key,
            max_attempts=payload.max_attempts,
        )
        record_audit_event(
            s,
            action="processing.job.submit",
            resource_type="processing_job",
            resource_id=j.id,
            actor=user,
        )
        s.commit()
        enqueue(j)
        return JobOut.model_validate(j)
    finally:
        s.close()


@router.get("/processing/jobs", response_model=list[JobOut])
def jobs(_: AnalyticsReader, status: str | None = None) -> list[JobOut]:
    s = get_db_session()
    try:
        q = select(ProcessingJob).order_by(ProcessingJob.created_at.desc())
        q = q.where(ProcessingJob.status == status) if status else q
        return [JobOut.model_validate(x) for x in s.scalars(q).all()]
    finally:
        s.close()


@router.post("/processing/jobs/{job_id}/retry", response_model=JobOut)
def retry_job(job_id: uuid.UUID, user: AnalyticsManager) -> JobOut:
    s = get_db_session()
    try:
        j = s.get(ProcessingJob, job_id)
        if j is None:
            raise HTTPException(404, "Processing job not found.")
        if j.status != "FAILED":
            raise HTTPException(409, "Only failed jobs can be retried.")
        j.status = "PENDING"
        j.error_message = None
        record_audit_event(
            s,
            action="processing.job.retry",
            resource_type="processing_job",
            resource_id=j.id,
            actor=user,
        )
        s.commit()
        enqueue(j)
        return JobOut.model_validate(j)
    finally:
        s.close()


@router.get("/heat/observations", response_model=list[ObservationOut])
def heat_observations(
    _: AnalyticsReader,
    start: datetime | None = None,
    end: datetime | None = None,
    geographic_area_id: uuid.UUID | None = None,
) -> list[ObservationOut]:
    s = get_db_session()
    try:
        q = select(WeatherObservation).order_by(WeatherObservation.observed_at)
        q = q.where(WeatherObservation.observed_at >= start) if start else q
        q = q.where(WeatherObservation.observed_at <= end) if end else q
        q = (
            q.where(WeatherObservation.geographic_area_id == geographic_area_id)
            if geographic_area_id
            else q
        )
        return [ObservationOut.model_validate(x) for x in s.scalars(q).all()]
    finally:
        s.close()


@router.post("/heat/indicators", response_model=HeatIndicatorOut)
def add_heat_indicator(payload: IndicatorCreate, user: AnalyticsManager) -> HeatIndicatorOut:
    if not payload.methodology_version.strip():
        raise HTTPException(
            422, "methodology_version is required; CRAM does not invent scientific formulas."
        )
    s = get_db_session()
    try:
        x = HeatIndicator(**payload.model_dump())
        s.add(x)
        s.flush()
        record_audit_event(
            s,
            action="heat.indicator.create",
            resource_type="heat_indicator",
            resource_id=x.id,
            actor=user,
            details={"methodology_version": payload.methodology_version},
        )
        s.commit()
        return HeatIndicatorOut.model_validate(x)
    finally:
        s.close()


@router.get("/heat/indicators", response_model=list[HeatIndicatorOut])
def heat_indicators(_: AnalyticsReader) -> list[HeatIndicatorOut]:
    s = get_db_session()
    try:
        return [
            HeatIndicatorOut.model_validate(x)
            for x in s.scalars(
                select(HeatIndicator).order_by(HeatIndicator.period_start.desc())
            ).all()
        ]
    finally:
        s.close()


def _generic_list(model: type[Any], limit: int = 200) -> list[dict[str, object]]:
    s = get_db_session()
    try:
        rows = s.scalars(select(model).limit(limit)).all()
        return [
            {
                c.name: getattr(r, c.name)
                for c in model.__table__.columns
                if c.name not in {"geometry", "location"}
            }
            for r in rows
        ]
    finally:
        s.close()


@router.get("/flood/incidents")
def flood_incidents(_: AnalyticsReader) -> list[dict[str, object]]:
    return _generic_list(FloodIncident)


@router.get("/flood/zones")
def flood_zones(_: AnalyticsReader) -> list[dict[str, object]]:
    return _generic_list(FloodZone)


@router.get("/flood/indicators")
def flood_indicators(_: AnalyticsReader) -> list[dict[str, object]]:
    return _generic_list(FloodRiskIndicator)


@router.get("/trees")
def trees(_: AnalyticsReader) -> list[dict[str, object]]:
    return _generic_list(Tree)


@router.get("/trees/inspections")
def tree_inspections(_: AnalyticsReader) -> list[dict[str, object]]:
    return _generic_list(TreeInspection)


@router.get("/trees/batches")
def tree_batches(_: AnalyticsReader) -> list[dict[str, object]]:
    return _generic_list(TreePlantingBatch)


@router.get("/trees/species")
def tree_species(_: AnalyticsReader) -> list[dict[str, object]]:
    return _generic_list(TreeSpecies)


@router.get("/trees/catchments")
def tree_catchments(_: AnalyticsReader) -> list[dict[str, object]]:
    return _generic_list(TreeCatchment)


@router.get("/vulnerability/socio-economic")
def socioeconomic(_: AnalyticsReader) -> list[dict[str, object]]:
    return _generic_list(SocioEconomicIndicator)


@router.get("/vulnerability/indicators")
def vulnerability(_: AnalyticsReader) -> list[dict[str, object]]:
    return _generic_list(VulnerabilityIndicator)


@router.post("/citizen-reports", response_model=CitizenOut)
def submit_citizen(payload: CitizenCreate) -> CitizenOut:
    s = get_db_session()
    try:
        loc = (
            WKTElement(f"POINT({payload.longitude} {payload.latitude})", srid=4326)
            if payload.latitude is not None and payload.longitude is not None
            else None
        )
        r = CitizenReport(
            public_reference=f"CR-{secrets.token_hex(5).upper()}",
            hazard_type=payload.hazard_type,
            description=payload.description,
            occurred_at=payload.occurred_at,
            submitted_at=datetime.now(UTC),
            location=loc,
            reporter_name=payload.reporter_name,
            reporter_contact=payload.reporter_contact,
            consent_to_contact=payload.consent_to_contact,
            status="SUBMITTED",
            is_public=False,
        )
        s.add(r)
        s.commit()
        return CitizenOut.model_validate(r)
    finally:
        s.close()


@router.post("/citizen-reports/{report_id}/attachments")
async def add_citizen_attachment(report_id: uuid.UUID, request: Request) -> dict[str, object]:
    allowed = {"image/jpeg", "image/png"}
    content_type = (request.headers.get("content-type") or "").split(";", 1)[0].lower()
    if content_type not in allowed:
        raise HTTPException(415, "Only JPEG and PNG citizen-report attachments are accepted.")
    body = await request.body()
    if not body or len(body) > 10 * 1024 * 1024:
        raise HTTPException(413, "Attachment must be between 1 byte and 10 MiB.")
    import hashlib

    checksum = hashlib.sha256(body).hexdigest()
    filename = request.headers.get("x-filename", "attachment")
    safe_name = "".join(c for c in filename if c.isalnum() or c in "._-")[:120] or "attachment"
    s = get_db_session()
    try:
        report = s.get(CitizenReport, report_id)
        if report is None:
            raise HTTPException(404, "Citizen report not found.")
        key = f"citizen-reports/{report_id}/{uuid.uuid4()}-{safe_name}"
        put_object(key=key, body=body, content_type=content_type)
        item = CitizenReportAttachment(
            citizen_report_id=report_id,
            object_key=key,
            original_filename=safe_name,
            mime_type=content_type,
            size_bytes=len(body),
            checksum_sha256=checksum,
            scan_status="ACCEPTED",
        )
        s.add(item)
        s.commit()
        return {
            "id": item.id,
            "object_key": key,
            "mime_type": content_type,
            "size_bytes": len(body),
        }
    finally:
        s.close()


@router.post("/citizen-reports/{report_id}/assign")
def assign_citizen(
    report_id: uuid.UUID, payload: GenericCreate, user: CitizenManager
) -> dict[str, object]:
    try:
        organisation_id = uuid.UUID(str(payload.data["organisation_id"]))
    except (KeyError, ValueError) as exc:
        raise HTTPException(422, "organisation_id is required.") from exc
    assigned_user_id = (
        uuid.UUID(str(payload.data["assigned_user_id"]))
        if payload.data.get("assigned_user_id")
        else None
    )
    s = get_db_session()
    try:
        report = s.get(CitizenReport, report_id)
        if report is None:
            raise HTTPException(404, "Citizen report not found.")
        if report.status not in {"VALIDATED", "ASSIGNED", "IN_PROGRESS"}:
            raise HTTPException(409, "Only validated/active reports can be assigned.")
        a = IncidentAssignment(
            citizen_report_id=report_id,
            organisation_id=organisation_id,
            assigned_user_id=assigned_user_id,
            assigned_by_user_id=user.id,
            status="ASSIGNED",
            notes=str(payload.data.get("notes") or "") or None,
            assignment_metadata={},
        )
        s.add(a)
        report.status = "ASSIGNED"
        s.flush()
        record_audit_event(
            s,
            action="citizen_report.assign",
            resource_type="citizen_report",
            resource_id=report.id,
            actor=user,
            details={
                "organisation_id": str(organisation_id),
                "assigned_user_id": str(assigned_user_id) if assigned_user_id else None,
            },
        )
        s.commit()
        return {"id": a.id, "status": a.status}
    finally:
        s.close()


@router.get("/citizen-reports", response_model=list[CitizenOut])
def citizen_queue(_: CitizenManager) -> list[CitizenOut]:
    s = get_db_session()
    try:
        return [
            CitizenOut.model_validate(x)
            for x in s.scalars(
                select(CitizenReport).order_by(CitizenReport.submitted_at.desc())
            ).all()
        ]
    finally:
        s.close()


@router.patch("/citizen-reports/{report_id}", response_model=CitizenOut)
def moderate(report_id: uuid.UUID, payload: CitizenModerate, user: CitizenManager) -> CitizenOut:
    allowed = {
        "SUBMITTED",
        "UNDER_REVIEW",
        "VALIDATED",
        "ASSIGNED",
        "IN_PROGRESS",
        "RESOLVED",
        "CLOSED",
        "REJECTED",
    }
    if payload.status not in allowed:
        raise HTTPException(422, "Invalid citizen-report status.")
    s = get_db_session()
    try:
        r = s.get(CitizenReport, report_id)
        if r is None:
            raise HTTPException(404, "Citizen report not found.")
        r.status = payload.status
        r.is_public = payload.is_public
        r.moderation_notes = payload.notes
        record_audit_event(
            s,
            action="citizen_report.status",
            resource_type="citizen_report",
            resource_id=r.id,
            actor=user,
            details={"status": r.status, "is_public": r.is_public},
        )
        s.commit()
        return CitizenOut.model_validate(r)
    finally:
        s.close()


@router.get("/citizen-reports/public", response_model=list[CitizenOut])
def public_reports() -> list[CitizenOut]:
    s = get_db_session()
    try:
        return [
            CitizenOut.model_validate(x)
            for x in s.scalars(
                select(CitizenReport).where(
                    CitizenReport.is_public.is_(True),
                    CitizenReport.status.in_(
                        ["VALIDATED", "ASSIGNED", "IN_PROGRESS", "RESOLVED", "CLOSED"]
                    ),
                )
            ).all()
        ]
    finally:
        s.close()


@router.post("/alerts")
def create_alert(payload: AlertCreate, user: AnalyticsManager) -> dict[str, object]:
    s = get_db_session()
    try:
        a = Alert(
            alert_type=payload.alert_type,
            severity=payload.severity,
            title=payload.title,
            message=payload.message,
            resource_type=payload.resource_type,
            resource_id=payload.resource_id,
        )
        s.add(a)
        s.flush()
        for uid in payload.recipient_user_ids:
            s.add(
                Notification(
                    alert_id=a.id,
                    recipient_user_id=uid,
                    channel="IN_APP",
                    status="DELIVERED",
                    attempt_count=1,
                    delivered_at=datetime.now(UTC),
                )
            )
        record_audit_event(
            s, action="alert.create", resource_type="alert", resource_id=a.id, actor=user
        )
        s.commit()
        return {"id": a.id, "notification_count": len(payload.recipient_user_ids)}
    finally:
        s.close()


@router.get("/notifications", response_model=list[NotificationOut])
def notifications(user: CurrentUser) -> list[NotificationOut]:
    s = get_db_session()
    try:
        return [
            NotificationOut.model_validate(x)
            for x in s.scalars(
                select(Notification)
                .where(Notification.recipient_user_id == user.id)
                .order_by(Notification.created_at.desc())
            ).all()
        ]
    finally:
        s.close()


@router.post("/notifications/{notification_id}/read", response_model=NotificationOut)
def read_notification(notification_id: uuid.UUID, user: CurrentUser) -> NotificationOut:
    s = get_db_session()
    try:
        n = s.get(Notification, notification_id)
        if n is None or n.recipient_user_id != user.id:
            raise HTTPException(404, "Notification not found.")
        n.read_at = datetime.now(UTC)
        s.commit()
        return NotificationOut.model_validate(n)
    finally:
        s.close()


@router.get("/dashboards")
def dashboards(user: CurrentUser) -> list[dict[str, object]]:
    perms = {p.code for role in user.roles for p in role.permissions}
    s = get_db_session()
    try:
        rows = s.scalars(select(DashboardDefinition).order_by(DashboardDefinition.name)).all()
        return [
            {
                "id": x.id,
                "code": x.code,
                "name": x.name,
                "configuration": x.configuration,
                "is_public": x.is_public,
            }
            for x in rows
            if x.is_public or x.required_permission is None or x.required_permission in perms
        ]
    finally:
        s.close()


@router.post("/reports", response_model=ReportOut)
def create_report(payload: ReportCreate, user: ReportsManager) -> ReportOut:
    s = get_db_session()
    try:
        r = Report(
            report_type=payload.report_type,
            parameters=payload.parameters,
            requested_by_user_id=user.id,
            source_dataset_version_ids=payload.source_dataset_version_ids,
            status="PENDING",
        )
        s.add(r)
        s.flush()
        j = create_job(
            s,
            job_type="report.generate",
            dataset_version_id=None,
            parameters={"report_id": str(r.id), "format": payload.format},
            idempotency_key=f"report:{r.id}:{payload.format}",
        )
        r.processing_job_id = j.id
        record_audit_event(
            s, action="report.request", resource_type="report", resource_id=r.id, actor=user
        )
        s.commit()
        enqueue(j)
        return ReportOut.model_validate(r)
    finally:
        s.close()


@router.get("/reports", response_model=list[ReportOut])
def reports(_: ReportsReader) -> list[ReportOut]:
    s = get_db_session()
    try:
        return [
            ReportOut.model_validate(x)
            for x in s.scalars(select(Report).order_by(Report.created_at.desc())).all()
        ]
    finally:
        s.close()


@router.post("/knowledge", response_model=KnowledgeOut)
def create_knowledge(payload: KnowledgeCreate, user: ReportsManager) -> KnowledgeOut:
    s = get_db_session()
    try:
        x = KnowledgeItem(**payload.model_dump())
        s.add(x)
        s.flush()
        record_audit_event(
            s,
            action="knowledge.create",
            resource_type="knowledge_item",
            resource_id=x.id,
            actor=user,
        )
        s.commit()
        return KnowledgeOut.model_validate(x)
    finally:
        s.close()


@router.get("/knowledge", response_model=list[KnowledgeOut])
def search_knowledge(
    user: CurrentUser, q: Annotated[str | None, Query()] = None
) -> list[KnowledgeOut]:
    s = get_db_session()
    try:
        stmt = select(KnowledgeItem).where(KnowledgeItem.is_active.is_(True))
        stmt = (
            stmt.where(
                or_(KnowledgeItem.title.ilike(f"%{q}%"), KnowledgeItem.summary.ilike(f"%{q}%"))
            )
            if q
            else stmt
        )
        rows = s.scalars(stmt.order_by(KnowledgeItem.title)).all()
        perms = {p.code for role in user.roles for p in role.permissions}
        can_restricted = bool(perms & {"reports.read", "datasets.read"})
        return [
            KnowledgeOut.model_validate(x)
            for x in rows
            if x.visibility == "PUBLIC" or can_restricted
        ]
    finally:
        s.close()


@router.get("/knowledge/public", response_model=list[KnowledgeOut])
def public_knowledge() -> list[KnowledgeOut]:
    s = get_db_session()
    try:
        return [
            KnowledgeOut.model_validate(x)
            for x in s.scalars(
                select(KnowledgeItem).where(
                    KnowledgeItem.visibility == "PUBLIC", KnowledgeItem.is_active.is_(True)
                )
            ).all()
        ]
    finally:
        s.close()


@router.get("/admin/settings")
def settings(_: AdminUser) -> list[dict[str, object]]:
    s = get_db_session()
    try:
        return [
            {"id": x.id, "key": x.key, "value": x.value, "description": x.description}
            for x in s.scalars(
                select(SystemSetting).where(SystemSetting.is_secret.is_(False))
            ).all()
        ]
    finally:
        s.close()


@router.post("/admin/settings")
def set_setting(payload: SettingCreate, user: AdminUser) -> dict[str, object]:
    s = get_db_session()
    try:
        x = s.scalar(select(SystemSetting).where(SystemSetting.key == payload.key))
        x = x or SystemSetting(key=payload.key, is_secret=False)
        x.value = payload.value
        x.description = payload.description
        s.add(x)
        s.flush()
        record_audit_event(
            s,
            action="admin.setting.update",
            resource_type="system_setting",
            resource_id=x.id,
            actor=user,
            details={"key": x.key},
        )
        s.commit()
        return {"id": x.id, "key": x.key, "value": x.value}
    finally:
        s.close()


@router.post("/analytics/methodologies", response_model=MethodologyOut)
def create_methodology(payload: MethodologyCreate, user: AnalyticsManager) -> MethodologyOut:
    s = get_db_session()
    try:
        x = AnalyticsMethodology(**payload.model_dump(), status="DRAFT")
        s.add(x)
        s.flush()
        record_audit_event(
            s,
            action="analytics.methodology.create",
            resource_type="analytics_methodology",
            resource_id=x.id,
            actor=user,
        )
        s.commit()
        return MethodologyOut.model_validate(x)
    finally:
        s.close()


@router.get("/analytics/methodologies", response_model=list[MethodologyOut])
def methodologies(_: AnalyticsReader) -> list[MethodologyOut]:
    s = get_db_session()
    try:
        return [
            MethodologyOut.model_validate(x)
            for x in s.scalars(
                select(AnalyticsMethodology).order_by(
                    AnalyticsMethodology.domain, AnalyticsMethodology.code
                )
            ).all()
        ]
    finally:
        s.close()
