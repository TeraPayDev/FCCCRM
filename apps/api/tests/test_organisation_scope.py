import uuid

from app.models.identity import Permission, Role, User
from app.services.organisation_scope import organisation_scope_allows


def _user_with_permission(organisation_id: uuid.UUID, permission_code: str) -> User:
    permission = Permission(code=permission_code)
    role = Role(code="test_role", name="Test Role")
    role.permissions = [permission]
    user = User(
        username="scope-user",
        email="scope-user@test.local",
        organisation_id=organisation_id,
    )
    user.roles = [role]
    return user


def test_organisation_scope_requires_permission_and_same_organisation() -> None:
    organisation_id = uuid.uuid4()
    user = _user_with_permission(organisation_id, "datasets.manage")

    assert organisation_scope_allows(
        user,
        permission_code="datasets.manage",
        resource_organisation_id=organisation_id,
    )
    assert not organisation_scope_allows(
        user,
        permission_code="datasets.manage",
        resource_organisation_id=uuid.uuid4(),
    )
    assert not organisation_scope_allows(
        user,
        permission_code="users.manage",
        resource_organisation_id=organisation_id,
    )


def test_organisation_scope_can_explicitly_allow_cross_organisation() -> None:
    user = _user_with_permission(uuid.uuid4(), "datasets.manage")

    assert organisation_scope_allows(
        user,
        permission_code="datasets.manage",
        resource_organisation_id=uuid.uuid4(),
        allow_cross_organisation=True,
    )
