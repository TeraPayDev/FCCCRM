#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
API_DIR="${ROOT_DIR}/apps/api"
TEMP_DB="cram_m4_acceptance"

cd "${ROOT_DIR}"

echo "============================================================"
echo "CRAM Milestone 4 - Core Database Foundation"
echo "Combined deploy and acceptance test"
echo "============================================================"

[[ -f ".env" ]] || { echo "ERROR: .env is required."; exit 1; }

echo "==> 1/9 Update backend lockfile and dependencies"
cd "${API_DIR}"
uv lock
uv sync

echo "==> 2/9 Run backend quality checks"
uv run ruff format app tests migrations
uv run ruff check app tests migrations
uv run ruff format --check app tests migrations
uv run mypy app tests
uv run pytest

echo "==> 3/9 Rebuild and start API/database containers"
cd "${ROOT_DIR}"
docker compose build api
docker compose up -d db api

echo "==> 4/9 Apply migration to development database"
docker compose exec -T api uv run alembic upgrade head

echo "==> 5/9 Apply safe seed data"
docker compose exec -T api uv run python -m app.db.seed

echo "==> 6/9 Verify development database foundation"
docker compose exec -T api uv run python -m app.db.verify_foundation

echo "==> 7/9 Create temporary fresh database"
docker compose exec -T db psql -U cram -d postgres -v ON_ERROR_STOP=1 \
  -c "DROP DATABASE IF EXISTS ${TEMP_DB} WITH (FORCE);"
docker compose exec -T db psql -U cram -d postgres -v ON_ERROR_STOP=1 \
  -c "CREATE DATABASE ${TEMP_DB};"

LIVE_URL="$(docker compose exec -T api printenv DATABASE_URL | tr -d '\r')"
TEMP_URL="${LIVE_URL%/*}/${TEMP_DB}"

cleanup() {
  docker compose exec -T db psql -U cram -d postgres \
    -c "DROP DATABASE IF EXISTS ${TEMP_DB} WITH (FORCE);" >/dev/null 2>&1 || true
}
trap cleanup EXIT

echo "==> 8/9 Fresh migration, verification, rollback, re-upgrade"
docker compose exec -T -e ALEMBIC_DATABASE_URL="${TEMP_URL}" api uv run alembic upgrade head
docker compose exec -T -e DATABASE_URL="${TEMP_URL}" api uv run python -m app.db.verify_foundation
docker compose exec -T -e ALEMBIC_DATABASE_URL="${TEMP_URL}" api uv run alembic downgrade base
docker compose exec -T -e ALEMBIC_DATABASE_URL="${TEMP_URL}" api uv run alembic upgrade head
docker compose exec -T -e DATABASE_URL="${TEMP_URL}" api uv run python -m app.db.verify_foundation

echo "==> 9/9 Display migration and seed state"
docker compose exec -T api uv run alembic current
docker compose exec -T db psql -U cram -d cram -c \
  "SELECT 'organisations' AS item, count(*) FROM cram.organisations
   UNION ALL SELECT 'roles', count(*) FROM cram.roles;"

echo "============================================================"
echo "MILESTONE 4 LOCAL ACCEPTANCE PASSED"
echo "============================================================"
