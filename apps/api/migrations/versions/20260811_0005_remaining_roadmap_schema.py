"""Remaining roadmap schema foundations.

Revision ID: 20260811_0005
Revises: 20260811_0004

Scientific formulas, institutional policy, provider integrations, and production architecture are intentionally not encoded here; those remain governed by roadmap dependencies.
"""

from collections.abc import Sequence

from alembic import op

import app.models  # noqa: F401
from app.db.base import Base

revision: str = "20260811_0005"
down_revision: str | None = "20260811_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None
TABLES = [
    "processing_jobs",
    "processing_job_logs",
    "weather_observations",
    "heat_indicators",
    "flood_incidents",
    "flood_zones",
    "flood_risk_indicators",
    "tree_species",
    "tree_catchments",
    "tree_planting_batches",
    "trees",
    "tree_inspections",
    "socio_economic_indicators",
    "vulnerability_indicators",
    "citizen_reports",
    "citizen_report_attachments",
    "incident_assignments",
    "alerts",
    "notifications",
    "dashboard_definitions",
    "reports",
    "knowledge_items",
    "system_settings",
    "analytics_methodologies",
    "analytics_model_runs",
    "scenario_runs",
]


def upgrade() -> None:
    bind = op.get_bind()
    for name in TABLES:
        Base.metadata.tables[f"cram.{name}"].create(bind=bind, checkfirst=True)


def downgrade() -> None:
    bind = op.get_bind()
    for name in reversed(TABLES):
        Base.metadata.tables[f"cram.{name}"].drop(bind=bind, checkfirst=True)
