#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
API="${ROOT}/apps/api"
WEB="${ROOT}/apps/web"

cd "${ROOT}"

echo "============================================================"
echo "CRAM Milestone 5 - Identity, Authentication and RBAC"
echo "Combined deploy and acceptance test"
echo "============================================================"

if [[ ! -f .env ]]; then
  echo "ERROR: .env is required."
  exit 1
fi

if ! grep -q '^CRAM_BOOTSTRAP_ADMIN_PASSWORD=' .env; then
  ADMIN_PASSWORD="$(python3 - <<'PY'
import secrets
print("M5-" + secrets.token_urlsafe(24))
PY
)"
  printf '\nCRAM_BOOTSTRAP_ADMIN_PASSWORD=%s\n' "${ADMIN_PASSWORD}" >> .env
else
  ADMIN_PASSWORD="$(grep '^CRAM_BOOTSTRAP_ADMIN_PASSWORD=' .env | tail -1 | cut -d= -f2-)"
fi

if ! grep -q '^AUTH_JWT_SECRET=' .env; then
  JWT_SECRET="$(python3 - <<'PY'
import secrets
print(secrets.token_urlsafe(48))
PY
)"
  printf 'AUTH_JWT_SECRET=%s\n' "${JWT_SECRET}" >> .env
else
  JWT_SECRET="$(grep '^AUTH_JWT_SECRET=' .env | tail -1 | cut -d= -f2-)"
fi

echo
echo "==> 1/8 Update backend lockfile and run backend quality"
cd "${API}"
uv lock
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
pnpm install
pnpm format
pnpm quality
pnpm build

echo
echo "==> 3/8 Rebuild and start API/web/database"
cd "${ROOT}"
docker compose build api web
docker compose up -d db api web

echo
echo "==> 4/8 Apply identity migration and RBAC seed matrix"
docker compose exec -T -e AUTH_JWT_SECRET="${JWT_SECRET}" api uv run alembic upgrade head
docker compose exec -T -e AUTH_JWT_SECRET="${JWT_SECRET}" api uv run python -m app.db.seed
docker compose exec -T -e AUTH_JWT_SECRET="${JWT_SECRET}" \
  -e CRAM_BOOTSTRAP_ADMIN_PASSWORD="${ADMIN_PASSWORD}" \
  api uv run python -c "from app.db.seed import seed_development_admin; seed_development_admin(); print('Development admin ready.')"

echo
echo "==> 5/8 Run database-backed authentication/RBAC tests"
docker compose run --rm -T --no-deps \
  -v "${API}/tests:/app/tests:ro" \
  -e APP_ENV=testing \
  -e AUTH_JWT_SECRET="${JWT_SECRET}" \
  -e RUN_DB_INTEGRATION=1 \
  api uv run pytest tests/test_auth_integration.py

echo
echo "==> 6/8 Verify login/current-user/permission endpoint from API container"
LOGIN_JSON="$(docker compose exec -T -e CRAM_ADMIN_PASSWORD="${ADMIN_PASSWORD}" api uv run python - <<'PY'
import json, os, urllib.request
payload=json.dumps({"username":"cramadmin","password":os.environ["CRAM_ADMIN_PASSWORD"]}).encode()
request=urllib.request.Request(
    "http://localhost:8000/api/v1/auth/login",
    data=payload,
    headers={"Content-Type":"application/json"},
    method="POST",
)
print(urllib.request.urlopen(request).read().decode())
PY
)"
ACCESS_TOKEN="$(python3 -c 'import json,sys; print(json.loads(sys.stdin.read())["access_token"])' <<< "${LOGIN_JSON}")"

docker compose exec -T -e CRAM_ACCESS_TOKEN="${ACCESS_TOKEN}" api uv run python - <<'PY'
import os, urllib.request
request=urllib.request.Request(
    "http://localhost:8000/api/v1/auth/me",
    headers={"Authorization": "Bearer " + os.environ["CRAM_ACCESS_TOKEN"]},
)
print(urllib.request.urlopen(request).read().decode())
PY

echo
echo "==> 7/8 Verify migration rollback/re-upgrade on temporary database"
TEMP_DB="cram_m5_acceptance"
docker compose exec -T db psql -U cram -d postgres -c "DROP DATABASE IF EXISTS ${TEMP_DB} WITH (FORCE);"
docker compose exec -T db psql -U cram -d postgres -c "CREATE DATABASE ${TEMP_DB};"
LIVE_URL="$(docker compose exec -T api printenv DATABASE_URL | tr -d '\r')"
TEMP_URL="${LIVE_URL%/*}/${TEMP_DB}"
docker compose exec -T -e ALEMBIC_DATABASE_URL="${TEMP_URL}" -e AUTH_JWT_SECRET="${JWT_SECRET}" api uv run alembic upgrade head
docker compose exec -T -e DATABASE_URL="${TEMP_URL}" -e AUTH_JWT_SECRET="${JWT_SECRET}" api uv run python -m app.db.seed
docker compose exec -T -e ALEMBIC_DATABASE_URL="${TEMP_URL}" -e AUTH_JWT_SECRET="${JWT_SECRET}" api uv run alembic downgrade 20260810_0001
docker compose exec -T -e ALEMBIC_DATABASE_URL="${TEMP_URL}" -e AUTH_JWT_SECRET="${JWT_SECRET}" api uv run alembic upgrade head
docker compose exec -T db psql -U cram -d postgres -c "DROP DATABASE IF EXISTS ${TEMP_DB} WITH (FORCE);"

echo
echo "==> 8/8 Final state"
docker compose exec -T api uv run alembic current
docker compose ps

echo
echo "============================================================"
echo "MILESTONE 5 LOCAL ACCEPTANCE PASSED"
echo "============================================================"
echo "Development login:"
echo "  URL:      http://10.1.11.7:3000/login"
echo "  Username: cramadmin"
echo "  Password: stored in ignored .env as CRAM_BOOTSTRAP_ADMIN_PASSWORD"
echo
echo "Verified:"
echo "  - login, refresh, logout and current-user API"
echo "  - permission-based dependency (not role-name authorization)"
echo "  - positive and negative authorization tests"
echo "  - invalid credentials and expired token rejection"
echo "  - account disabled/temporary lock framework"
echo "  - RBAC seed matrix v0.1"
echo "  - authentication UI"
echo "  - Milestone 5 migration rollback/re-upgrade"
