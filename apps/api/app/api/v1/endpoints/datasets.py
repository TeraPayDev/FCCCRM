from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    HTTPException,
    Query,
    Request,
    Response,
    status,
)
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db_session, get_session_factory
from app.models.data_management import (
    Approval,
    DatasetUpload,
    DatasetVersion,
    DatasetVersionStatusHistory,
    DataValidationRun,
    ValidationError,
)
from app.models.identity import User
from app.schemas.datasets import (
    ApprovalAction,
    ApprovalResponse,
    DatasetCreate,
    DatasetFieldCreate,
    DatasetFieldResponse,
    DatasetPage,
    DatasetResponse,
    DatasetSourceCreate,
    DatasetSourceResponse,
    DatasetUpdate,
    DatasetUploadResponse,
    DatasetVersionResponse,
    ValidationErrorResponse,
    ValidationRunResponse,
    VersionStatusHistoryResponse,
)
from app.security.dependencies import require_permission
from app.services.audit import record_audit_event
from app.services.catalogue import (
    DatasetConflictError,
    DatasetNotFoundError,
    create_dataset,
    create_field,
    create_source,
    get_dataset,
    list_datasets,
    list_fields,
    list_sources,
    list_versions,
    update_dataset,
)
from app.services.ingestion import UploadValidationError, create_csv_upload
from app.services.lifecycle import (
    LifecycleError,
    decide_approval,
    publish_version,
    submit_for_approval,
)
from app.services.object_storage import get_object
from app.services.validation import (
    VALIDATION_RULE_REGISTRY,
    ValidationServiceError,
    create_validation_run,
    execute_validation,
)

router = APIRouter(prefix="/datasets", tags=["datasets"])

DatasetReader = Annotated[User, Depends(require_permission("datasets.read"))]
DatasetManager = Annotated[User, Depends(require_permission("datasets.manage"))]
DatasetUploader = Annotated[User, Depends(require_permission("datasets.upload"))]
DatasetValidator = Annotated[User, Depends(require_permission("datasets.validate"))]
DatasetApprover = Annotated[User, Depends(require_permission("datasets.approve"))]
DatasetPublisher = Annotated[User, Depends(require_permission("datasets.publish"))]

OffsetParam = Annotated[int, Query(ge=0)]
LimitParam = Annotated[int, Query(ge=1, le=200)]
DatasetStatusParam = Annotated[str | None, Query(alias="status")]
FilenameParam = Annotated[str, Query(min_length=1, max_length=255)]


def _dataset_response(item: object) -> DatasetResponse:
    return DatasetResponse.model_validate(item, from_attributes=True)


def _source_response(item: object) -> DatasetSourceResponse:
    return DatasetSourceResponse.model_validate(item, from_attributes=True)


def _field_response(item: object) -> DatasetFieldResponse:
    return DatasetFieldResponse.model_validate(item, from_attributes=True)


def _version_response(item: object) -> DatasetVersionResponse:
    return DatasetVersionResponse.model_validate(item, from_attributes=True)


def _upload_response(item: object) -> DatasetUploadResponse:
    return DatasetUploadResponse.model_validate(item, from_attributes=True)


def _approval_response(item: object) -> ApprovalResponse:
    return ApprovalResponse.model_validate(item, from_attributes=True)


def _validation_response(session: Session, run: DataValidationRun) -> ValidationRunResponse:
    errors = list(
        session.scalars(
            select(ValidationError)
            .where(ValidationError.validation_run_id == run.id)
            .order_by(ValidationError.created_at, ValidationError.row_number)
        ).all()
    )
    payload = ValidationRunResponse.model_validate(run, from_attributes=True)
    payload.errors = [
        ValidationErrorResponse.model_validate(item, from_attributes=True) for item in errors
    ]
    return payload


def _background_validate(run_id: uuid.UUID, actor_id: uuid.UUID) -> None:
    factory = get_session_factory()
    with factory() as session, session.begin():
        run = session.get(DataValidationRun, run_id)
        actor = session.get(User, actor_id)
        if run is None:
            return
        try:
            execute_validation(session, run=run, actor=actor)
        except Exception:
            run.status = "FAILED"
            raise


