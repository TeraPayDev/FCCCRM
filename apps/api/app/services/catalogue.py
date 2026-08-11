from __future__ import annotations

import uuid

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models.data_management import Dataset, DatasetField, DatasetSource, DatasetVersion


class DatasetNotFoundError(LookupError):
    pass


class DatasetConflictError(ValueError):
    pass


def get_dataset(session: Session, dataset_id: uuid.UUID) -> Dataset:
    dataset = session.get(Dataset, dataset_id)
    if dataset is None:
        raise DatasetNotFoundError("Dataset not found.")
    return dataset


def list_datasets(
    session: Session,
    *,
    offset: int = 0,
    limit: int = 50,
    owner_organisation_id: uuid.UUID | None = None,
    category: str | None = None,
    status: str | None = None,
    query_text: str | None = None,
) -> tuple[list[Dataset], int]:
    query = select(Dataset)
    count_query = select(func.count()).select_from(Dataset)
    filters = []
    if owner_organisation_id is not None:
        filters.append(Dataset.owner_organisation_id == owner_organisation_id)
    if category:
        filters.append(Dataset.category == category)
    if status:
        filters.append(Dataset.status == status)
    if query_text:
        pattern = f"%{query_text.strip()}%"
        filters.append(or_(Dataset.name.ilike(pattern), Dataset.code.ilike(pattern)))
    if filters:
        query = query.where(*filters)
        count_query = count_query.where(*filters)
    total = int(session.scalar(count_query) or 0)
    items = list(session.scalars(query.order_by(Dataset.name).offset(offset).limit(limit)).all())
    return items, total


def create_dataset(session: Session, **values: object) -> Dataset:
    code = str(values["code"]).strip()
    if session.scalar(select(Dataset.id).where(Dataset.code == code)) is not None:
        raise DatasetConflictError("Dataset code already exists.")
    dataset = Dataset(**values)
    session.add(dataset)
    session.flush()
    return dataset


def update_dataset(session: Session, dataset: Dataset, **values: object) -> Dataset:
    for name, value in values.items():
        if value is not None:
            setattr(dataset, name, value)
    session.flush()
    return dataset


def create_source(session: Session, dataset_id: uuid.UUID, **values: object) -> DatasetSource:
    get_dataset(session, dataset_id)
    source = DatasetSource(dataset_id=dataset_id, **values)
    session.add(source)
    session.flush()
    return source


def list_sources(session: Session, dataset_id: uuid.UUID) -> list[DatasetSource]:
    get_dataset(session, dataset_id)
    return list(
        session.scalars(
            select(DatasetSource)
            .where(DatasetSource.dataset_id == dataset_id)
            .order_by(DatasetSource.name)
        ).all()
    )


def create_field(session: Session, dataset_id: uuid.UUID, **values: object) -> DatasetField:
    get_dataset(session, dataset_id)
    name = str(values["name"])
    existing = session.scalar(
        select(DatasetField.id).where(
            DatasetField.dataset_id == dataset_id,
            DatasetField.name == name,
        )
    )
    if existing is not None:
        raise DatasetConflictError("Dataset field already exists.")
    field = DatasetField(dataset_id=dataset_id, **values)
    session.add(field)
    session.flush()
    return field


def list_fields(session: Session, dataset_id: uuid.UUID) -> list[DatasetField]:
    get_dataset(session, dataset_id)
    return list(
        session.scalars(
            select(DatasetField)
            .where(DatasetField.dataset_id == dataset_id)
            .order_by(DatasetField.ordinal)
        ).all()
    )


def list_versions(session: Session, dataset_id: uuid.UUID) -> list[DatasetVersion]:
    get_dataset(session, dataset_id)
    return list(
        session.scalars(
            select(DatasetVersion)
            .where(DatasetVersion.dataset_id == dataset_id)
            .order_by(DatasetVersion.version_number.desc())
        ).all()
    )
