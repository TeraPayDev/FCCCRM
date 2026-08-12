# Public Data Integration Runtime Test Plan

Run these checks after rebuilding `api`, `web`, and `worker`.

## 1. API route inventory

Confirm OpenAPI exposes:

- `/api/v1/public-data/weather/open-meteo`
- `/api/v1/public-data/weather/history`
- `/api/v1/public-data/weather/nasa-power`
- `/api/v1/public-data/spatial/osm`
- `/api/v1/public-data/vulnerability/world-bank`
- `/api/v1/public-data/earth-observation/copernicus`
- `/api/v1/public-data/earth-observation/usgs`
- `/api/v1/public-data/climate/copernicus-cds`
- `/api/v1/public-data/gis/reference`
- `/api/v1/integrations/public/bootstrap`
- `/api/v1/integrations/runs`

## 2. Processing bootstrap

Using an administrator token, POST `/api/v1/integrations/public/bootstrap` and verify:

- six active public connectors exist;
- the old `SLMET-SANDBOX` connector is inactive when present;
- public schedules are active and point to their current connector IDs;
- repeated bootstrap calls update rather than duplicate schedules.

POST `/api/v1/processing/schedules/run-due`. Confirm `PUBLIC_CONNECTOR_SYNC` jobs appear and integration runs record success/failure with source-specific error messages.

## 3. Live module checks

- Heat shows Open-Meteo and NASA POWER reference rows.
- Flood shows precipitation and OSM waterway context without a generated flood-risk classification.
- Trees shows OSM tree reference features where OSM coverage exists.
- Vulnerability shows World Bank Sierra Leone values without a generated vulnerability score.
- Advanced Analytics shows historical Open-Meteo/NASA series and Copernicus/USGS catalogue records.

## 4. GIS resilience

Open GIS Explorer and confirm:

- the basemap appears;
- governed CRAM layers appear independently of external reference availability;
- public weather/tree/waterway/boundary reference layers can be toggled;
- an external API failure reports a warning but does not blank the governed map.

## 5. Version lifecycle

Publish a newer approved dataset version and verify the previous `PUBLISHED` version becomes `SUPERSEDED` while remaining in version history.

## 6. Session timeout

For a practical runtime test, temporarily reduce `SESSION_IDLE_TIMEOUT_MS` in a local test build (for example to 60 seconds), rebuild the web container, sign in, remain idle, and verify:

- browser session storage is cleared;
- protected routes redirect to `/login?reason=expired`;
- login screen displays the session-expired message.

Restore the production timeout to 30 minutes after the test.
