#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
API="${ROOT}/apps/api"
WEB="${ROOT}/apps/web"
cd "${ROOT}"

[[ -f .env ]] || { echo "ERROR: .env is required."; exit 1; }
set -a
# shellcheck disable=SC1091
source .env
set +a

: "${AUTH_JWT_SECRET:?AUTH_JWT_SECRET is required}"
: "${CRAM_BOOTSTRAP_ADMIN_PASSWORD:?CRAM_BOOTSTRAP_ADMIN_PASSWORD is required}"
: "${OBJECT_STORAGE_BUCKET:?OBJECT_STORAGE_BUCKET is required}"

printf '%s\n' \
  "============================================================" \
  "CRAM Milestones 9-12 - Data Platform Foundation" \
  "Catalogue + Ingestion + Validation + Approval/Publishing" \
  "Combined deploy and acceptance test" \
  "============================================================"

echo "==> 1/10 Backend quality"
cd "${API}"
uv sync --frozen
uv run ruff check app tests migrations --fix
uv run ruff format app tests migrations
uv run ruff check app tests migrations
uv run ruff format --check app tests migrations
uv run mypy app tests
uv run pytest

echo "==> 2/10 Frontend quality"
cd "${WEB}"
pnpm install --frozen-lockfile
pnpm format
pnpm quality
pnpm build

echo "==> 3/10 Rebuild and start platform services"
cd "${ROOT}"
docker compose build api web
docker compose up -d db redis geoserver object-storage api web

echo "==> 4/10 Apply data-platform migration and RBAC seed"
docker compose exec -T api uv run alembic upgrade head
docker compose exec -T api uv run python -m app.db.seed
docker compose exec -T \
  -e CRAM_BOOTSTRAP_ADMIN_PASSWORD="${CRAM_BOOTSTRAP_ADMIN_PASSWORD}" \
  api uv run python -c 'from app.db.seed import seed_development_admin; seed_development_admin()'

echo "==> 5/10 Prepare a permission-separated Data Steward acceptance user"
docker compose exec -T \
  -e CRAM_STEWARD_PASSWORD="Milestone9-12-Steward-Password-123!" \
  api uv run python - <<'PY'
import os
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.db.session import get_session_factory
from app.models.identity import Organisation, Role, User
from app.security.passwords import hash_password

factory = get_session_factory()
with factory() as session, session.begin():
    organisation = session.scalar(select(Organisation).where(Organisation.code == "FCC"))
    role = session.scalar(
        select(Role).options(selectinload(Role.permissions)).where(Role.code == "data_steward")
    )
    assert organisation is not None and role is not None
    user = session.scalar(select(User).where(User.username == "m912steward"))
    if user is None:
        user = User(
            username="m912steward",
            email="m912steward@development.local",
            organisation_id=organisation.id,
            password_hash=hash_password(os.environ["CRAM_STEWARD_PASSWORD"]),
            is_active=True,
        )
        session.add(user)
    user.password_hash = hash_password(os.environ["CRAM_STEWARD_PASSWORD"])
    user.organisation_id = organisation.id
    user.is_active = True
    user.roles = [role]
    session.flush()
    permissions = {permission.code for permission in role.permissions}
    assert {"datasets.read", "datasets.manage", "datasets.upload", "datasets.validate"} <= permissions
    assert "datasets.approve" not in permissions
    assert "datasets.publish" not in permissions
print("PASS: Data Steward has catalogue/upload/validation permissions without approve/publish.")
PY

echo "==> 6/10 Verify catalogue, source metadata, field definitions, and CSV ingestion"
docker compose exec -T \
  -e CRAM_ADMIN_PASSWORD="${CRAM_BOOTSTRAP_ADMIN_PASSWORD}" \
  -e CRAM_STEWARD_PASSWORD="Milestone9-12-Steward-Password-123!" \
  api uv run python - <<'PY'
import json
import os
import urllib.error
import urllib.parse
import urllib.request
import uuid

BASE = "http://localhost:8000/api/v1"


