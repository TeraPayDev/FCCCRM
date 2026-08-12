from __future__ import annotations

import hashlib
import re
import uuid
from pathlib import PurePath

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.data_management import (
    Dataset,
    DatasetField,
    DatasetSource,
    DatasetUpload,
    DatasetVersion,
)
from app.models.identity import User
from app.services.audit import record_audit_event
from app.services.csv_schema import CsvSchemaError, infer_csv_schema
from app.services.lifecycle import transition_version
from app.services.object_storage import put_object

MAX_UPLOAD_BYTES = 10 * 1024 * 1024
CSV_MIME_TYPES = {"text/csv", "application/csv", "application/vnd.ms-excel", "text/plain"}


class UploadValidationError(ValueError):
    pass


def _types_compatible(configured: str, inferred: str) -> bool:
    configured = configured.lower()
    inferred = inferred.lower()
    if configured == inferred:
        return True
    if configured in {"number", "float", "decimal"} and inferred == "integer":
        return True
    if configured == "string":
        return True
    return False


def ensure_csv_schema(session: Session, *, dataset: Dataset, content: bytes) -> int:
    try:
        inferred, row_count = infer_csv_schema(content)
    except CsvSchemaError as exc:
        raise UploadValidationError(str(exc)) from exc
    existing = list(
        session.scalars(
            select(DatasetField)
            .where(DatasetField.dataset_id == dataset.id)
            .order_by(DatasetField.ordinal)
        ).all()
    )

    if not existing:
        for inferred_field in inferred:
            session.add(DatasetField(dataset_id=dataset.id, **inferred_field))
        session.flush()
        return row_count

    inferred_by_name = {str(inferred_field["name"]): inferred_field for inferred_field in inferred}
    missing = [
        existing_field.name
        for existing_field in existing
        if existing_field.is_required and existing_field.name not in inferred_by_name
    ]
    if missing:
        raise UploadValidationError(
            "CSV is missing required configured columns: " + ", ".join(sorted(missing)) + "."
        )

    conflicts: list[str] = []
    for existing_field in existing:
        detected = inferred_by_name.get(existing_field.name)
        if detected is None:
            continue
        inferred_type = str(detected["data_type"])
        if not _types_compatible(existing_field.data_type, inferred_type):
            conflicts.append(
                f"{existing_field.name} "
                f"({existing_field.data_type} configured, {inferred_type} detected)"
            )

    if conflicts:
        raise UploadValidationError(
            "CSV schema conflicts with the configured dataset schema: " + "; ".join(conflicts) + "."
        )

    existing_names = {existing_field.name for existing_field in existing}
    for inferred_field in inferred:
        if str(inferred_field["name"]) not in existing_names:
            session.add(DatasetField(dataset_id=dataset.id, **inferred_field))
    session.flush()
    return row_count


def safe_filename(filename: str) -> str:
    basename = PurePath(filename).name
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", basename).strip("._")
    if not cleaned:
        raise UploadValidationError("Filename is invalid.")
    return cleaned[:180]


def create_csv_upload(
    session: Session,
    *,
    dataset: Dataset,
    source_id: uuid.UUID | None,
    actor: User,
    filename: str,
    content_type: str,
    content: bytes,
) -> tuple[DatasetVersion, DatasetUpload]:
    if not content:
        raise UploadValidationError("Uploaded file is empty.")
    if len(content) > MAX_UPLOAD_BYTES:
        raise UploadValidationError("Uploaded file exceeds the 10 MiB development limit.")
    cleaned = safe_filename(filename)
    if not cleaned.lower().endswith(".csv"):
        raise UploadValidationError(
            "Only CSV uploads are supported in the generic ingestion milestone."
        )
    if source_id is not None:
        source = session.get(DatasetSource, source_id)
        if source is None or source.dataset_id != dataset.id:
            raise UploadValidationError("Selected dataset source does not belong to this dataset.")

    normalized_type = content_type.split(";", 1)[0].strip().lower()
    if normalized_type not in CSV_MIME_TYPES:
        raise UploadValidationError("Unsupported CSV content type.")

    row_count = ensure_csv_schema(session, dataset=dataset, content=content)

    next_version = (
        int(
            session.scalar(
                select(func.coalesce(func.max(DatasetVersion.version_number), 0)).where(
                    DatasetVersion.dataset_id == dataset.id
                )
            )
            or 0
        )
        + 1
    )
    checksum = hashlib.sha256(content).hexdigest()
    version = DatasetVersion(
        dataset_id=dataset.id,
        source_id=source_id,
        version_number=next_version,
        status="DRAFT",
        checksum_sha256=checksum,
        row_count=row_count,
    )
    session.add(version)
    session.flush()
    object_key = f"datasets/{dataset.id}/versions/{version.id}/{cleaned}"
    put_object(key=object_key, body=content, content_type=normalized_type)
    upload = DatasetUpload(
        dataset_version_id=version.id,
        uploaded_by_user_id=actor.id,
        object_key=object_key,
        original_filename=cleaned,
        mime_type=normalized_type,
        size_bytes=len(content),
        checksum_sha256=checksum,
    )
    session.add(upload)
    transition_version(session, version, to_status="UPLOADED", actor=actor)
    record_audit_event(
        session,
        action="dataset.upload",
        resource_type="dataset_version",
        resource_id=version.id,
        actor=actor,
        organisation_id=dataset.owner_organisation_id,
        details={
            "filename": cleaned,
            "size_bytes": len(content),
            "checksum_sha256": checksum,
            "source_id": str(source_id) if source_id else None,
        },
    )
    session.flush()
    return version, upload
