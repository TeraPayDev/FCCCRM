from __future__ import annotations

import csv
import io
from datetime import UTC, datetime

from sqlalchemy import delete, select, text
from sqlalchemy.orm import Session

from app.models.data_management import (
    DatasetField,
    DatasetUpload,
    DatasetVersion,
    DataValidationRun,
    ValidationError,
)
from app.models.identity import User
from app.services.audit import record_audit_event
from app.services.lifecycle import transition_version
from app.services.object_storage import get_object

VALIDATION_RULE_REGISTRY: dict[str, str] = {
    "required_column": "Required dataset field must exist in the CSV header.",
    "required_value": "Required field values must not be blank.",
    "max_null_fraction": "Configured maximum blank-value fraction for a field.",
    "data_type": "Field value must parse as the configured data type.",
    "min": "Numeric value must be greater than or equal to the configured minimum.",
    "max": "Numeric value must be less than or equal to the configured maximum.",
    "not_future": "Configured temporal values must not be in the future.",
    "unique": "Configured field values must be unique within the uploaded version.",
    "latitude": "Latitude must be between -90 and 90.",
    "longitude": "Longitude must be between -180 and 180.",
    "geometry_wkt": "WKT geometry must be valid in the configured SRID.",
    "containment_area_code": "Geometry must fall within the configured CRAM geographic area.",
    "duplicate_record": "Duplicate complete CSV rows are reported as warnings.",
}


class ValidationServiceError(ValueError):
    pass


def create_validation_run(
    session: Session,
    *,
    version: DatasetVersion,
    execution_mode: str,
) -> DataValidationRun:
    if version.status not in {"UPLOADED", "VALIDATION_FAILED", "VALIDATED"}:
        raise ValidationServiceError("Dataset version is not ready for validation.")

    run = DataValidationRun(
        dataset_version_id=version.id,
        status="PENDING",
        execution_mode=execution_mode,
    )

    session.add(run)
    session.flush()

    return run


def _value_excerpt(value: str) -> str:
    return value[:500]


def _add_issue(
    session: Session,
    *,
    run: DataValidationRun,
    severity: str,
    rule_code: str,
    message: str,
    row_number: int | None = None,
    field_name: str | None = None,
    value: str | None = None,
) -> None:
    session.add(
        ValidationError(
            validation_run_id=run.id,
            row_number=row_number,
            field_name=field_name,
            rule_code=rule_code,
            severity=severity,
            message=message,
            value_excerpt=_value_excerpt(value) if value is not None else None,
        )
    )

    if severity == "ERROR":
        run.error_count += 1
    else:
        run.warning_count += 1


def _parse_type(value: str, data_type: str) -> bool:
    if value == "":
        return True

    normalized = data_type.lower()

    try:
        if normalized in {"integer", "int"}:
            int(value)

        elif normalized in {"number", "float", "decimal"}:
            float(value)

        elif normalized in {"boolean", "bool"}:
            if value.strip().lower() not in {
                "true",
                "false",
                "1",
                "0",
                "yes",
                "no",
            }:
                return False

        elif normalized in {"date", "datetime", "timestamp"}:
            datetime.fromisoformat(value.replace("Z", "+00:00"))

    except ValueError:
        return False

    return True


