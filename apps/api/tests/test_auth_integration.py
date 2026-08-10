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
from app.models.identity import Organisation, Role, User
from app.security.passwords import hash_password

pytestmark = pytest.mark.database


@pytest.fixture
def auth_users() -> Generator[tuple[str, str]]:
    if os.getenv("RUN_DB_INTEGRATION") != "1":
        pytest.skip("Database integration test runs only in the migration gate.")

    seed()
    factory = get_session_factory()
    password = "Milestone5-Test-Password-123!"

    with factory() as session, session.begin():
        session.execute(delete(User).where(User.username.in_(["m5admin", "m5public"])))
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
            username="m5admin",
            email="m5admin@test.local",
            organisation_id=fcc.id,
            password_hash=hash_password(password),
        )
        admin.roles = [admin_role]
        public = User(
            username="m5public",
            email="m5public@test.local",
            organisation_id=fcc.id,
            password_hash=hash_password(password),
        )
        public.roles = [public_role]
        session.add_all([admin, public])

    yield "m5admin", password

    with factory() as session, session.begin():
        session.execute(delete(User).where(User.username.in_(["m5admin", "m5public"])))


def _login(client: TestClient, username: str, password: str) -> dict[str, object]:
    response = client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": password},
    )
    assert response.status_code == 200
    return cast(dict[str, object], response.json())


def test_authentication_refresh_logout_and_permissions(
    auth_users: tuple[str, str],
) -> None:
    username, password = auth_users
    client = TestClient(app)

    bad = client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": "wrong"},
    )
    assert bad.status_code == 401

    tokens = _login(client, username, password)
    access = str(tokens["access_token"])
    refresh = str(tokens["refresh_token"])

    me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {access}"})
    assert me.status_code == 200
    assert me.json()["username"] == username
    assert "users.read" in me.json()["permissions"]

    permitted = client.get(
        "/api/v1/auth/permissions",
        headers={"Authorization": f"Bearer {access}"},
    )
    assert permitted.status_code == 200

    refreshed = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh},
    )
    assert refreshed.status_code == 200

    logout = client.post(
        "/api/v1/auth/logout",
        headers={"Authorization": f"Bearer {access}"},
    )
    assert logout.status_code == 204

    revoked = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {access}"},
    )
    assert revoked.status_code == 401


def test_user_without_permission_receives_403(
    auth_users: tuple[str, str],
) -> None:
    _, password = auth_users
    client = TestClient(app)
    tokens = _login(client, "m5public", password)
    access = str(tokens["access_token"])

    denied = client.get(
        "/api/v1/auth/permissions",
        headers={"Authorization": f"Bearer {access}"},
    )
    assert denied.status_code == 403
