# CRAM Local Infrastructure

This document describes the CRAM local development services established under **Milestone 2 - Local Infrastructure with Docker**.

It covers only the Milestone 2 infrastructure baseline. Application database models, authentication, climate modules, GIS layer publication, CI/CD, and other later-roadmap work are intentionally outside this document.

## 1. Project location

```text
/opt/cram/source/cram-platform
```

All commands in this document assume the project root unless stated otherwise.

## 2. Local Docker services

| Service | Container | Purpose | Access |
|---|---|---|---|
| Web | `cram-web` | React/Vite development frontend | LAN: `http://10.1.11.7:3000` |
| API | `cram-api` | FastAPI development API | LAN: `http://10.1.11.7:8000` |
| PostgreSQL/PostGIS | `cram-db` | Relational and spatial database | Docker network only |
| Redis | `cram-redis` | Local supporting/cache service | Docker network only |
| GeoServer | `cram-geoserver` | GIS service | LAN: `http://10.1.11.7:8080/geoserver` |
| Object storage | `cram-object-storage` | S3-compatible RustFS storage | Docker network only |

The private Docker network is:

```text
cram_internal
```

PostgreSQL, Redis, and object storage are intentionally not published directly to the LAN.

## 3. Persistent volumes

```text
cram_postgres_data
cram_redis_data
cram_geoserver_data
cram_object_storage_data
```

These named Docker volumes preserve local infrastructure data across normal container recreation.

## 4. Environment configuration

The committed configuration template is:

```text
.env.example
```

The runtime configuration is:

```text
.env
```

The runtime `.env` file contains development credentials and is excluded from Git. Do not commit it.

## 5. Start the local stack

```bash
cd /opt/cram/source/cram-platform
docker compose up -d
```

Check service state:

```bash
docker compose ps
```

The Milestone 2 baseline expects all six services to become healthy.

## 6. Stop the local stack

```bash
docker compose down
```

This stops/removes the containers and network but leaves the named data volumes intact.

Do not use `docker compose down -v` unless local infrastructure data is intentionally being destroyed.

## 7. Rebuild application containers

API:

```bash
docker compose build api
docker compose up -d api
```

Web:

```bash
docker compose build web
docker compose up -d web
```

## 8. View logs

All services:

```bash
docker compose logs --tail=100
```

Specific service:

```bash
docker compose logs --tail=100 api
docker compose logs --tail=100 db
docker compose logs --tail=100 geoserver
docker compose logs --tail=100 object-storage
```

Follow logs:

```bash
docker compose logs -f api
```

## 9. Development bootstrap

The development bootstrap script is:

```text
infrastructure/scripts/bootstrap-dev.sh
```

Run:

```bash
./infrastructure/scripts/bootstrap-dev.sh
```

It:

1. Starts the local Compose stack.
2. Waits for the required services to become healthy.
3. Verifies API-to-PostgreSQL/PostGIS connectivity.
4. Ensures the configured development object-storage bucket exists.
5. Verifies the configured bucket.

It does not create CRAM application/domain tables.

## 10. Database initialization

The PostgreSQL initialization directory is:

```text
infrastructure/docker/postgres/init
```

Current initialization file:

```text
001-enable-postgis.sql
```

It enables the required PostGIS extensions and reserves the `cram` schema.

The directory is mounted read-only at:

```text
/docker-entrypoint-initdb.d
```

PostgreSQL Docker initialization scripts execute when a **new/fresh database volume** is initialized. They are not intended as the application migration mechanism; database migrations belong to the later database-foundation milestone.

## 11. Verify API -> PostgreSQL/PostGIS

The bootstrap script performs this check automatically.

Manual verification:

```bash
docker compose exec api uv run python -c "
import os
import psycopg

url = os.environ['DATABASE_URL'].replace('postgresql+psycopg://', 'postgresql://', 1)

with psycopg.connect(url) as conn:
    with conn.cursor() as cur:
        cur.execute('SELECT current_database(), current_user, PostGIS_Version();')
        print(cur.fetchone())
"
```

## 12. Verify Redis

```bash
docker compose exec redis redis-cli ping
```

Expected:

```text
PONG
```

## 13. Verify API -> object storage

```bash
docker compose exec api uv run python -c "
import os
import boto3

s3 = boto3.client(
    's3',
    endpoint_url=os.environ['OBJECT_STORAGE_ENDPOINT'],
    aws_access_key_id=os.environ['OBJECT_STORAGE_ACCESS_KEY'],
    aws_secret_access_key=os.environ['OBJECT_STORAGE_SECRET_KEY'],
    region_name=os.environ['OBJECT_STORAGE_REGION'],
)

print([b['Name'] for b in s3.list_buckets().get('Buckets', [])])
"
```

The development bootstrap ensures the configured CRAM bucket exists.

## 14. Configure and verify GeoServer -> PostGIS

Run:

```bash
python3 infrastructure/scripts/configure-geoserver-postgis.py
```

The script:

1. Authenticates to the local GeoServer administration REST API.
2. Creates the `cram` workspace if required.
3. Creates the `cram-postgis` PostGIS datastore if required.
4. Configures the datastore to reach the Docker database service at `db:5432`.
5. Queries available feature types from GeoServer to verify the datastore connection.

The script reads PostgreSQL values from the local `.env` file.

If the GeoServer credentials stored in `.env` do not match the credentials currently configured in GeoServer, the script prompts securely for the current GeoServer credentials.

This milestone verifies the datastore connection only. Publishing actual CRAM GIS layers belongs to the GIS Foundation milestone.

## 15. Full Milestone 2 local verification

Run:

```bash
./infrastructure/scripts/verify-local-infrastructure.sh
```

Then:

```bash
docker compose ps
```

Expected infrastructure state:

```text
cram-db               healthy
cram-redis            healthy
cram-object-storage   healthy
cram-api              healthy
cram-web              healthy
cram-geoserver        healthy
```

GeoServer/PostGIS connectivity is verified separately with:

```bash
python3 infrastructure/scripts/configure-geoserver-postgis.py
```

## 16. LAN endpoints

```text
Frontend:
http://10.1.11.7:3000

FastAPI:
http://10.1.11.7:8000

FastAPI Swagger:
http://10.1.11.7:8000/docs

GeoServer:
http://10.1.11.7:8080/geoserver
```

The local firewall should allow the required development ports only from the intended LAN.

## 17. Milestone 2 boundaries

This infrastructure baseline deliberately does **not** implement:

- SQLAlchemy application models
- Alembic application migrations
- authentication/RBAC
- domain tables
- climate analytics
- GIS layer publication
- CI/CD
- production infrastructure

Those items remain in their existing later roadmap milestones.
