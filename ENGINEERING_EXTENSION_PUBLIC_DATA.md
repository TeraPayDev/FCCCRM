# CRAM Public Data, GIS, ETL and Session Hardening Extension

This source package extends the tested CSV-ingestion baseline with:

- live/reference Open-Meteo weather and multi-year history;
- NASA POWER meteorological history;
- OpenStreetMap Overpass tree, waterway and administrative-boundary references;
- World Bank Sierra Leone indicator references;
- Copernicus Data Space Sentinel-2 STAC catalogue discovery;
- USGS Landsat STAC catalogue discovery;
- Copernicus Climate Data Store credential/readiness support;
- real public connector bootstrap, scheduled `PUBLIC_CONNECTOR_SYNC` jobs, integration-run history, retry/status tracking and legacy sandbox deactivation;
- GIS basemap/reference-layer integration with independent failure handling so external outages do not blank governed CRAM GIS data;
- Heat, Flood, Tree, Vulnerability and Advanced Analytics live-reference UI surfaces;
- dataset publishing lifecycle hardening: publishing a newer version supersedes the previous published version;
- protected-route session guard with 30-minute idle timeout, transparent access-token refresh while active, and redirect to login on timeout/failed refresh;
- automated unit coverage for public-data normalization, lifecycle superseding and browser session timeout state;
- operational integration and runtime test documentation.

## Governance boundary

Public sources are deliberately labelled as reference data. They do not become authoritative FCC/agency data merely because an API call succeeds. Governing institutional data still follows CRAM's dataset version, validation, approval and publication lifecycle. Flood/vulnerability scores are not fabricated without approved methodologies.

## External configuration

Only Copernicus CDS programmatic downloads need an additional server-side credential:

```env
COPERNICUS_CDS_KEY=<personal-access-token>
```

The public Open-Meteo, NASA POWER, World Bank, Overpass, Copernicus STAC and USGS STAC adapters require no secret in this package. Runtime internet/DNS access is required.
