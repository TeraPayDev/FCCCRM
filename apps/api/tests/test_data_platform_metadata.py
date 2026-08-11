import app.models  # noqa: F401
from app.db.base import Base


def test_data_platform_tables_are_registered() -> None:
    expected = {
        "cram.data_validation_runs",
        "cram.validation_errors",
        "cram.approvals",
        "cram.dataset_version_status_history",
    }
    names = {f"{table.schema}.{table.name}" for table in Base.metadata.tables.values()}
    assert expected <= names
