# CRAM Database Conventions v1

This document records the Milestone 4 database conventions only. It does not define later business workflows.

## Schema

CRAM application tables live in the PostgreSQL `cram` schema.

## Naming

- Tables and columns use plural/singular `snake_case` conventions already established by the roadmap.
- Primary keys are named `id`.
- Foreign keys use `<resource>_id`.
- Indexes and constraints are explicitly named.

## Primary keys

Application entities use PostgreSQL UUID primary keys. The database migration uses `gen_random_uuid()` as the server default.

## Timestamps

Application timestamps are timezone-aware PostgreSQL timestamps. Application code treats timestamps as UTC.

## Foreign keys

Deletion behavior is selected deliberately:
- `CASCADE` for dependent association/version records.
- `SET NULL` where historical metadata should survive an optional-reference deletion.
- `RESTRICT` where deleting an owner would invalidate an existing record.

## Indexes

Indexes are added for known foundation access paths and foreign-key lookups. A GiST index is included for geographic geometry.

## Spatial columns

`geographic_areas` contains `MULTIPOLYGON` geometry and `POINT` centroid columns. Milestone 4 uses SRID 4326 only to prove geometry creation/querying. This does not define the final FCC spatial hierarchy or final CRS policy, which remain Milestone 8 decisions based on authoritative source data.

## Migrations

Alembic is the supported mechanism for application schema changes. Development migrations must pass:

`upgrade -> downgrade -> upgrade`

The required CI `Migration validation` check executes this cycle.

## Seed data

Milestone 4 seed data is limited to known organisations and placeholder system roles already named in the approved roadmap. It does not seed permissions, users, passwords, datasets, climate data, approval rules, or scientific methodology.

## Secrets

Database credentials remain environment-managed and are not embedded in models, migrations, seeds, or documentation.
