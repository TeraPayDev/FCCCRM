#!/usr/bin/env bash
set -euo pipefail
: "${POSTGRES_DB:?required}" "${POSTGRES_USER:?required}"
out="${1:-/opt/cram/backups/cram-$(date -u +%Y%m%dT%H%M%SZ).dump}"
mkdir -p "$(dirname "$out")"
docker compose exec -T db pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" --format=custom --no-owner --no-acl > "$out"
test -s "$out"
sha256sum "$out" > "$out.sha256"
echo "$out"
