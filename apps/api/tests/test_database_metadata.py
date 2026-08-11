import app.models  # noqa: F401
from app.db.base import Base


def test_milestone_4_tables_are_registered() -> None:
    expected = {
        "audit_logs",
        "dataset_fields",
        "dataset_sources",
        "dataset_uploads",
        "dataset_versions",
        "datasets",
        "geographic_areas",
        "organisations",
        "permissions",
        "role_permissions",
        "roles",
        "spatial_layers",
        "user_roles",
        "users",
    }

    actual = {key.split(".", 1)[-1] for key in Base.metadata.tables}

    assert expected <= actual
