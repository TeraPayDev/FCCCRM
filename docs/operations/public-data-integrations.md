# CRAM Public Reference Data Integrations

## Purpose

CRAM can retrieve public reference data for demonstrations, situational awareness, and engineering validation while institutional feeds from FCC, SL-Met, NDMA, NaCSA, Statistics Sierra Leone, and other authoritative providers are being onboarded.

Public reference data does **not** bypass CRAM governance. A successful connector run records provenance and execution metadata. Data that is to become authoritative CRAM content must still enter a governed dataset version, pass validation, be approved, and be published.

## Included connectors

| Connector | CRAM use | Default cadence |
|---|---|---:|
| Open-Meteo — Freetown | Current/forecast temperature, humidity, rain, pressure, cloud and wind | Hourly |
| NASA POWER — Freetown | Daily meteorological history/reference series | Daily |
| OpenStreetMap Overpass — Freetown | Trees, waterways and administrative-boundary reference features | Daily |
| World Bank Indicators — Sierra Leone | National socio-economic/environmental context for vulnerability analysis | Daily |
| Copernicus Data Space STAC | Sentinel-2 Earth-observation catalogue discovery | 6 hours |
| USGS Landsat STAC | Landsat catalogue discovery | 12 hours |

The Processing screen can bootstrap these connectors and schedules. The bootstrap operation is idempotent: existing connector/schedule definitions are updated and re-enabled rather than duplicated. The legacy `SLMET-SANDBOX` connector and `SLMET-WEATHER-SCHEDULE` are deactivated when present.

## Climate Data Store

Longer-term climate analysis can use the Copernicus Climate Data Store (CDS). Catalogue readiness is exposed in CRAM, but downloading CDS datasets requires a CDS account/token and acceptance of the applicable dataset terms.

Set the token only in runtime configuration:

```env
COPERNICUS_CDS_KEY=<secret>
```

Never commit the value to Git or a distributable source archive.

## GIS basemap and reference layers

The GIS Explorer combines governed CRAM/PostGIS/GeoServer layers with optional public reference layers. If a public source is temporarily unavailable, governed CRAM GIS data continues to load.

The development/demo map uses the public OpenStreetMap standard tile service. This is suitable for low-volume validation only. Production deployment should use an approved tile provider or a self-hosted tile service and comply with the selected provider's usage policy.

## Governance rules

- Public connector output is labelled `PUBLIC_REFERENCE`.
- Public API failures never silently replace governed data.
- Flood screens expose rainfall and spatial context but do not calculate a flood-risk score unless an approved methodology is configured.
- World Bank indicators are contextual inputs only; CRAM does not invent an institutional vulnerability index.
- Earth-observation catalogue hits are discoverability metadata, not automatically approved CRAM layers.
- Publishing a newer dataset version supersedes the previously published version, preserving history and auditability.

## Session handling

Authenticated CRAM screens are protected by a session guard. The current idle timeout is 30 minutes. User activity refreshes the idle timestamp, and access tokens can refresh transparently while the session remains active. On idle timeout or failed refresh, CRAM clears the browser session and redirects to `/login?reason=expired` with an explicit session-expired message.

## Validation checklist

1. Log in as an authorized CRAM user.
2. Open **Processing** and select **Configure public connectors**.
3. Confirm the legacy sandbox connector/schedule is inactive and the public connectors are active.
4. Run due schedules; confirm integration runs transition to `SUCCEEDED` or expose a meaningful source-specific failure.
5. Open **GIS Explorer** and confirm the basemap loads and governed layers remain usable even if a public reference source fails.
6. Open **Heat** and confirm Open-Meteo/NASA POWER reference sections return values.
7. Open **Flood** and confirm rainfall/waterway context is shown without an invented risk classification.
8. Open **Trees** and confirm OSM reference tree features when present.
9. Open **Vulnerability** and confirm World Bank indicators are clearly labelled national public reference inputs.
10. Open **Advanced Analytics** and confirm Copernicus/USGS catalogue results and CDS readiness.
11. Allow the browser session to exceed the configured idle timeout (or test with a temporarily shorter local timeout) and confirm automatic logout/redirect.
