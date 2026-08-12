from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.models.engineering import IntegrationConnector, IntegrationRun
from app.models.processing import ProcessingJob
from app.services.processing import registry
from app.services.public_data import PublicDataError, run_public_connector


class PublicConnectorProcessor:
    job_type = "PUBLIC_CONNECTOR_SYNC"

    def run(self, session: Session, job: ProcessingJob) -> str | None:
        raw_id = job.parameters.get("connector_id")
        if not isinstance(raw_id, str):
            raise ValueError("PUBLIC_CONNECTOR_SYNC requires connector_id.")
        connector = session.get(IntegrationConnector, uuid.UUID(raw_id))
        if connector is None:
            raise ValueError("Integration connector not found.")
        started = datetime.now(UTC)
        try:
            result = run_public_connector(connector.connector_type)
            count = result.get("record_count", 0)
            records_received = int(count) if isinstance(count, (int, float, str)) else 0
            run = IntegrationRun(
                connector_id=connector.id,
                status="SUCCEEDED",
                records_received=records_received,
                started_at=started,
                completed_at=datetime.now(UTC),
                run_metadata={
                    "source": result.get("source"),
                    "retrieved_at": result.get("retrieved_at"),
                    "governance": result.get("governance"),
                },
            )
            session.add(run)
            session.flush()
            return f"integration-run:{run.id}"
        except PublicDataError as exc:
            session.add(
                IntegrationRun(
                    connector_id=connector.id,
                    status="FAILED",
                    records_received=0,
                    started_at=started,
                    completed_at=datetime.now(UTC),
                    error_message=str(exc)[:4000],
                    run_metadata={"source": connector.institution},
                )
            )
            session.flush()
            raise


registry.register(PublicConnectorProcessor())