@router.get("/validation-rules", response_model=dict[str, str])
def validation_rule_registry(_: DatasetReader) -> dict[str, str]:
    return VALIDATION_RULE_REGISTRY


@router.get("", response_model=DatasetPage)
def datasets_list(
    _: DatasetReader,
    offset: OffsetParam = 0,
    limit: LimitParam = 50,
    owner_organisation_id: uuid.UUID | None = None,
    category: str | None = None,
    dataset_status: DatasetStatusParam = None,
    q: str | None = None,
) -> DatasetPage:
    session = get_db_session()
    try:
        items, total = list_datasets(
            session,
            offset=offset,
            limit=limit,
            owner_organisation_id=owner_organisation_id,
            category=category,
            status=dataset_status,
            query_text=q,
        )
        return DatasetPage(
            items=[_dataset_response(item) for item in items],
            total=total,
            offset=offset,
            limit=limit,
        )
    finally:
        session.close()


@router.post("", response_model=DatasetResponse, status_code=status.HTTP_201_CREATED)
def dataset_create(payload: DatasetCreate, actor: DatasetManager) -> DatasetResponse:
    session = get_db_session()
    try:
        try:
            item = create_dataset(session, **payload.model_dump())
            record_audit_event(
                session,
                action="dataset.create",
                resource_type="dataset",
                resource_id=item.id,
                actor=actor,
                organisation_id=item.owner_organisation_id,
                details={"code": item.code, "name": item.name},
            )
            session.commit()
            return _dataset_response(item)
        except DatasetConflictError as exc:
            session.rollback()
            raise HTTPException(status_code=409, detail=str(exc)) from exc
    finally:
        session.close()


@router.get("/approvals", response_model=list[ApprovalResponse])
def approvals_list(_: DatasetApprover) -> list[ApprovalResponse]:
    session = get_db_session()
    try:
        items = list(session.scalars(select(Approval).order_by(Approval.submitted_at.desc())).all())
        return [_approval_response(item) for item in items]
    finally:
        session.close()


@router.get("/{dataset_id}", response_model=DatasetResponse)
def dataset_detail(dataset_id: uuid.UUID, _: DatasetReader) -> DatasetResponse:
    session = get_db_session()
    try:
        try:
            return _dataset_response(get_dataset(session, dataset_id))
        except DatasetNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
    finally:
        session.close()


@router.patch("/{dataset_id}", response_model=DatasetResponse)
def dataset_update(
    dataset_id: uuid.UUID, payload: DatasetUpdate, actor: DatasetManager
) -> DatasetResponse:
    session = get_db_session()
    try:
        try:
            item = get_dataset(session, dataset_id)
            before = {
                "name": item.name,
                "status": item.status,
                "owner_organisation_id": str(item.owner_organisation_id),
            }
            item = update_dataset(session, item, **payload.model_dump(exclude_unset=True))
            record_audit_event(
                session,
                action="dataset.update",
                resource_type="dataset",
                resource_id=item.id,
                actor=actor,
                organisation_id=item.owner_organisation_id,
                details={
                    "before": before,
                    "after": payload.model_dump(exclude_unset=True, mode="json"),
                },
            )
            session.commit()
            return _dataset_response(item)
        except DatasetNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
    finally:
        session.close()


@router.get("/{dataset_id}/sources", response_model=list[DatasetSourceResponse])
def sources_list(dataset_id: uuid.UUID, _: DatasetReader) -> list[DatasetSourceResponse]:
    session = get_db_session()
    try:
        try:
            return [_source_response(item) for item in list_sources(session, dataset_id)]
        except DatasetNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
    finally:
        session.close()


