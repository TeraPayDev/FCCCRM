#!/usr/bin/env bash
set -euo pipefail

# CRAM Milestone 2 - Local Infrastructure Verification
# Runs only the infrastructure checks required by the Milestone 2 baseline.

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${ROOT_DIR}"

echo "==> Docker Compose service status"
docker compose ps

echo
echo "==> PostgreSQL/PostGIS"
docker compose exec -T api uv run python - <<'PY'
import os
import psycopg

database_url = os.environ["DATABASE_URL"]
if database_url.startswith("postgresql+psycopg://"):
    database_url = "postgresql://" + database_url.removeprefix("postgresql+psycopg://")

with psycopg.connect(database_url) as conn:
    with conn.cursor() as cur:
        cur.execute("SELECT current_database(), current_user, PostGIS_Version();")
        print(cur.fetchone())
PY

echo
echo "==> Redis"
docker compose exec -T redis redis-cli ping

echo
echo "==> Object storage from API container"
docker compose exec -T api uv run python - <<'PY'
import os
import boto3

s3 = boto3.client(
    "s3",
    endpoint_url=os.environ["OBJECT_STORAGE_ENDPOINT"],
    aws_access_key_id=os.environ["OBJECT_STORAGE_ACCESS_KEY"],
    aws_secret_access_key=os.environ["OBJECT_STORAGE_SECRET_KEY"],
    region_name=os.environ.get("OBJECT_STORAGE_REGION", "us-east-1"),
)
print([bucket["Name"] for bucket in s3.list_buckets().get("Buckets", [])])
PY

echo
echo "Local infrastructure verification completed."
