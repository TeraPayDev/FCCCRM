#!/usr/bin/env bash
set -euo pipefail

# CRAM Milestone 2 - Development Bootstrap
# Purpose:
#   - Verify the local Docker infrastructure is running.
#   - Verify PostgreSQL/PostGIS from inside the API container.
#   - Ensure the configured development object-storage bucket exists.
#
# This script intentionally does NOT create application/domain tables,
# users, roles, climate records, or other later-milestone data.

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${ROOT_DIR}"

if [[ ! -f ".env" ]]; then
  echo "ERROR: ${ROOT_DIR}/.env does not exist."
  echo "Create it from .env.example before running this script."
  exit 1
fi

echo "==> Starting CRAM local infrastructure"
docker compose up -d

echo "==> Waiting for required containers to report healthy"

required_services=("db" "redis" "object-storage" "api" "web" "geoserver")

for service in "${required_services[@]}"; do
  container_id="$(docker compose ps -q "${service}")"

  if [[ -z "${container_id}" ]]; then
    echo "ERROR: service '${service}' has no running container."
    exit 1
  fi

  for _ in $(seq 1 30); do
    status="$(docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' "${container_id}")"

    if [[ "${status}" == "healthy" || "${status}" == "running" ]]; then
      break
    fi

    sleep 2
  done

  status="$(docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' "${container_id}")"

  if [[ "${status}" != "healthy" && "${status}" != "running" ]]; then
    echo "ERROR: service '${service}' did not become ready. Current state: ${status}"
    docker compose ps
    exit 1
  fi

  echo "    ${service}: ${status}"
done

echo "==> Verifying API -> PostgreSQL/PostGIS connectivity"
docker compose exec -T api uv run python - <<'PY'
import os
from urllib.parse import urlparse

import psycopg

database_url = os.environ["DATABASE_URL"]

# psycopg does not use SQLAlchemy's postgresql+psycopg scheme.
if database_url.startswith("postgresql+psycopg://"):
    database_url = "postgresql://" + database_url.removeprefix("postgresql+psycopg://")

with psycopg.connect(database_url) as conn:
    with conn.cursor() as cur:
        cur.execute("SELECT current_database(), current_user, PostGIS_Version();")
        database, user, postgis_version = cur.fetchone()

print(f"    database={database}")
print(f"    user={user}")
print(f"    postgis={postgis_version}")
PY

echo "==> Ensuring configured development object-storage bucket exists"
docker compose exec -T api uv run python - <<'PY'
import os

import boto3
from botocore.exceptions import ClientError

endpoint = os.environ["OBJECT_STORAGE_ENDPOINT"]
access_key = os.environ["OBJECT_STORAGE_ACCESS_KEY"]
secret_key = os.environ["OBJECT_STORAGE_SECRET_KEY"]
bucket = os.environ["OBJECT_STORAGE_BUCKET"]
region = os.environ.get("OBJECT_STORAGE_REGION", "us-east-1")

s3 = boto3.client(
    "s3",
    endpoint_url=endpoint,
    aws_access_key_id=access_key,
    aws_secret_access_key=secret_key,
    region_name=region,
)

try:
    s3.head_bucket(Bucket=bucket)
    print(f"    bucket '{bucket}' already exists")
except ClientError as exc:
    error_code = str(exc.response.get("Error", {}).get("Code", ""))
    http_status = exc.response.get("ResponseMetadata", {}).get("HTTPStatusCode")

    if http_status == 404 or error_code in {"404", "NoSuchBucket", "NotFound"}:
        s3.create_bucket(Bucket=bucket)
        print(f"    created bucket '{bucket}'")
    else:
        raise

response = s3.list_buckets()
bucket_names = [item["Name"] for item in response.get("Buckets", [])]

if bucket not in bucket_names:
    raise RuntimeError(f"Configured bucket '{bucket}' was not returned by list_buckets().")

print(f"    verified bucket '{bucket}'")
PY

echo
echo "CRAM development bootstrap completed successfully."