@router.post("/{dataset_id}/sources", response_model=DatasetSourceResponse, status_code=201)
def source_create(
    dataset_id: uuid.UUID, payload: DatasetSourceCreate, actor: DatasetManager
) -> DatasetSourceResponse:
    session = get_db_session()
    try:
        item = create_source(session, dataset_id, **payload.model_dump())
        record_audit_event(
            session,
            action="dataset.source.create",
            resource_type="dataset_source",
            resource_id=item.id,
            actor=actor,
            details={"dataset_id": str(dataset_id), "source_type": item.source_type},
        )
        session.commit()
        return _source_response(item)
    except DatasetNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    finally:
        session.close()


@router.get("/{dataset_id}/fields", response_model=list[DatasetFieldResponse])
def fields_list(dataset_id: uuid.UUID, _: DatasetReader) -> list[DatasetFieldResponse]:
    session = get_db_session()
    try:
        try:
            return [_field_response(item) for item in list_fields(session, dataset_id)]
        except DatasetNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
    finally:
        session.close()


@router.post("/{dataset_id}/fields", response_model=DatasetFieldResponse, status_code=201)
def field_create(
    dataset_id: uuid.UUID, payload: DatasetFieldCreate, actor: DatasetManager
) -> DatasetFieldResponse:
    session = get_db_session()
    try:
        try:
            item = create_field(session, dataset_id, **payload.model_dump())
            record_audit_event(
                session,
                action="dataset.field.create",
                resource_type="dataset_field",
                resource_id=item.id,
                actor=actor,
                details={
                    "dataset_id": str(dataset_id),
                    "name": item.name,
                    "data_type": item.data_type,
                },
            )
            session.commit()
            return _field_response(item)
        except (DatasetNotFoundError, DatasetConflictError) as exc:
            raise HTTPException(
                status_code=409 if isinstance(exc, DatasetConflictError) else 404, detail=str(exc)
            ) from exc
    finally:
        session.close()


@router.get("/{dataset_id}/versions", response_model=list[DatasetVersionResponse])
def versions_list(dataset_id: uuid.UUID, _: DatasetReader) -> list[DatasetVersionResponse]:
    session = get_db_session()
    try:
        try:
            return [_version_response(item) for item in list_versions(session, dataset_id)]
        except DatasetNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
    finally:
        session.close()


@router.post("/{dataset_id}/uploads", response_model=DatasetUploadResponse, status_code=201)
async def upload_csv(
    dataset_id: uuid.UUID,
    request: Request,
    actor: DatasetUploader,
    filename: FilenameParam,
    source_id: uuid.UUID | None = None,
) -> DatasetUploadResponse:
    session = get_db_session()
    try:
        try:
            dataset = get_dataset(session, dataset_id)
            content = await request.body()
            _, upload = create_csv_upload(
                session,
                dataset=dataset,
                source_id=source_id,
                actor=actor,
                filename=filename,
                content_type=request.headers.get("content-type", "application/octet-stream"),
                content=content,
            )
            session.commit()
            return _upload_response(upload)
        except (DatasetNotFoundError, UploadValidationError) as exc:
            session.rollback()
            raise HTTPException(
                status_code=400 if isinstance(exc, UploadValidationError) else 404, detail=str(exc)
            ) from exc
    finally:
        session.close()


@router.get("/versions/{version_id}/download")
def download_upload(version_id: uuid.UUID, _: DatasetReader) -> Response:
    session = get_db_session()
    try:
        upload = session.scalar(
            select(DatasetUpload).where(DatasetUpload.dataset_version_id == version_id)
        )
        if upload is None:
            raise HTTPException(status_code=404, detail="Dataset upload not found.")
        return Response(
            content=get_object(upload.object_key),
            media_type=upload.mime_type or "application/octet-stream",
            headers={"Content-Disposition": f'attachment; filename="{upload.original_filename}"'},
        )
    finally:
        session.close()


