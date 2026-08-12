from __future__ import annotations

import os
import uuid
from unittest.mock import patch

import pytest
from sqlalchemy import select

from app.db.seed import seed
from app.db.session import get_session_factory
from app.models.data_management import Approval, DatasetVersion, DataValidationRun
from app.models.identity import Organisation, Role, User
from app.security.passwords import hash_password
from app.services.catalogue import create_dataset, create_field, create_source
from app.services.ingestion import UploadValidationError, create_csv_upload, safe_filename
from app.services.lifecycle import decide_approval, publish_version, submit_for_approval
from app.services.validation import create_validation_run, execute_validation

pytestmark = pytest.mark.database


@pytest.fixture
def data_platform_context() -> tuple[uuid.UUID, uuid.UUID]:
    if os.getenv("RUN_DB_INTEGRATION") != "1":
        pytest.skip("Database integration test runs only in the migration gate.")
    seed()
    factory = get_session_factory()
    suffix = uuid.uuid4().hex[:10]
    with factory() as session, session.begin():
        organisation = session.scalar(select(Organisation).where(Organisation.code == "FCC"))
        role = session.scalar(select(Role).where(Role.code == "system_administrator"))
        assert organisation is not None
        assert role is not None
        user = User(
            username=f"data-platform-{suffix}",
            email=f"data-platform-{suffix}@test.local",
            organisation_id=organisation.id,
            password_hash=hash_password("Data-Platform-Test-123!"),
        )
        user.roles = [role]
        session.add(user)
        session.flush()
        dataset = create_dataset(
            session,
            code=f"SYN-{suffix}",
            name="Synthetic data-platform acceptance dataset",
            description="Synthetic test only",
            owner_organisation_id=organisation.id,
            category="acceptance",
            sensitivity="INTERNAL",
            expected_format="CSV",
            update_frequency="ad hoc",
            status="DRAFT",
        )
        create_source(
            session,
            dataset.id,
            provider_organisation_id=organisation.id,
            name="Synthetic CSV",
            source_type="FILE",
            source_reference="controlled acceptance fixture",
            connection_secret_ref=None,
            update_method="manual upload",
        )
        create_field(
            session,
            dataset.id,
            name="temperature_c",
            data_type="number",
            ordinal=0,
            is_required=True,
            description=None,
            validation_rules={"min": -20, "max": 60},
        )
        return dataset.id, user.id


def test_safe_filename_and_upload_restrictions() -> None:
    assert safe_filename("../weather sample.csv") == "weather_sample.csv"
    with pytest.raises(UploadValidationError):
        safe_filename("../")


def test_catalogue_ingestion_validation_and_lifecycle(
    data_platform_context: tuple[uuid.UUID, uuid.UUID],
) -> None:
    dataset_id, user_id = data_platform_context
    raw = b"temperature_c\n27.4\n999\n"
    factory = get_session_factory()
    stored: dict[str, bytes] = {}

    def fake_put(*, key: str, body: bytes, content_type: str) -> None:
        assert content_type == "text/csv"
        stored[key] = body

    def fake_get(key: str) -> bytes:
        return stored[key]

    with (
        patch("app.services.ingestion.put_object", side_effect=fake_put),
        patch("app.services.validation.get_object", side_effect=fake_get),
    ):
        with factory() as session, session.begin():
            from app.models.data_management import Dataset

            dataset = session.get(Dataset, dataset_id)
            actor = session.get(User, user_id)
            assert dataset is not None
            assert actor is not None
            version, upload = create_csv_upload(
                session,
                dataset=dataset,
                source_id=None,
                actor=actor,
                filename="weather.csv",
                content_type="text/csv",
                content=raw,
            )
            assert stored[upload.object_key] == raw
            run = create_validation_run(session, version=version, execution_mode="SYNC")
            execute_validation(session, run=run, actor=actor)
            assert run.status == "FAILED"
            assert run.error_count == 1
            failed_version_id = version.id

        with factory() as session, session.begin():
            failed = session.get(DatasetVersion, failed_version_id)
            assert failed is not None
            assert failed.status == "VALIDATION_FAILED"

            dataset_id_again = failed.dataset_id
            actor = session.get(User, user_id)
            from app.models.data_management import Dataset

            dataset_model = session.get(Dataset, dataset_id_again)
            assert dataset_model is not None
            assert actor is not None
            good_version, _ = create_csv_upload(
                session,
                dataset=dataset_model,
                source_id=None,
                actor=actor,
                filename="weather-good.csv",
                content_type="text/csv",
                content=b"temperature_c\n27.4\n28.1\n",
            )
            run = create_validation_run(session, version=good_version, execution_mode="SYNC")
            execute_validation(session, run=run, actor=actor)
            assert run.status == "PASSED"
            approval = submit_for_approval(session, good_version, actor)
            decide_approval(session, approval, actor=actor, approve=True, comments="accepted")
            publish_version(session, good_version, actor)
            assert good_version.status == "PUBLISHED"
            assert approval.status == "APPROVED"
            published_version_id = good_version.id

        with factory() as session, session.begin():
            from app.models.data_management import Dataset

            first_published = session.get(DatasetVersion, published_version_id)
            dataset_model = session.get(Dataset, dataset_id)
            actor = session.get(User, user_id)
            assert first_published is not None
            assert dataset_model is not None
            assert actor is not None
            replacement, _ = create_csv_upload(
                session,
                dataset=dataset_model,
                source_id=None,
                actor=actor,
                filename="weather-replacement.csv",
                content_type="text/csv",
                content=b"temperature_c\n29.0\n29.5\n",
            )
            run = create_validation_run(session, version=replacement, execution_mode="SYNC")
            execute_validation(session, run=run, actor=actor)
            approval = submit_for_approval(session, replacement, actor)
            decide_approval(session, approval, actor=actor, approve=True, comments="replacement")
            publish_version(session, replacement, actor)
            assert replacement.status == "PUBLISHED"
            assert first_published.status == "SUPERSEDED"

        with factory() as session:
            assert session.scalar(select(Approval).where(Approval.status == "APPROVED")) is not None
            assert (
                session.scalar(
                    select(DataValidationRun).where(DataValidationRun.status == "PASSED")
                )
                is not None
            )
