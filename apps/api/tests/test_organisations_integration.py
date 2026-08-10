import os
from collections.abc import Generator
from typing import cast

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, select
from sqlalchemy.orm import selectinload

from app.db.seed import seed
from app.db.session import get_session_factory
from app.main import app
from app.models.data_management import Dataset, DatasetSource
from app.models.identity import Organisation, Role, User
from app.security.passwords import hash_password
from app.services.organisation_scope import organisation_scope_allows

pytestmark = pytest.mark.database


@pytest.fixture
def organisation_admin() -> Generator[tuple[str, str]]:
    if os.getenv("RUN_DB_INTEGRATION") != "1":
        pytest.skip("Database integration test runs only in the migration/acceptance gate.")

    seed()
    factory = get_session_factory()
    password = "Milestone6-Test-Password-123!"

    with factory() as session, session.begin():
        session.execute(delete(User).where(User.username == "m6admin"))
        fcc = session.scalar(select(Organisation).where(Organisation.code == "FCC"))
        admin_role = session.scalar(
            select(Role)
            .options(selectinload(Role.permissions))
            .where(Role.code == "system_administrator")
        )
        assert fcc is not None
        assert admin_role is not None
        user = User(
            username="m6admin",
            email="m6admin@test.local",
            organisation_id=fcc.id,
            password_hash=hash_password(password),
        )
        user.roles = [admin_role]
        session.add(user)

    yield "m6admin", password

    with factory() as session, session.begin():
        dataset = session.scalar(select(Dataset).where(Dataset.code == "M6-OWNERSHIP-TEST"))
        if dataset is not None:
            session.delete(dataset)
        session.execute(delete(User).where(User.username == "m6admin"))
        session.execute(delete(Organisation).where(Organisation.code == "M6-TEMP"))


def _login(client: TestClient, username: str, password: str) -> dict[str, object]:
    response = client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": password},
    )
    assert response.status_code == 200
    return cast(dict[str, object], response.json())


def test_organisation_crud_and_user_assignment(
    organisation_admin: tuple[str, str],
) -> None:
    username, password = organisation_admin
    client = TestClient(app)
    token = str(_login(client, username, password)["access_token"])
    headers = {"Authorization": f"Bearer {token}"}

    listing = client.get("/api/v1/organisations", headers=headers)
    assert listing.status_code == 200
    codes = {item["code"] for item in listing.json()}
    assert {"FCC", "NaCSA", "NDMA", "SL-Met", "Stats-SL", "ONS"}.issubset(codes)

    created = client.post(
        "/api/v1/organisations",
        headers=headers,
        json={"code": "M6-TEMP", "name": "Milestone 6 Temporary Organisation"},
    )
    assert created.status_code == 201
    organisation_id = created.json()["id"]

    updated = client.patch(
        f"/api/v1/organisations/{organisation_id}",
        headers=headers,
        json={"name": "Milestone 6 Temporary Partner"},
    )
    assert updated.status_code == 200
    assert updated.json()["name"] == "Milestone 6 Temporary Partner"

    users = client.get("/api/v1/organisations/users", headers=headers)
    assert users.status_code == 200
    admin = next(item for item in users.json() if item["username"] == username)

    assigned = client.patch(
        f"/api/v1/organisations/users/{admin['id']}",
        headers=headers,
        json={"organisation_id": organisation_id},
    )
    assert assigned.status_code == 200
    assert assigned.json()["organisation_id"] == organisation_id

    reassigned_fcc = next(item for item in listing.json() if item["code"] == "FCC")
    restored = client.patch(
        f"/api/v1/organisations/users/{admin['id']}",
        headers=headers,
        json={"organisation_id": reassigned_fcc["id"]},
    )
    assert restored.status_code == 200

    deleted = client.delete(f"/api/v1/organisations/{organisation_id}", headers=headers)
    assert deleted.status_code == 204


def test_dataset_and_source_identify_owner_provider_and_scope(
    organisation_admin: tuple[str, str],
) -> None:
    username, _ = organisation_admin
    factory = get_session_factory()

    with factory() as session, session.begin():
        user = session.scalar(
            select(User)
            .options(selectinload(User.roles).selectinload(Role.permissions))
            .where(User.username == username)
        )
        fcc = session.scalar(select(Organisation).where(Organisation.code == "FCC"))
        slmet = session.scalar(select(Organisation).where(Organisation.code == "SL-Met"))
        assert user is not None
        assert fcc is not None
        assert slmet is not None

        dataset = Dataset(
            code="M6-OWNERSHIP-TEST",
            name="Milestone 6 Ownership Test",
            owner_organisation_id=fcc.id,
        )
        session.add(dataset)
        session.flush()
        source = DatasetSource(
            dataset_id=dataset.id,
            provider_organisation_id=slmet.id,
            name="SL-Met Test Provider",
            source_type="file",
        )
        session.add(source)
        session.flush()

        assert dataset.owner_organisation_id == fcc.id
        assert source.provider_organisation_id == slmet.id
        assert organisation_scope_allows(
            user,
            permission_code="datasets.manage",
            resource_organisation_id=fcc.id,
        )
        assert not organisation_scope_allows(
            user,
            permission_code="datasets.manage",
            resource_organisation_id=slmet.id,
        )
