from __future__ import annotations

import os
import sys
import time
from datetime import UTC, datetime, timedelta

sys.path.insert(0, os.getenv("CRAM_API_PATH", "/app"))

from sqlalchemy import select  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from app.db.session import get_session_factory  # noqa: E402
from app.models.engineering import ProcessingSchedule  # noqa: E402
from app.models.processing import ProcessingJob  # noqa: E402
from app.services.processing import create_job, execute_job  # noqa: E402
import app.services.processors  # noqa: E402,F401
import app.services.reporting  # noqa: E402,F401

POLL_SECONDS = float(os.getenv("WORKER_POLL_SECONDS", "2"))
MAX_BACKOFF_SECONDS = int(os.getenv("WORKER_MAX_BACKOFF_SECONDS", "300"))


def enqueue_due_schedules(session: Session) -> int:
    now = datetime.now(UTC)
    rows = session.scalars(
        select(ProcessingSchedule)
        .where(ProcessingSchedule.is_active.is_(True), ProcessingSchedule.next_run_at <= now)
        .with_for_update(skip_locked=True)
    ).all()
    queued = 0
    for schedule in rows:
        key = f"schedule:{schedule.id}:{schedule.next_run_at.isoformat()}"
        create_job(
            session,
            job_type=schedule.job_type,
            dataset_version_id=schedule.dataset_version_id,
            parameters=schedule.parameters,
            idempotency_key=key,
        )
        schedule.last_run_at = now
        schedule.last_status = "QUEUED"
        schedule.next_run_at = now + timedelta(minutes=schedule.interval_minutes)
        queued += 1
    if queued:
        session.commit()
    return queued


def main() -> None:
    factory = get_session_factory()
    while True:
        with factory() as session:
            enqueue_due_schedules(session)
            job = session.scalar(
                select(ProcessingJob)
                .where(ProcessingJob.status == "PENDING")
                .order_by(ProcessingJob.created_at)
                .with_for_update(skip_locked=True)
            )
            if job is None:
                session.rollback()
                time.sleep(POLL_SECONDS)
                continue
            execute_job(session, job)
            if job.status == "FAILED" and job.attempts < job.max_attempts:
                delay = min(MAX_BACKOFF_SECONDS, 2 ** max(0, job.attempts - 1))
                job.status = "PENDING"
                session.commit()
                time.sleep(delay)
        time.sleep(0.2)


if __name__ == "__main__":
    main()