@router.post(
    "/versions/{version_id}/validate", response_model=ValidationRunResponse, status_code=202
)
def validate_version(
    version_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    actor: DatasetValidator,
    background: bool = False,
) -> ValidationRunResponse:
    session = get_db_session()
    try:
        version = session.get(DatasetVersion, version_id)
        if version is None:
            raise HTTPException(status_code=404, detail="Dataset version not found.")
        try:
            run = create_validation_run(
                session,
                version=version,
                execution_mode="BACKGROUND" if background else "SYNC",
            )
            if background:
                session.commit()
                response = _validation_response(session, run)
                background_tasks.add_task(_background_validate, run.id, actor.id)
                return response
            execute_validation(session, run=run, actor=actor)
            session.commit()
            return _validation_response(session, run)
        except ValidationServiceError as exc:
            session.rollback()
            raise HTTPException(status_code=409, detail=str(exc)) from exc
    finally:
        session.close()


@router.get("/versions/{version_id}/validations", response_model=list[ValidationRunResponse])
def validation_runs(version_id: uuid.UUID, _: DatasetReader) -> list[ValidationRunResponse]:
    session = get_db_session()
    try:
        runs = list(
            session.scalars(
                select(DataValidationRun)
                .where(DataValidationRun.dataset_version_id == version_id)
                .order_by(DataValidationRun.created_at.desc())
            ).all()
        )
        return [_validation_response(session, run) for run in runs]
    finally:
        session.close()


@router.get("/versions/{version_id}/history", response_model=list[VersionStatusHistoryResponse])
def version_history(version_id: uuid.UUID, _: DatasetReader) -> list[VersionStatusHistoryResponse]:
    session = get_db_session()
    try:
        items = list(
            session.scalars(
                select(DatasetVersionStatusHistory)
                .where(DatasetVersionStatusHistory.dataset_version_id == version_id)
                .order_by(DatasetVersionStatusHistory.created_at)
            ).all()
        )
        return [
            VersionStatusHistoryResponse.model_validate(item, from_attributes=True)
            for item in items
        ]
    finally:
        session.close()


@router.post("/versions/{version_id}/submit", response_model=ApprovalResponse)
def submit_version(version_id: uuid.UUID, actor: DatasetManager) -> ApprovalResponse:
    session = get_db_session()
    try:
        version = session.get(DatasetVersion, version_id)
        if version is None:
            raise HTTPException(status_code=404, detail="Dataset version not found.")
        try:
            approval = submit_for_approval(session, version, actor)
            session.commit()
            return _approval_response(approval)
        except LifecycleError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
    finally:
        session.close()


@router.post("/approvals/{approval_id}/approve", response_model=ApprovalResponse)
def approve_version(
    approval_id: uuid.UUID, payload: ApprovalAction, actor: DatasetApprover
) -> ApprovalResponse:
    session = get_db_session()
    try:
        approval = session.get(Approval, approval_id)
        if approval is None:
            raise HTTPException(status_code=404, detail="Approval not found.")
        try:
            decide_approval(session, approval, actor=actor, approve=True, comments=payload.comments)
            session.commit()
            return _approval_response(approval)
        except LifecycleError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
    finally:
        session.close()


@router.post("/approvals/{approval_id}/reject", response_model=ApprovalResponse)
def reject_version(
    approval_id: uuid.UUID, payload: ApprovalAction, actor: DatasetApprover
) -> ApprovalResponse:
    session = get_db_session()
    try:
        approval = session.get(Approval, approval_id)
        if approval is None:
            raise HTTPException(status_code=404, detail="Approval not found.")
        try:
            decide_approval(
                session, approval, actor=actor, approve=False, comments=payload.comments
            )
            session.commit()
            return _approval_response(approval)
        except LifecycleError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
    finally:
        session.close()


@router.post("/versions/{version_id}/publish", response_model=DatasetVersionResponse)
def publish_dataset_version(
    version_id: uuid.UUID, actor: DatasetPublisher
) -> DatasetVersionResponse:
    session = get_db_session()
    try:
        version = session.get(DatasetVersion, version_id)
        if version is None:
            raise HTTPException(status_code=404, detail="Dataset version not found.")
        try:
            publish_version(session, version, actor)
            session.commit()
            return _version_response(version)
        except LifecycleError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
    finally:
        session.close()
