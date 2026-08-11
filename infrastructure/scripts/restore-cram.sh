#!/usr/bin/env bash
set -euo pipefail
: "${POSTGRES_DB:?required}" "${POSTGRES_USER:?required}"
file="${1:?usage: restore-cram.sh BACKUP.dump}"
test -s "$file"
if [[ -f "$file.sha256" ]]; then sha256sum -c "$file.sha256"; fi
cat "$file" | docker compose exec -T db pg_restore -U "$POSTGRES_USER" -d "$POSTGRES_DB" --clean --if-exists --no-owner --no-acl