def json_request(path, *, token=None, body=None, method=None, expected=(200, 201, 202)):
    data = None if body is None else json.dumps(body).encode()
    headers = {"Accept": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if body is not None:
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(
        BASE + path,
        data=data,
        headers=headers,
        method=method or ("POST" if body is not None else "GET"),
    )
    try:
        with urllib.request.urlopen(request) as response:
            assert response.status in expected
            return json.loads(response.read().decode()) if response.status != 204 else None
    except urllib.error.HTTPError as exc:
        payload = exc.read().decode()
        if exc.code not in expected:
            raise AssertionError(f"{path}: unexpected HTTP {exc.code}: {payload}") from exc
        return {"status": exc.code, "payload": payload}


def raw_request(path, *, token, content, content_type="text/csv", expected=(200, 201)):
    request = urllib.request.Request(
        BASE + path,
        data=content,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": content_type,
            "Accept": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(request) as response:
        assert response.status in expected
        return json.loads(response.read().decode())


def binary_get(path, *, token):
    request = urllib.request.Request(
        BASE + path,
        headers={"Authorization": f"Bearer {token}"},
    )
    with urllib.request.urlopen(request) as response:
        assert response.status == 200
        return response.read()


admin = json_request(
    "/auth/login",
    body={"username": "cramadmin", "password": os.environ["CRAM_ADMIN_PASSWORD"]},
)["access_token"]
steward = json_request(
    "/auth/login",
    body={"username": "m912steward", "password": os.environ["CRAM_STEWARD_PASSWORD"]},
)["access_token"]
organisations = json_request("/organisations", token=admin)
fcc = next(item for item in organisations if item["code"] == "FCC")

suffix = uuid.uuid4().hex[:10]
dataset = json_request(
    "/datasets",
    token=steward,
    body={
        "code": f"M912-{suffix}",
        "name": "CRAM synthetic weather-like data-platform acceptance dataset",
        "description": "Synthetic acceptance data only; not an official SL-Met contract.",
        "owner_organisation_id": fcc["id"],
        "category": "weather-like acceptance",
        "sensitivity": "INTERNAL",
        "expected_format": "CSV",
        "update_frequency": "controlled acceptance run",
    },
)
source = json_request(
    f"/datasets/{dataset['id']}/sources",
    token=steward,
    body={
        "provider_organisation_id": fcc["id"],
        "name": "Synthetic acceptance CSV",
        "source_type": "FILE",
        "source_reference": "controlled synthetic fixture",
        "connection_secret_ref": "secret://cram/acceptance-placeholder",
        "update_method": "manual CSV upload",
    },
)
assert source["connection_secret_ref"].startswith("secret://")
assert "password" not in json.dumps(source).lower()

fields = [
    ("observed_at", "datetime", {"not_future": True, "unique": True}),
    ("station_code", "string", {}),
    ("temperature_c", "number", {"min": -20, "max": 60}),
    ("humidity_pct", "number", {"min": 0, "max": 100}),
    ("latitude", "number", {"semantic": "latitude"}),
    ("longitude", "number", {"semantic": "longitude"}),
]
for ordinal, (name, data_type, rules) in enumerate(fields):
    json_request(
        f"/datasets/{dataset['id']}/fields",
        token=steward,
        body={
            "name": name,
            "data_type": data_type,
            "ordinal": ordinal,
            "is_required": True,
            "validation_rules": rules,
        },
    )

invalid_csv = (
    b"observed_at,station_code,temperature_c,humidity_pct,latitude,longitude\n"
    b"2026-08-10T08:00:00Z,SYNTH-001,27.4,999,8.481,-13.231\n"
)
valid_csv = (
    b"observed_at,station_code,temperature_c,humidity_pct,latitude,longitude\n"
    b"2026-08-10T08:00:00Z,SYNTH-001,27.4,82,8.481,-13.231\n"
    b"2026-08-10T09:00:00Z,SYNTH-001,28.1,79,8.481,-13.231\n"
)

invalid_upload = raw_request(
    f"/datasets/{dataset['id']}/uploads?filename=invalid-weather.csv&source_id={source['id']}",
    token=steward,
    content=invalid_csv,
)
assert binary_get(
    f"/datasets/versions/{invalid_upload['dataset_version_id']}/download", token=steward
) == invalid_csv
invalid_run = json_request(
    f"/datasets/versions/{invalid_upload['dataset_version_id']}/validate",
    token=steward,
    method="POST",
)
assert invalid_run["status"] == "FAILED" and invalid_run["error_count"] >= 1
assert any(item["field_name"] == "humidity_pct" for item in invalid_run["errors"])
blocked = json_request(
    f"/datasets/versions/{invalid_upload['dataset_version_id']}/submit",
    token=steward,
    method="POST",
    expected=(409,),
)
assert blocked["status"] == 409

valid_upload = raw_request(
    f"/datasets/{dataset['id']}/uploads?filename=valid-weather.csv&source_id={source['id']}",
    token=steward,
    content=valid_csv,
)
assert binary_get(
    f"/datasets/versions/{valid_upload['dataset_version_id']}/download", token=steward
) == valid_csv
valid_run = json_request(
    f"/datasets/versions/{valid_upload['dataset_version_id']}/validate",
    token=steward,
    method="POST",
)
assert valid_run["status"] == "PASSED" and valid_run["error_count"] == 0
approval = json_request(
    f"/datasets/versions/{valid_upload['dataset_version_id']}/submit",
    token=steward,
    method="POST",
)

# Permission separation: Data Steward cannot approve or publish.
for path in (
    f"/datasets/approvals/{approval['id']}/approve",
    f"/datasets/versions/{valid_upload['dataset_version_id']}/publish",
):
    denied = json_request(path, token=steward, body={"comments": "must be denied"} if "approve" in path else None, method="POST", expected=(403,))
    assert denied["status"] == 403

approved = json_request(
    f"/datasets/approvals/{approval['id']}/approve",
    token=admin,
    body={"comments": "Synthetic acceptance version approved."},
)
assert approved["status"] == "APPROVED"
published = json_request(
    f"/datasets/versions/{valid_upload['dataset_version_id']}/publish",
    token=admin,
    method="POST",
)
assert published["status"] == "PUBLISHED"
versions = json_request(f"/datasets/{dataset['id']}/versions", token=steward)
assert any(item["status"] == "PUBLISHED" for item in versions)
page = json_request(f"/datasets?q={urllib.parse.quote(dataset['code'])}", token=steward)
assert page["total"] >= 1 and page["items"][0]["owner_organisation_id"] == fcc["id"]

print("PASS: catalogue, original CSV preservation, versioning, validation, approval and publication verified.")
print(f"ACCEPTANCE_DATASET_ID={dataset['id']}")
PY

echo "==> 7/10 Verify validation registry and background-capable execution contract"
docker compose exec -T api uv run python - <<'PY'
from app.services.validation import VALIDATION_RULE_REGISTRY
required = {
    "required_column", "required_value", "max_null_fraction", "data_type", "min", "max",
    "not_future", "unique", "latitude", "longitude", "geometry_wkt",
    "containment_area_code", "duplicate_record",
}
assert required <= set(VALIDATION_RULE_REGISTRY)
print("PASS: reusable schema/completeness/numeric/temporal/geospatial/duplicate validation registry verified.")
PY

echo "==> 8/10 Verify audit trail and version-status history"
docker compose exec -T api uv run python - <<'PY'
from sqlalchemy import func, select
from app.db.session import get_session_factory
from app.models.audit import AuditLog
from app.models.data_management import DatasetVersionStatusHistory
factory = get_session_factory()
with factory() as session:
    actions = set(session.scalars(select(AuditLog.action).where(AuditLog.action.like("dataset.%"))).all())
    required = {"dataset.create", "dataset.upload", "dataset.validation.complete", "dataset.approval.submit", "dataset.approval.approve", "dataset.publish"}
    assert required <= actions
    history_count = session.scalar(select(func.count()).select_from(DatasetVersionStatusHistory)) or 0
    assert history_count >= 6
print("PASS: data-governance actions are audited and version status history is persisted.")
PY

echo "==> 9/10 Verify migration head and data-platform tables"
docker compose exec -T api uv run alembic current | grep -q '20260811_0004 (head)'
docker compose exec -T db psql -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" -Atc \
  "SELECT count(*) FROM information_schema.tables WHERE table_schema='cram' AND table_name IN ('data_validation_runs','validation_errors','approvals','dataset_version_status_history');" | grep -q '^4$'
echo "PASS: migration 20260811_0004 and all four data-platform governance tables verified."

echo "==> 10/10 Final state"
docker compose exec -T api uv run alembic current
docker compose ps
printf '%s\n' \
  "============================================================" \
  "MILESTONES 9 + 10 + 11 + 12 LOCAL ACCEPTANCE PASSED" \
  "Data catalogue:  http://10.1.11.7:3000/datasets" \
  "Approval queue:  http://10.1.11.7:3000/approvals" \
  "============================================================"
