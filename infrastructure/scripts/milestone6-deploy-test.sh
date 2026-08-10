#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
API="${ROOT}/apps/api"
WEB="${ROOT}/apps/web"

cd "${ROOT}"

echo "============================================================"
echo "CRAM Milestone 6 - Organisations and Institutional Ownership"
echo "Combined deploy and acceptance test"
echo "============================================================"

if [[ ! -f .env ]]; then
  echo "ERROR: .env is required."
  exit 1
fi

ADMIN_PASSWORD="$(grep '^CRAM_BOOTSTRAP_ADMIN_PASSWORD=' .env | tail -1 | cut -d= -f2-)"
JWT_SECRET="$(grep '^AUTH_JWT_SECRET=' .env | tail -1 | cut -d= -f2-)"

if [[ -z "${ADMIN_PASSWORD}" || -z "${JWT_SECRET}" ]]; then
  echo "ERROR: Milestone 5 authentication settings are missing from .env."
  exit 1
fi

echo
echo "==> 1/8 Run backend quality"
cd "${API}"
uv sync
uv run ruff check app tests migrations --fix
uv run ruff format app tests migrations
uv run ruff check app tests migrations
uv run ruff format --check app tests migrations
uv run mypy app tests
uv run pytest

echo
echo "==> 2/8 Run frontend quality"
cd "${WEB}"
pnpm install --frozen-lockfile
pnpm format
pnpm quality
pnpm build

echo
echo "==> 3/8 Rebuild and start API/web/database"
cd "${ROOT}"
docker compose build api web
docker compose up -d db api web

echo
echo "==> 4/8 Re-apply controlled institution seed and development administrator"
docker compose exec -T -e AUTH_JWT_SECRET="${JWT_SECRET}" api uv run python -m app.db.seed
docker compose exec -T \
  -e AUTH_JWT_SECRET="${JWT_SECRET}" \
  -e CRAM_BOOTSTRAP_ADMIN_PASSWORD="${ADMIN_PASSWORD}" \
  api uv run python -c "from app.db.seed import seed_development_admin; seed_development_admin(); print('Development admin ready.')"

echo
echo "==> 5/8 Run database-backed organisation acceptance tests"
docker compose run --rm -T --no-deps \
  -v "${API}/tests:/app/tests:ro" \
  -e APP_ENV=testing \
  -e AUTH_JWT_SECRET="${JWT_SECRET}" \
  -e RUN_DB_INTEGRATION=1 \
  api uv run pytest tests/test_organisations_integration.py tests/test_organisation_scope.py

echo
echo "==> 6/8 Verify live organisation administration and user assignment API"
docker compose exec -T \
  -e CRAM_ADMIN_PASSWORD="${ADMIN_PASSWORD}" \
  api uv run python - <<'PY'
import json
import os
import urllib.error
import urllib.request

BASE = "http://localhost:8000/api/v1"


def request(path: str, *, method: str = "GET", token: str | None = None, body: object | None = None):
    data = None if body is None else json.dumps(body).encode()
    headers = {"Accept": "application/json"}
    if body is not None:
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(BASE + path, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req) as response:
        raw = response.read().decode()
        return None if not raw else json.loads(raw)


login = request(
    "/auth/login",
    method="POST",
    body={"username": "cramadmin", "password": os.environ["CRAM_ADMIN_PASSWORD"]},
)
token = login["access_token"]
organisations = request("/organisations", token=token)
codes = {item["code"] for item in organisations}
required = {"FCC", "NaCSA", "NDMA", "SL-Met", "Stats-SL", "ONS"}
assert required <= codes, (required - codes)

for existing in organisations:
    if existing["code"] == "M6-ACCEPT":
        try:
            request(f"/organisations/{existing['id']}", method="DELETE", token=token)
        except urllib.error.HTTPError:
            pass

