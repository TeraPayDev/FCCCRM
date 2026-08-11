from __future__ import annotations

import os
import uuid
from collections.abc import Generator
from typing import cast

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.db.seed import seed
from app.db.session import get_session_factory
from app.main import app
from app.models.identity import Organisation, Role, User
from app.security.passwords import hash_password

pytestmark = pytest.mark.database


@pytest.fixture
def auth_users() -> Generator[tuple[str, str, str]]:
    if os.getenv("RUN_DB_INTEGRATION") != "1":
        pytest.skip("Database integration test runs only in the migration gate.")

    seed()

    factory = get_session_factory()
    password = "Milestone5-Test-Password-123!"

    suffix = uuid.uuid4().hex[:12]
    admin_username = f"m5admin-{suffix}"
    public_username = f"m5public-{suffix}"

    with factory() as session, session.begin():
        fcc = session.scalar(select(Organisation).where(Organisation.code == "FCC"))

        admin_role = session.scalar(
            select(Role)
            .options(selectinload(Role.permissions))
            .where(Role.code == "system_administrator")
        )

        public_role = session.scalar(select(Role).where(Role.code == "public_user"))

        assert fcc is not None
        assert admin_role is not None
        assert public_role is not None

        admin = User(
            username=admin_username,
            email=f"{admin_username}@test.local",
            organisation_id=fcc.id,
            password_hash=hash_password(password),
        )
        admin.roles = [admin_role]

        public = User(
            username=public_username,
            email=f"{public_username}@test.local",
            organisation_id=fcc.id,
            password_hash=hash_password(password),
        )
        public.roles = [public_role]

        session.add_all(
            [
                admin,
                public,
            ]
        )

    # Do not delete the users during teardown.
    #
    # Authentication now creates immutable audit records whose actor_user_id
    # references must remain historically valid. Migration-gate databases are
    # disposable, and unique usernames prevent repeated-test collisions.
    yield admin_username, public_username, password


def _login(
    client: TestClient,
    username: str,
    password: str,
) -> dict[str, object]:
    response = client.post(
        "/api/v1/auth/login",
        json={
            "username": username,
            "password": password,
        },
    )

    assert response.status_code == 200

    return cast(
        dict[str, object],
        response.json(),
    )


def test_authentication_refresh_logout_and_permissions(
    auth_users: tuple[str, str, str],
) -> None:
    admin_username, _, password = auth_users

    client = TestClient(app)

    invalid = client.post(
        "/api/v1/auth/login",
        json={
            "username": admin_username,
            "password": "wrong",
        },
    )

    assert invalid.status_code == 401

    tokens = _login(
        client,
        admin_username,
        password,
    )

    access_token = str(tokens["access_token"])
    refresh_token = str(tokens["refresh_token"])

    current_user = client.get(
        "/api/v1/auth/me",
        headers={
            "Authorization": f"Bearer {access_token}",
        },
    )

    assert current_user.status_code == 200
    assert current_user.json()["username"] == admin_username
    assert "users.read" in current_user.json()["permissions"]

    permissions = client.get(
        "/api/v1/auth/permissions",
        headers={
            "Authorization": f"Bearer {access_token}",
        },
    )

    assert permissions.status_code == 200

    refreshed = client.post(
        "/api/v1/auth/refresh",
        json={
            "refresh_token": refresh_token,
        },
    )

    assert refreshed.status_code == 200

    logout = client.post(
        "/api/v1/auth/logout",
        headers={
            "Authorization": f"Bearer {access_token}",
        },
    )

    assert logout.status_code == 204

    revoked = client.get(
        "/api/v1/auth/me",
        headers={
            "Authorization": f"Bearer {access_token}",
        },
    )

    assert revoked.status_code == 401


def test_user_without_permission_receives_403(
    auth_users: tuple[str, str, str],
) -> None:
    _, public_username, password = auth_users

    client = TestClient(app)

    tokens = _login(
        client,
        public_username,
        password,
    )

    access_token = str(tokens["access_token"])

    denied = client.get(
        "/api/v1/auth/permissions",
        headers={
            "Authorization": f"Bearer {access_token}",
        },
    )

    assert denied.status_code == 403
