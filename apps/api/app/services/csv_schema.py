from __future__ import annotations

import csv
import io
import re
from typing import TypedDict


class CsvSchemaError(ValueError):
    pass


class CsvSchemaField(TypedDict):
    name: str
    data_type: str
    ordinal: int
    is_required: bool
    validation_rules: dict[str, object]


def _infer_value_type(values: list[str]) -> str:
    populated = [value.strip() for value in values if value.strip()]
    if not populated:
        return "string"
    if all(re.fullmatch(r"[-+]?\d+", value) for value in populated):
        return "integer"
    try:
        for value in populated:
            float(value)
        return "number"
    except ValueError:
        return "string"


def infer_csv_schema(content: bytes) -> tuple[list[CsvSchemaField], int]:
    try:
        decoded = content.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise CsvSchemaError("CSV must be UTF-8 encoded.") from exc

    reader = csv.reader(io.StringIO(decoded))
    try:
        headers = [header.strip() for header in next(reader)]
    except StopIteration as exc:
        raise CsvSchemaError("Uploaded CSV has no header row.") from exc

    if not headers or any(not header for header in headers):
        raise CsvSchemaError("Every CSV column must have a header.")
    if len(set(headers)) != len(headers):
        raise CsvSchemaError("CSV headers must be unique.")

    rows = list(reader)
    sample = rows[:500]
    fields: list[CsvSchemaField] = []
    for ordinal, name in enumerate(headers):
        values = [row[ordinal] if ordinal < len(row) else "" for row in sample]
        all_values = [row[ordinal] if ordinal < len(row) else "" for row in rows]
        fields.append(
            {
                "name": name,
                "data_type": _infer_value_type(values),
                "ordinal": ordinal,
                "is_required": bool(rows) and all(value.strip() for value in all_values),
                "validation_rules": {"inferred_from_csv": True},
            }
        )
    return fields, len(rows)