def execute_validation(
    session: Session,
    *,
    run: DataValidationRun,
    actor: User | None,
) -> DataValidationRun:
    version = session.get(
        DatasetVersion,
        run.dataset_version_id,
    )

    if version is None:
        raise ValidationServiceError("Dataset version not found.")

    upload = session.scalar(
        select(DatasetUpload).where(DatasetUpload.dataset_version_id == version.id)
    )

    if upload is None:
        raise ValidationServiceError("Dataset version has no uploaded source file.")

    fields = list(
        session.scalars(
            select(DatasetField)
            .where(DatasetField.dataset_id == version.dataset_id)
            .order_by(DatasetField.ordinal)
        ).all()
    )

    session.execute(delete(ValidationError).where(ValidationError.validation_run_id == run.id))

    run.status = "RUNNING"
    run.started_at = datetime.now(UTC)
    run.error_count = 0
    run.warning_count = 0

    transition_version(
        session,
        version,
        to_status="VALIDATING",
        actor=actor,
    )

    raw = get_object(upload.object_key)

    try:
        decoded_text = raw.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValidationServiceError("CSV must be UTF-8 encoded.") from exc

    reader = csv.DictReader(io.StringIO(decoded_text))

    headers = reader.fieldnames or []
    expected = {field.name for field in fields}

    for field in fields:
        if field.is_required and field.name not in headers:
            _add_issue(
                session,
                run=run,
                severity="ERROR",
                rule_code="required_column",
                message=(f"Required column '{field.name}' is missing."),
                field_name=field.name,
            )

    for unexpected in sorted(set(headers) - expected):
        _add_issue(
            session,
            run=run,
            severity="WARNING",
            rule_code="unexpected_column",
            message=(f"Unexpected column '{unexpected}' is present."),
            field_name=unexpected,
        )

    seen_rows: set[tuple[str, ...]] = set()

    unique_values: dict[
        str,
        set[str],
    ] = {field.name: set() for field in fields}

    null_counts: dict[
        str,
        int,
    ] = {field.name: 0 for field in fields}

    rows = list(reader)
    run.total_rows = len(rows)

    for row_index, row in enumerate(
        rows,
        start=2,
    ):
        signature = tuple(row.get(header, "") or "" for header in headers)

        if signature in seen_rows:
            _add_issue(
                session,
                run=run,
                severity="WARNING",
                rule_code="duplicate_record",
                message="Duplicate record detected.",
                row_number=row_index,
            )

        seen_rows.add(signature)

        for field in fields:
            value = (row.get(field.name) or "").strip()

            rules = field.validation_rules

            if not value:
                null_counts[field.name] += 1

            if field.is_required and not value:
                _add_issue(
                    session,
                    run=run,
                    severity="ERROR",
                    rule_code="required_value",
                    message=("Required value is missing."),
                    row_number=row_index,
                    field_name=field.name,
                )
                continue

            if value and not _parse_type(
                value,
                field.data_type,
            ):
                _add_issue(
                    session,
                    run=run,
                    severity="ERROR",
                    rule_code="data_type",
                    message=(f"Value cannot be parsed as {field.data_type}."),
                    row_number=row_index,
                    field_name=field.name,
                    value=value,
                )
                continue

            if value and rules.get("unique") is True:
                if value in unique_values[field.name]:
                    _add_issue(
                        session,
                        run=run,
                        severity="ERROR",
                        rule_code="unique",
                        message=("Duplicate field value is not allowed by this dataset rule."),
                        row_number=row_index,
                        field_name=field.name,
                        value=value,
                    )

                unique_values[field.name].add(value)

            if value and field.data_type.lower() in {
                "number",
                "float",
                "decimal",
                "integer",
                "int",
            }:
                number = float(value)

                minimum = rules.get("min")
                maximum = rules.get("max")

                if isinstance(
                    minimum,
                    int | float,
                ) and number < float(minimum):
                    _add_issue(
                        session,
                        run=run,
                        severity="ERROR",
                        rule_code="minimum",
                        message=(f"Value is below configured minimum {minimum}."),
                        row_number=row_index,
                        field_name=field.name,
                        value=value,
                    )

                if isinstance(
                    maximum,
                    int | float,
                ) and number > float(maximum):
                    _add_issue(
                        session,
                        run=run,
                        severity="ERROR",
                        rule_code="maximum",
                        message=(f"Value is above configured maximum {maximum}."),
                        row_number=row_index,
                        field_name=field.name,
                        value=value,
                    )

                semantic = rules.get("semantic")

                if semantic == "latitude" and not -90 <= number <= 90:
                    _add_issue(
                        session,
                        run=run,
                        severity="ERROR",
                        rule_code=("latitude_range"),
                        message=("Latitude must be between -90 and 90."),
                        row_number=row_index,
                        field_name=field.name,
                        value=value,
                    )

                if semantic == "longitude" and not -180 <= number <= 180:
                    _add_issue(
                        session,
                        run=run,
                        severity="ERROR",
                        rule_code=("longitude_range"),
                        message=("Longitude must be between -180 and 180."),
                        row_number=row_index,
                        field_name=field.name,
                        value=value,
                    )

            if value and field.data_type.lower() == "geometry_wkt":
                srid = rules.get("srid")

                if not isinstance(
                    srid,
                    int,
                ):
                    _add_issue(
                        session,
                        run=run,
                        severity="ERROR",
                        rule_code="geometry_wkt",
                        message=("geometry_wkt fields require an integer SRID validation rule."),
                        row_number=row_index,
                        field_name=field.name,
                    )

                else:
                    valid = session.scalar(
                        text("SELECT ST_IsValid(ST_GeomFromText(:wkt, :srid))"),
                        {
                            "wkt": value,
                            "srid": srid,
                        },
                    )

                    if valid is not True:
                        _add_issue(
                            session,
                            run=run,
                            severity="ERROR",
                            rule_code=("geometry_wkt"),
                            message=("Geometry is invalid for the configured SRID."),
                            row_number=row_index,
                            field_name=field.name,
                            value=value,
                        )

                    containment_code = rules.get("containment_area_code")

                    if (
                        isinstance(
                            containment_code,
                            str,
                        )
                        and valid is True
                    ):
                        contained = session.scalar(
                            text(
                                "SELECT EXISTS ("
                                "SELECT 1 FROM "
                                "cram.geographic_areas "
                                "WHERE code=:code "
                                "AND ST_Within("
                                "ST_GeomFromText("
                                ":wkt,:srid"
                                "), geometry"
                                ")"
                                ")"
                            ),
                            {
                                "code": (containment_code),
                                "wkt": value,
                                "srid": srid,
                            },
                        )

                        if contained is not True:
                            _add_issue(
                                session,
                                run=run,
                                severity="ERROR",
                                rule_code=("containment_area_code"),
                                message=(
                                    "Geometry is "
                                    "outside the "
                                    "configured "
                                    "geographic "
                                    "containment area."
                                ),
                                row_number=row_index,
                                field_name=field.name,
                                value=value,
                            )

            if (
                value
                and rules.get("not_future") is True
                and field.data_type.lower()
                in {
                    "date",
                    "datetime",
                    "timestamp",
                }
            ):
                parsed = datetime.fromisoformat(
                    value.replace(
                        "Z",
                        "+00:00",
                    )
                )

                if parsed.tzinfo is None:
                    parsed = parsed.replace(tzinfo=UTC)

                if parsed > datetime.now(UTC):
                    _add_issue(
                        session,
                        run=run,
                        severity="ERROR",
                        rule_code=("future_timestamp"),
                        message=("Future timestamp is not allowed by this dataset rule."),
                        row_number=row_index,
                        field_name=field.name,
                        value=value,
                    )

    if run.total_rows > 0:
        for field in fields:
            threshold = field.validation_rules.get("max_null_fraction")

            if isinstance(
                threshold,
                int | float,
            ):
                fraction = null_counts[field.name] / run.total_rows

                if fraction > float(threshold):
                    _add_issue(
                        session,
                        run=run,
                        severity="ERROR",
                        rule_code=("max_null_fraction"),
                        message=(
                            "Blank-value fraction "
                            f"{fraction:.3f} "
                            "exceeds configured "
                            "maximum "
                            f"{threshold}."
                        ),
                        field_name=field.name,
                    )

    run.completed_at = datetime.now(UTC)

    run.status = "PASSED" if run.error_count == 0 else "FAILED"

    version.row_count = run.total_rows

    transition_version(
        session,
        version,
        to_status=("VALIDATED" if run.error_count == 0 else "VALIDATION_FAILED"),
        actor=actor,
    )

    record_audit_event(
        session,
        action=("dataset.validation.complete"),
        resource_type=("dataset_version"),
        resource_id=version.id,
        actor=actor,
        details={
            "validation_run_id": str(run.id),
            "status": run.status,
            "rows": run.total_rows,
            "errors": run.error_count,
            "warnings": run.warning_count,
        },
    )

    session.flush()

    return run
