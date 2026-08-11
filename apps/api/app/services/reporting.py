from __future__ import annotations

import csv
import io
from datetime import UTC, datetime

from sqlalchemy.orm import Session

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
                "CSV is enabled by default. PDF/XLSX require approved templates/output requirements."
            )
        stream = io.StringIO()
        writer = csv.writer(stream)
        writer.writerow(["CRAM report type", report.report_type])
        writer.writerow(["Generated UTC", datetime.now(UTC).isoformat()])
        writer.writerow(["Parameters", report.parameters])
        writer.writerow(
            ["Source dataset versions", *[str(v) for v in report.source_dataset_version_ids]]
        )
        key = f"reports/{report.id}.csv"
        put_object(key=key, body=stream.getvalue().encode(), content_type="text/csv")
        report.file_reference = key
        report.status = "COMPLETED"
        report.completed_at = datetime.now(UTC)
        session.flush()
        return key


registry.register(ReportProcessor())
