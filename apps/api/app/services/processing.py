from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Protocol

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.processing import ProcessingJob, ProcessingJobLog


class Processor(Protocol):
    job_type: str

    def run(self, session: Session, job: ProcessingJob) -> str | None: ...


class ProcessorRegistry:
    def __init__(self) -> None:
        self._items: dict[str, Processor] = {}

    def register(self, processor: Processor) -> None:
        self._items[processor.job_type] = processor

    def get(self, job_type: str) -> Processor:
        try:
            return self._items[job_type]
        except KeyError as exc:
            raise ValueError(f"Unknown processor: {job_type}") from exc


registry = ProcessorRegistry()


def log(
    session: Session,
    job: ProcessingJob,
    level: str,
    message: str,
    details: dict[str, object] | None = None,
) -> None:
    session.add(
        ProcessingJobLog(
            processing_job_id=job.id,
            level=level,
            message=message,
            details=details or {},
            created_at=datetime.now(UTC),
        )
    )


def create_job(
    session: Session,
    *,
    job_type: str,
    dataset_version_id: uuid.UUID | None,
    parameters: dict[str, object],
    idempotency_key: str,
    max_attempts: int = 3,
) -> ProcessingJob:
    existing = session.scalar(
        select(ProcessingJob).where(ProcessingJob.idempotency_key == idempotency_key)
    )
    if existing is not None:
        return existing
    job = ProcessingJob(
        job_type=job_type,
        dataset_version_id=dataset_version_id,
        parameters=parameters,
        idempotency_key=idempotency_key,
        max_attempts=max(1, max_attempts),
    )
    session.add(job)
    try:
        session.flush()
    except IntegrityError:
        session.rollback()
        existing = session.scalar(
            select(ProcessingJob).where(ProcessingJob.idempotency_key == idempotency_key)
        )
        if existing is None:
            raise
        return existing
    log(session, job, "INFO", "Processing job created.")
    return job


def enqueue(job: ProcessingJob) -> None:
    """Persisted PENDING status is the durable queue; workers poll with SKIP LOCKED."""
    return None


def execute_job(session: Session, job: ProcessingJob) -> ProcessingJob:
    if job.status == "SUCCEEDED":
        return job
    if job.attempts >= job.max_attempts:
        return job
    job.status = "RUNNING"
    job.started_at = datetime.now(UTC)
    job.attempts += 1
    job.error_message = None
    log(session, job, "INFO", "Processing attempt started.", {"attempt": job.attempts})
    session.commit()
    try:
        output = registry.get(job.job_type).run(session, job)
        job.status = "SUCCEEDED"
        job.stage = "PUBLISHED_OUTPUT"
        job.output_reference = output
        job.completed_at = datetime.now(UTC)
        log(session, job, "INFO", "Processing job completed.")
    except Exception as exc:
        job.status = "FAILED"
        job.error_message = str(exc)[:4000]
        job.completed_at = datetime.now(UTC)
        log(session, job, "ERROR", "Processing job failed.", {"error": job.error_message})
    session.commit()
    return job
