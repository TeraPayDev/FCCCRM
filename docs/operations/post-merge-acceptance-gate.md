# Post-Merge Acceptance Gate

Run on the CRAM server after overlaying this package and before Git push.

```bash
cd /opt/cram/source/cram-platform/apps/api
uv run ruff format app tests migrations
uv run ruff format --check app tests migrations
uv run ruff check app tests migrations
uv run mypy app tests
uv run pytest -q

cd ../web
pnpm exec prettier --write src tests
pnpm format:check
pnpm exec tsc --noEmit
pnpm lint
pnpm test -- --run
pnpm build

cd /opt/cram/source/cram-platform
docker compose config >/dev/null
docker compose build api worker web
docker compose up -d --force-recreate api worker web
sleep 10
docker compose ps -a
```

For CDS readiness after the rebuild:

```bash
docker compose exec api sh -c 'test -n "$COPERNICUS_CDS_KEY" && echo "PASS: CDS token injected" || echo "MISSING: CDS token"'
curl -s http://127.0.0.1:8000/api/v1/health
```

Do not print the CDS token itself.