created = request(
    "/organisations",
    method="POST",
    token=token,
    body={"code": "M6-ACCEPT", "name": "Milestone 6 Acceptance Institution"},
)
updated = request(
    f"/organisations/{created['id']}",
    method="PATCH",
    token=token,
    body={"name": "Milestone 6 Acceptance Partner"},
)
assert updated["name"] == "Milestone 6 Acceptance Partner"

users = request("/organisations/users", token=token)
admin = next(item for item in users if item["username"] == "cramadmin")
fcc = next(item for item in organisations if item["code"] == "FCC")
assigned = request(
    f"/organisations/users/{admin['id']}",
    method="PATCH",
    token=token,
    body={"organisation_id": created["id"]},
)
assert assigned["organisation_id"] == created["id"]
restored = request(
    f"/organisations/users/{admin['id']}",
    method="PATCH",
    token=token,
    body={"organisation_id": fcc["id"]},
)
assert restored["organisation_id"] == fcc["id"]
request(f"/organisations/{created['id']}", method="DELETE", token=token)
print("PASS: live organisation CRUD and user institutional assignment verified.")
PY

echo
echo "==> 7/8 Verify dataset owner/provider links and organisation-boundary helper"
docker compose exec -T -e AUTH_JWT_SECRET="${JWT_SECRET}" api uv run python - <<'PY'
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.db.session import get_session_factory
from app.models.data_management import Dataset, DatasetSource
from app.models.identity import Organisation, Role, User
from app.services.organisation_scope import organisation_scope_allows

factory = get_session_factory()
with factory() as session, session.begin():
    previous = session.scalar(select(Dataset).where(Dataset.code == "M6-LIVE-OWNERSHIP"))
    if previous is not None:
        session.delete(previous)
        session.flush()

    fcc = session.scalar(select(Organisation).where(Organisation.code == "FCC"))
    slmet = session.scalar(select(Organisation).where(Organisation.code == "SL-Met"))
    admin = session.scalar(
        select(User)
        .options(selectinload(User.roles).selectinload(Role.permissions))
        .where(User.username == "cramadmin")
    )
    assert fcc is not None and slmet is not None and admin is not None

    dataset = Dataset(
        code="M6-LIVE-OWNERSHIP",
        name="Milestone 6 Live Ownership Verification",
        owner_organisation_id=fcc.id,
    )
    session.add(dataset)
    session.flush()
    source = DatasetSource(
        dataset_id=dataset.id,
        provider_organisation_id=slmet.id,
        name="SL-Met Ownership Verification",
        source_type="file",
    )
    session.add(source)
    session.flush()

    assert dataset.owner_organisation_id == fcc.id
    assert source.provider_organisation_id == slmet.id
    assert organisation_scope_allows(
        admin,
        permission_code="datasets.manage",
        resource_organisation_id=fcc.id,
    )
    assert not organisation_scope_allows(
        admin,
        permission_code="datasets.manage",
        resource_organisation_id=slmet.id,
    )
    session.delete(dataset)

print("PASS: dataset owner, source provider, and organisation-boundary logic verified.")
PY

echo
echo "==> 8/8 Final state"
docker compose exec -T api uv run alembic current
docker compose ps

echo
echo "============================================================"
echo "MILESTONE 6 LOCAL ACCEPTANCE PASSED"
echo "============================================================"
echo "Organisation administration UI: http://10.1.11.7:3000/organisations"
echo
echo "Verified:"
echo "  - FCC, NaCSA, NDMA, SL-Met, Statistics Sierra Leone and ONS seed set"
echo "  - organisation list/create/read/update/delete management"
echo "  - user-to-organisation assignment and removal capability"
echo "  - dataset owner organisation and dataset-source provider organisation"
echo "  - permission-based organisation administration (no role-name authorization)"
echo "  - reusable organisation-boundary helper for future review/approval logic"
echo "  - organisation administration UI"
echo "  - existing migration head remains valid; no Milestone 6 schema migration was required"
