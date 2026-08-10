from __future__ import annotations

import uuid

from sqlalchemy import inspect, text
from sqlalchemy.exc import IntegrityError

from app.db.session import get_engine

EXPECTED_TABLES = {
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


def verify_tables() -> None:
    inspector = inspect(get_engine())
    actual = set(inspector.get_table_names(schema="cram"))
    missing = EXPECTED_TABLES - actual
    if missing:
        raise RuntimeError(f"Missing CRAM tables: {sorted(missing)}")
    print(f"PASS: {len(EXPECTED_TABLES)} expected CRAM tables exist.")


def verify_foreign_key_enforcement() -> None:
    connection = get_engine().connect()
    tx = connection.begin()
    try:
        connection.execute(
            text("""INSERT INTO cram.datasets (code, name, owner_organisation_id)
                    VALUES (:code, :name, :owner_id)"""),
            {"code": f"fk-test-{uuid.uuid4()}", "name": "FK test", "owner_id": uuid.uuid4()},
        )
        tx.commit()
    except IntegrityError:
        tx.rollback()
        print("PASS: foreign-key enforcement rejected an invalid organisation reference.")
    else:
        raise RuntimeError("Foreign-key enforcement test unexpectedly succeeded.")
    finally:
        connection.close()


def verify_geometry() -> None:
    with get_engine().connect() as connection:
        tx = connection.begin()
        try:
            row = connection.execute(
                text("""
                    INSERT INTO cram.geographic_areas
                        (code, name, area_type, geometry, centroid)
                    VALUES
                        (:code, 'Milestone 4 geometry test', 'TEST',
                         ST_Multi(ST_GeomFromText(
                           'POLYGON((-13.30 8.40,-13.20 8.40,-13.20 8.50,-13.30 8.50,-13.30 8.40))', 4326)),
                         ST_GeomFromText('POINT(-13.25 8.45)', 4326))
                    RETURNING id
                """),
                {"code": f"geom-test-{uuid.uuid4()}"},
            ).one()
            result = connection.execute(
                text("""SELECT ST_IsValid(geometry) AS valid,
                               ST_SRID(geometry) AS geometry_srid,
                               ST_SRID(centroid) AS centroid_srid
                        FROM cram.geographic_areas WHERE id = :id"""),
                {"id": row.id},
            ).one()
            if not result.valid or result.geometry_srid != 4326 or result.centroid_srid != 4326:
                raise RuntimeError(f"Unexpected geometry result: {result}")
            print("PASS: PostGIS geometry columns can be inserted and queried.")
        finally:
            tx.rollback()


def verify_indexes() -> None:
    inspector = inspect(get_engine())
    required = {
        ("datasets", "ix_datasets_owner_organisation_id"),
        ("dataset_versions", "ix_dataset_versions_dataset_id"),
        ("audit_logs", "ix_audit_logs_occurred_at"),
        ("geographic_areas", "ix_geographic_areas_geometry_gist"),
        ("spatial_layers", "ix_spatial_layers_dataset_version_id"),
    }
    missing = set()
    for table, index_name in required:
        names = {idx["name"] for idx in inspector.get_indexes(table, schema="cram")}
        if index_name not in names:
            missing.add((table, index_name))
    if missing:
        raise RuntimeError(f"Missing deliberate indexes: {sorted(missing)}")
    print("PASS: deliberate foundation indexes are present.")


def main() -> None:
    verify_tables()
    verify_foreign_key_enforcement()
    verify_geometry()
    verify_indexes()
    print("CRAM Milestone 4 database foundation verification passed.")


if __name__ == "__main__":
    main()
