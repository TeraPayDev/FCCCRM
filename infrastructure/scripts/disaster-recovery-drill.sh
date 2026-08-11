#!/usr/bin/env bash
set -euo pipefail
ROOT="${CRAM_ROOT:-/opt/cram/source/cram-platform}"
BACKUP_DIR="${CRAM_BACKUP_DIR:-/opt/cram/backups}"
cd "$ROOT"
echo "=== CRAM DISASTER-RECOVERY DRILL ==="
./infrastructure/scripts/backup-cram.sh
latest="$(find "$BACKUP_DIR" -maxdepth 1 -type f -printf '%T@ %p\n' 2>/dev/null | sort -nr | head -1 | cut -d' ' -f2-)"
if [[ -z "${latest:-}" ]]; then echo "FAIL: no backup artifact found"; exit 1; fi
echo "PASS: backup artifact created: $latest"
echo "Restore is intentionally not executed against the active database. Use restore-cram.sh in an isolated acceptance environment."
