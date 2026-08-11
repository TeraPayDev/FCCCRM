from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.data_management import Approval, DatasetVersion, DatasetVersionStatusHistory
from app.models.identity import User
from app.services.audit import record_audit_event


class LifecycleError(ValueError):
    pass


def _history(
    session: Session,
    version: DatasetVersion,
    *,
    to_status: str,
    actor: User | None,
    comment: str | None = None,
) -> None:
    previous = version.status
    version.status = to_status
    if to_status == "PUBLISHED":
        version.published_at = datetime.now(UTC)
    session.add(
        DatasetVersionStatusHistory(
            dataset_version_id=version.id,
            from_status=previous,
            to_status=to_status,
            changed_by_user_id=actor.id if actor else None,
            comment=comment,
        )
    )


def transition_version(
    session: Session,
    version: DatasetVersion,
    *,
    to_status: str,
    actor: User | None,
    comment: str | None = None,
) -> None:
    previous = version.status
    _history(session, version, to_status=to_status, actor=actor, comment=comment)
    record_audit_event(
        session,
        action=f"dataset.version.{to_status.lower()}",
        resource_type="dataset_version",
        resource_id=version.id,
        actor=actor,
        details={"from_status": previous, "to_status": to_status, "comment": comment},
    )


def submit_for_approval(session: Session, version: DatasetVersion, actor: User) -> Approval:
    if version.status != "VALIDATED":
        raise LifecycleError("Only a validated dataset version can be submitted for approval.")
    existing = session.scalar(select(Approval).where(Approval.dataset_version_id == version.id))
    if existing is not None:
        raise LifecycleError("This dataset version already has an approval record.")
    approval = Approval(
        dataset_version_id=version.id, submitted_by_user_id=actor.id, status="PENDING"
    )
    session.add(approval)
    _history(session, version, to_status="PENDING_APPROVAL", actor=actor)
    record_audit_event(
        session,
        action="dataset.approval.submit",
        resource_type="dataset_version",
        resource_id=version.id,
        actor=actor,
    )
    session.flush()
    return approval


def decide_approval(
    session: Session,
    approval: Approval,
    *,
    actor: User,
    approve: bool,
    comments: str | None,
) -> Approval:
    if approval.status != "PENDING":
        raise LifecycleError("Approval has already been decided.")
    version = session.get(DatasetVersion, approval.dataset_version_id)
    if version is None:
        raise LifecycleError("Dataset version not found.")
    approval.status = "APPROVED" if approve else "REJECTED"
    approval.reviewed_by_user_id = actor.id
    approval.reviewed_at = datetime.now(UTC)
    approval.comments = comments
    _history(
        session,
        version,
        to_status="APPROVED" if approve else "REJECTED",
        actor=actor,
        comment=comments,
    )
    record_audit_event(
        session,
        action="dataset.approval.approve" if approve else "dataset.approval.reject",
        resource_type="dataset_version",
        resource_id=version.id,
        actor=actor,
        details={"comments": comments},
    )
    session.flush()
    return approval


def publish_version(session: Session, version: DatasetVersion, actor: User) -> DatasetVersion:
    if version.status != "APPROVED":
        raise LifecycleError("Only an approved dataset version can be published.")
    _history(session, version, to_status="PUBLISHED", actor=actor)
    record_audit_event(
        session,
        action="dataset.publish",
        resource_type="dataset_version",
        resource_id=version.id,
        actor=actor,
    )
    session.flush()
    return version
