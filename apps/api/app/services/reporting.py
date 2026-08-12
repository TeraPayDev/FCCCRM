from __future__ import annotations

import csv
import io
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.citizen import CitizenReport
from app.models.climate import (
    FloodIncident,
    FloodRiskIndicator,
    FloodZone,
    HeatIndicator,
    SocioEconomicIndicator,
    Tree,
    TreeInspection,
    VulnerabilityIndicator,
    WeatherObservation,
)
from app.models.data_management import Dataset, DatasetVersion
from app.models.outputs import Report
from app.models.processing import ProcessingJob
from app.services.object_storage import put_object
from app.services.processing import registry


class ReportProcessor:
    job_type = "report.generate"

    def run(self, session: Session, job: ProcessingJob) -> str | None:
        raw = job.parameters.get("report_id")
        if not raw:
            raise ValueError("report_id is required")
        import uuid

        report = session.get(Report, uuid.UUID(str(raw)))
        if report is None:
            raise ValueError("Report not found")
        fmt = str(job.parameters.get("format", "CSV")).upper()
        if fmt != "CSV":
            raise ValueError(
                "CSV is enabled by default. PDF/XLSX require approved templates/"
                "output requirements."
            )
        stream = io.StringIO()
        writer = csv.writer(stream)
        parameters = report.parameters or {}
        writer.writerow(["Climate Risk Analytics Management (CRAM) Report"])
        writer.writerow(
            ["Title", parameters.get("title", report.report_type.replace("_", " ").title())]
        )
        writer.writerow(["Report type", report.report_type])
        writer.writerow(["Generated UTC", datetime.now(UTC).isoformat()])
        writer.writerow(["Geography", parameters.get("geography", "Freetown")])
        writer.writerow(["Date from", parameters.get("date_from") or "Latest available"])
        writer.writerow(["Date to", parameters.get("date_to") or "Latest available"])
        modules = parameters.get("modules", [])
        writer.writerow(
            [
                "Included modules",
                ", ".join(str(item) for item in modules)
                if isinstance(modules, list)
                else str(modules),
            ]
        )
        writer.writerow([])
        writer.writerow(["Governed CRAM snapshot"])
        selected_modules = (
            set(str(item) for item in modules) if isinstance(modules, list) else set()
        )
        counts: list[tuple[str, Any]] = []
        if "heat" in selected_modules:
            counts.extend(
                [
                    ("Weather observations", WeatherObservation),
                    ("Approved heat indicators", HeatIndicator),
                ]
            )
        if "flood" in selected_modules:
            counts.extend(
                [
                    ("Flood incidents", FloodIncident),
                    ("Flood zones", FloodZone),
                    ("Flood risk indicators", FloodRiskIndicator),
                ]
            )
        if "trees" in selected_modules:
            counts.extend([("Trees", Tree), ("Tree inspections", TreeInspection)])
        if "vulnerability" in selected_modules:
            counts.extend(
                [
                    ("Socio-economic indicators", SocioEconomicIndicator),
                    ("Vulnerability indicators", VulnerabilityIndicator),
                ]
            )
        if "citizen reports" in selected_modules:
            counts.append(("Citizen hazard reports", CitizenReport))
        counts.extend([("Registered datasets", Dataset), ("Dataset versions", DatasetVersion)])
        for label, model in counts:
            count = session.scalar(select(func.count()).select_from(model)) or 0
            writer.writerow([label, count])
        writer.writerow([])
        writer.writerow(["Governance and provenance"])
        writer.writerow(["Report ID", str(report.id)])
        writer.writerow(["Requested by user ID", str(report.requested_by_user_id)])
        writer.writerow(
            ["Source dataset versions", *[str(v) for v in report.source_dataset_version_ids]]
        )
        writer.writerow([])
        writer.writerow(
            [
                "Generation note",
                "This export preserves report parameters and source-version provenance. "
                "Analytical values remain governed by their originating CRAM datasets "
                "and approved methodologies.",
            ]
        )
        key = f"reports/{report.id}.csv"
        put_object(key=key, body=stream.getvalue().encode(), content_type="text/csv")
        report.file_reference = key
        report.status = "COMPLETED"
        report.completed_at = datetime.now(UTC)
        session.flush()
        return key


registry.register(ReportProcessor())
