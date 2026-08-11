from __future__ import annotations
import os, sys, time
sys.path.insert(0, os.getenv("CRAM_API_PATH","/app"))
from sqlalchemy import select
from app.db.session import get_session_factory
from app.models.processing import ProcessingJob
from app.services.processing import execute_job
import app.services.processors  # noqa: F401
import app.services.reporting  # noqa: F401

def main()->None:
    factory=get_session_factory()
    while True:
        with factory() as session:
            job=session.scalar(select(ProcessingJob).where(ProcessingJob.status=="PENDING").order_by(ProcessingJob.created_at).with_for_update(skip_locked=True))
            if job is None:
                session.rollback(); time.sleep(2); continue
            execute_job(session,job)
            if job.status=="FAILED" and job.attempts<job.max_attempts:
                job.status="PENDING"; session.commit()
        time.sleep(0.2)
if __name__=="__main__": main()
