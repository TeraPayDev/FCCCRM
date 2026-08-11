from __future__ import annotations

import csv
import io
import uuid
from datetime import date, datetime

from geoalchemy2.elements import WKTElement
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.climate import (
    FloodIncident,
    FloodZone,
    SocioEconomicIndicator,
    Tree,
    TreeInspection,
    WeatherObservation,
)
from app.models.data_management import DatasetUpload, DatasetVersion
from app.models.processing import ProcessingJob
from app.services.object_storage import get_object
from app.services.processing import registry


def _rows(session: Session, job: ProcessingJob) -> tuple[DatasetVersion, list[dict[str, str]]]:
    if job.dataset_version_id is None:
        raise ValueError("dataset_version_id is required")
    version = session.get(DatasetVersion, job.dataset_version_id)
    if version is None or version.status not in {"VALIDATED", "APPROVED", "PUBLISHED"}:
        raise ValueError("Processor requires a validated, approved, or published DatasetVersion.")
    upload = session.scalar(
        select(DatasetUpload)
        .where(DatasetUpload.dataset_version_id == version.id)
        .order_by(DatasetUpload.created_at.desc())
    )
    if upload is None:
        raise ValueError("DatasetVersion has no preserved upload.")
    body = get_object(upload.object_key).decode("utf-8-sig")
    return version, list(csv.DictReader(io.StringIO(body)))


def _columns(job: ProcessingJob, defaults: dict[str, str]) -> dict[str, str]:
    result = dict(defaults)
    custom = job.parameters.get("columns")
    if isinstance(custom, dict):
        result.update({str(key): str(value) for key, value in custom.items()})
    return result


def _float(value: str | None) -> float | None:
    return None if value is None or value.strip() == "" else float(value)


def _int(value: str | None) -> int | None:
    return None if value is None or value.strip() == "" else int(value)


def _uuid(value: str | None) -> uuid.UUID | None:
    return None if value is None or value.strip() == "" else uuid.UUID(value)


