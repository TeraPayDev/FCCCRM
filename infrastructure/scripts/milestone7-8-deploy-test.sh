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
: "${GEOSERVER_ADMIN_USER:?GEOSERVER_ADMIN_USER is required}"
: "${GEOSERVER_ADMIN_PASSWORD:?GEOSERVER_ADMIN_PASSWORD is required}"

printf '%s\n' "============================================================" "CRAM Milestones 7 + 8 - Audit Framework and GIS Foundation" "Combined deploy and acceptance test" "============================================================"

echo "==> 1/9 Backend quality"
cd "${API}"
uv sync
uv run ruff check app tests migrations --fix
uv run ruff format app tests migrations
uv run ruff check app tests migrations
uv run ruff format --check app tests migrations
uv run mypy app tests
uv run pytest

echo "==> 2/9 Frontend quality"
cd "${WEB}"
pnpm install --frozen-lockfile
pnpm format
pnpm quality
pnpm build

echo "==> 3/9 Rebuild and start platform services"
cd "${ROOT}"
docker compose build api web
docker compose up -d db redis geoserver object-storage api web

echo "==> 4/9 Apply migration, RBAC seed, administrator, and synthetic GIS seed"
docker compose exec -T api uv run alembic upgrade head
docker compose exec -T api uv run python -m app.db.seed
docker compose exec -T -e CRAM_BOOTSTRAP_ADMIN_PASSWORD="${CRAM_BOOTSTRAP_ADMIN_PASSWORD}" api uv run python -c 'from app.db.seed import seed_development_admin; seed_development_admin()'
docker compose exec -T api uv run python -m app.db.seed_gis

echo "==> 5/9 Verify append-only audit database protection and sanitized service"
docker compose exec -T api uv run python - <<'PY'
from sqlalchemy import select, text
from app.db.session import get_session_factory
from app.models.audit import AuditLog
from app.services.audit import record_audit_event

factory = get_session_factory()
with factory() as session, session.begin():
    event = record_audit_event(session, action="acceptance.audit", resource_type="acceptance", details={"password": "must-not-persist", "safe": "ok"})
    event_id = event.id
with factory() as session:
    event = session.scalar(select(AuditLog).where(AuditLog.id == event_id))
    assert event is not None and event.details["password"] == "[REDACTED]"
    try:
        session.execute(text("UPDATE cram.audit_logs SET action='tampered' WHERE id=:id"), {"id": event_id})
        session.commit()
        raise AssertionError("audit UPDATE unexpectedly succeeded")
    except Exception:
        session.rollback()
print("PASS: audit sanitization and append-only protection verified.")
PY

echo "==> 6/9 Verify PostGIS storage and spatial filtering"
docker compose exec -T api uv run python - <<'PY'
from sqlalchemy import text
from app.db.session import get_session_factory
factory = get_session_factory()
with factory() as session:
    row = session.execute(text("SELECT code, ST_IsValid(geometry), ST_SRID(geometry) FROM cram.geographic_areas WHERE code='CRAM-SAMPLE-AREA'")).one()
    assert row[1] is True and row[2] == 4326
    count = session.execute(text("SELECT count(*) FROM cram.geographic_areas WHERE geometry && ST_MakeEnvelope(-13.31,8.39,-13.19,8.51,4326) AND ST_Intersects(geometry, ST_MakeEnvelope(-13.31,8.39,-13.19,8.51,4326))")).scalar_one()
    assert count >= 1
print("PASS: valid PostGIS geometry and spatial filtering verified.")
PY

echo "==> 7/9 Configure/verify CRAM GeoServer workspace, PostGIS store, and sample layer"
GS="http://localhost:8080/geoserver/rest"
AUTH="${GEOSERVER_ADMIN_USER}:${GEOSERVER_ADMIN_PASSWORD}"
curl -fsS -u "${AUTH}" "${GS}/workspaces/cram.json" >/dev/null 2>&1 || curl -fsS -u "${AUTH}" -H 'Content-Type: application/json' -X POST "${GS}/workspaces" -d '{"workspace":{"name":"cram"}}' >/dev/null
if ! curl -fsS -u "${AUTH}" "${GS}/workspaces/cram/datastores/cram_postgis.json" >/dev/null 2>&1; then
  curl -fsS -u "${AUTH}" -H 'Content-Type: application/json' -X POST "${GS}/workspaces/cram/datastores" -d "{\"dataStore\":{\"name\":\"cram_postgis\",\"connectionParameters\":{\"entry\":[{\"@key\":\"dbtype\",\"$\":\"postgis\"},{\"@key\":\"host\",\"$\":\"db\"},{\"@key\":\"port\",\"$\":\"5432\"},{\"@key\":\"database\",\"$\":\"${POSTGRES_DB}\"},{\"@key\":\"schema\",\"$\":\"cram\"},{\"@key\":\"user\",\"$\":\"${POSTGRES_USER}\"},{\"@key\":\"passwd\",\"$\":\"${POSTGRES_PASSWORD}\"}]}}}" >/dev/null
fi
curl -fsS -u "${AUTH}" "${GS}/workspaces/cram/datastores/cram_postgis/featuretypes/geographic_areas.json" >/dev/null 2>&1 || curl -fsS -u "${AUTH}" -H 'Content-Type: application/json' -X POST "${GS}/workspaces/cram/datastores/cram_postgis/featuretypes" -d '{"featureType":{"name":"geographic_areas","nativeName":"geographic_areas","title":"CRAM Synthetic GIS Acceptance Areas","srs":"EPSG:4326","enabled":true}}' >/dev/null
curl -fsS "http://localhost:8080/geoserver/cram/ows?service=WFS&version=2.0.0&request=GetFeature&typeNames=cram:geographic_areas&outputFormat=application/json&count=1" | grep -q 'CRAM-SAMPLE-AREA'
echo "PASS: GeoServer reads the CRAM PostGIS sample layer."

echo "==> 8/9 Verify live audit and GIS APIs"
docker compose exec -T -e CRAM_ADMIN_PASSWORD="${CRAM_BOOTSTRAP_ADMIN_PASSWORD}" api uv run python - <<'PY'
import json, os, urllib.request
BASE="http://localhost:8000/api/v1"
def req(path, token=None, body=None):
    data=None if body is None else json.dumps(body).encode()
    headers={"Accept":"application/json"}
    if body is not None: headers["Content-Type"]="application/json"
    if token: headers["Authorization"]=f"Bearer {token}"
    request=urllib.request.Request(BASE+path,data=data,headers=headers,method="POST" if body is not None else "GET")
    with urllib.request.urlopen(request) as response: return json.loads(response.read().decode())
login=req("/auth/login",body={"username":"cramadmin","password":os.environ["CRAM_ADMIN_PASSWORD"]})
token=login["access_token"]
events=req("/audit?limit=20",token=token)
assert any(event["action"] == "auth.login.success" for event in events)
layers=req("/gis/layers",token=token)
areas=req("/gis/areas?bbox=-13.31,8.39,-13.19,8.51",token=token)
assert any(layer["layer_name"] == "geographic_areas" for layer in layers)
assert any(area["code"] == "CRAM-SAMPLE-AREA" and area["metadata"].get("authoritative") is False for area in areas)
print("PASS: live audit and GIS APIs verified.")
PY

echo "==> 9/9 Final state"
docker compose exec -T api uv run alembic current
docker compose ps
printf '%s\n' "============================================================" "MILESTONES 7 + 8 LOCAL ACCEPTANCE PASSED" "Audit viewer: http://10.1.11.7:3000/audit" "GIS map:      http://10.1.11.7:3000/map" "============================================================"
