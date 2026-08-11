from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REQUIRED = [
    "apps/api/app/models/processing.py",
    "apps/api/app/models/climate.py",
    "apps/api/app/models/citizen.py",
    "apps/api/app/models/operations.py",
    "apps/api/app/models/outputs.py",
    "apps/api/app/services/processing.py",
    "apps/api/app/services/processors.py",
    "apps/api/app/services/reporting.py",
    "apps/api/app/api/v1/endpoints/roadmap.py",
    "apps/api/migrations/versions/20260811_0005_remaining_roadmap_schema.py",
    "services/worker/worker.py",
    "services/worker/Dockerfile",
    "apps/web/src/pages/DashboardsPage.tsx",
    "apps/web/src/pages/RoadmapModulePage.tsx",
    "infrastructure/scripts/backup-cram.sh",
    "infrastructure/scripts/restore-cram.sh",
]
missing = [item for item in REQUIRED if not (ROOT / item).is_file()]
if missing:
    raise SystemExit("Missing remaining-milestone code files:\n" + "\n".join(missing))
print(f"PASS: {len(REQUIRED)} required remaining-milestone code assets are present.")