def _datetime(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _date(value: str) -> date:
    return date.fromisoformat(value)


class WeatherObservationProcessor:
    job_type = "heat.weather.import"

    def run(self, session: Session, job: ProcessingJob) -> str | None:
        version, rows = _rows(session, job)
        columns = _columns(
            job,
            {
                "observed_at": "observed_at",
                "station_code": "station_code",
                "temperature_c": "temperature_c",
                "humidity_pct": "humidity_pct",
                "heat_index_c": "heat_index_c",
                "geographic_area_id": "geographic_area_id",
                "longitude": "longitude",
                "latitude": "latitude",
            },
        )
        session.query(WeatherObservation).filter(
            WeatherObservation.dataset_version_id == version.id
        ).delete(synchronize_session=False)
        for number, row in enumerate(rows, start=2):
            observed = row.get(columns["observed_at"])
            if not observed:
                raise ValueError(f"Missing observed_at at CSV row {number}")
            lon = _float(row.get(columns["longitude"]))
            lat = _float(row.get(columns["latitude"]))
            location = (
                WKTElement(f"POINT({lon} {lat})", srid=4326)
                if lon is not None and lat is not None
                else None
            )
            session.add(
                WeatherObservation(
                    dataset_version_id=version.id,
                    observed_at=_datetime(observed),
                    station_code=row.get(columns["station_code"]) or None,
                    geographic_area_id=_uuid(row.get(columns["geographic_area_id"])),
                    temperature_c=_float(row.get(columns["temperature_c"])),
                    humidity_pct=_float(row.get(columns["humidity_pct"])),
                    heat_index_c=_float(row.get(columns["heat_index_c"])),
                    location=location,
                    source_row_number=number,
                    methodology_version=None,
                )
            )
        session.flush()
        return f"weather-observations:{version.id}"


class FloodIncidentProcessor:
    job_type = "flood.incidents.import"

    def run(self, session: Session, job: ProcessingJob) -> str | None:
        version, rows = _rows(session, job)
        columns = _columns(
            job,
            {
                "occurred_at": "occurred_at",
                "severity": "severity",
                "description": "description",
                "geographic_area_id": "geographic_area_id",
                "longitude": "longitude",
                "latitude": "latitude",
            },
        )
        session.query(FloodIncident).filter(FloodIncident.dataset_version_id == version.id).delete(
            synchronize_session=False
        )
        for number, row in enumerate(rows, start=2):
            occurred = row.get(columns["occurred_at"])
            if not occurred:
                raise ValueError(f"Missing occurred_at at CSV row {number}")
            lon = _float(row.get(columns["longitude"]))
            lat = _float(row.get(columns["latitude"]))
            session.add(
                FloodIncident(
                    dataset_version_id=version.id,
                    occurred_at=_datetime(occurred),
                    severity=row.get(columns["severity"]) or None,
                    description=row.get(columns["description"]) or None,
                    geographic_area_id=_uuid(row.get(columns["geographic_area_id"])),
                    location=WKTElement(f"POINT({lon} {lat})", srid=4326)
                    if lon is not None and lat is not None
                    else None,
                    methodology_version=None,
                )
            )
        session.flush()
        return f"flood-incidents:{version.id}"


class FloodZoneProcessor:
    job_type = "flood.zones.import"

    def run(self, session: Session, job: ProcessingJob) -> str | None:
        version, rows = _rows(session, job)
        columns = _columns(
            job, {"code": "code", "name": "name", "wkt": "wkt", "risk_class": "risk_class"}
        )
        session.query(FloodZone).filter(FloodZone.dataset_version_id == version.id).delete(
            synchronize_session=False
        )
        for number, row in enumerate(rows, start=2):
            code = row.get(columns["code"])
            name = row.get(columns["name"])
            wkt = row.get(columns["wkt"])
            if not code or not name or not wkt:
                raise ValueError(f"Flood zone code/name/wkt required at row {number}")
            session.add(
                FloodZone(
                    dataset_version_id=version.id,
                    code=code,
                    name=name,
                    geometry=WKTElement(wkt, srid=4326),
                    risk_class=row.get(columns["risk_class"]) or None,
                    methodology_version=None,
                )
            )
        session.flush()
        return f"flood-zones:{version.id}"


class TreeRegistryProcessor:
    job_type = "trees.registry.import"

    def run(self, session: Session, job: ProcessingJob) -> str | None:
        version, rows = _rows(session, job)
        columns = _columns(
            job,
            {
                "tree_code": "tree_code",
                "species_id": "species_id",
                "batch_id": "batch_id",
                "catchment_id": "catchment_id",
                "planted_on": "planted_on",
                "longitude": "longitude",
                "latitude": "latitude",
            },
        )
        session.query(Tree).filter(Tree.dataset_version_id == version.id).delete(
            synchronize_session=False
        )
        for number, row in enumerate(rows, start=2):
            tree_code = row.get(columns["tree_code"])
            if not tree_code:
                raise ValueError(f"tree_code required at row {number}")
            lon = _float(row.get(columns["longitude"]))
            lat = _float(row.get(columns["latitude"]))
            planted = row.get(columns["planted_on"])
            session.add(
                Tree(
                    dataset_version_id=version.id,
                    tree_code=tree_code,
                    species_id=_uuid(row.get(columns["species_id"])),
                    batch_id=_uuid(row.get(columns["batch_id"])),
                    catchment_id=_uuid(row.get(columns["catchment_id"])),
                    planted_on=_date(planted) if planted else None,
                    location=WKTElement(f"POINT({lon} {lat})", srid=4326)
                    if lon is not None and lat is not None
                    else None,
                    methodology_version=None,
                )
            )
        session.flush()
        return f"trees:{version.id}"


class TreeInspectionProcessor:
    job_type = "trees.inspections.import"

    def run(self, session: Session, job: ProcessingJob) -> str | None:
        version, rows = _rows(session, job)
        columns = _columns(
            job,
            {
                "tree_id": "tree_id",
                "inspected_at": "inspected_at",
                "status": "status",
                "height_m": "height_m",
                "diameter_cm": "diameter_cm",
                "notes": "notes",
            },
        )
        session.query(TreeInspection).filter(
            TreeInspection.dataset_version_id == version.id
        ).delete(synchronize_session=False)
        for number, row in enumerate(rows, start=2):
            tree_id = _uuid(row.get(columns["tree_id"]))
            inspected = row.get(columns["inspected_at"])
            status = row.get(columns["status"])
            if tree_id is None or not inspected or not status:
                raise ValueError(f"tree_id/inspected_at/status required at row {number}")
            session.add(
                TreeInspection(
                    dataset_version_id=version.id,
                    tree_id=tree_id,
                    inspected_at=_datetime(inspected),
                    status=status,
                    height_m=_float(row.get(columns["height_m"])),
                    diameter_cm=_float(row.get(columns["diameter_cm"])),
                    notes=row.get(columns["notes"]) or None,
                    methodology_version=None,
                )
            )
        session.flush()
        return f"tree-inspections:{version.id}"


class SocioEconomicProcessor:
    job_type = "vulnerability.socioeconomic.import"

    def run(self, session: Session, job: ProcessingJob) -> str | None:
        version, rows = _rows(session, job)
        columns = _columns(
            job,
            {
                "geographic_area_id": "geographic_area_id",
                "period_start": "period_start",
                "period_end": "period_end",
                "indicator_code": "indicator_code",
                "value": "value",
                "unit": "unit",
            },
        )
        session.query(SocioEconomicIndicator).filter(
            SocioEconomicIndicator.dataset_version_id == version.id
        ).delete(synchronize_session=False)
        for number, row in enumerate(rows, start=2):
            area = _uuid(row.get(columns["geographic_area_id"]))
            start = row.get(columns["period_start"])
            end = row.get(columns["period_end"])
            code = row.get(columns["indicator_code"])
            value = _float(row.get(columns["value"]))
            unit = row.get(columns["unit"])
            if area is None or not start or not end or not code or value is None or not unit:
                raise ValueError(f"Incomplete socio-economic indicator at row {number}")
            session.add(
                SocioEconomicIndicator(
                    dataset_version_id=version.id,
                    geographic_area_id=area,
                    period_start=_date(start),
                    period_end=_date(end),
                    indicator_code=code,
                    value=value,
                    unit=unit,
                    methodology_version=None,
                )
            )
        session.flush()
        return f"socioeconomic-indicators:{version.id}"


for processor in (
    WeatherObservationProcessor(),
    FloodIncidentProcessor(),
    FloodZoneProcessor(),
    TreeRegistryProcessor(),
    TreeInspectionProcessor(),
    SocioEconomicProcessor(),
):
    registry.register(processor)
