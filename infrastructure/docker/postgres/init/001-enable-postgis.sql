-- CRAM Milestone 2 - PostgreSQL/PostGIS initialization
--
-- This script is intentionally infrastructure-only.
-- It enables the PostGIS extensions required by CRAM without creating
-- application/domain tables that belong to later roadmap milestones.
--
-- PostgreSQL Docker initialization scripts execute only when a fresh
-- database volume is initialized.

CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS postgis_topology;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_namespace
        WHERE nspname = 'cram'
    ) THEN
        EXECUTE 'CREATE SCHEMA cram';
    END IF;
END
$$;

COMMENT ON SCHEMA cram IS
    'Reserved CRAM application schema. Application tables are created by later roadmap migrations.';
