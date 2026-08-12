# CRAM TOR-aligned decision-support UI extension

This extension turns the engineering-oriented prototype into a decision-support demonstration aligned to the FCC CRAM Terms of Reference while preserving CRAM's governance boundary between live public reference data and authoritative institutional data.

## Implemented presentation capabilities

- Executive dashboard with live temperature, humidity, rainfall, citizen-report, processing and spatial-reference KPIs.
- Real time-series charts from Open-Meteo and NASA POWER rather than static demonstration values.
- Freetown temperature and precipitation heat surfaces using multiple real Open-Meteo grid cells.
- Integrated GIS Explorer with independent layer controls for temperature, rainfall, mapped trees, waterways, administrative boundaries and governed CRAM layers.
- Tree distribution mapping from OpenStreetMap reference points, ready to combine with FCC tree registry, catchments, inspections and survival records.
- Flood monitoring with rainfall charts and precipitation heat surface over mapped waterways; no flood-probability metric is fabricated without an approved methodology and authoritative zone/incident inputs.
- Vulnerability context from World Bank indicators, with a methodology-gated workflow for future Stats-SL/NaCSA spatial vulnerability indices.
- Long-term climate trend charts using historical Open-Meteo and NASA POWER data and Earth-observation catalogue visibility for Copernicus and USGS.
- User & Access Management for role-specific demonstration accounts and partner institutions.
- Permission-aware navigation based on the authenticated user's CRAM permission claims.
- Existing 30-minute inactivity session guard and refresh-token handling retained.
- NASA POWER missing-data sentinel values are normalized to null rather than displayed as valid measurements.
- Legacy SLMET sandbox connector/schedule is retired by migration while its historical audit evidence is preserved.

## Role demonstration matrix

| Role | Suggested demo purpose |
|---|---|
| System Administrator / FCC Administrator | Full platform administration, identity, approvals, audit and operations |
| Data Steward | Dataset registration, upload, validation and governance |
| Climate Analyst | Heat, flood, vulnerability, GIS and advanced analytics |
| Agency Analyst | Partner-agency data consumption, GIS and reporting |
| Executive User | Executive dashboard, GIS and reports |
| Public User | Public citizen-hazard submission route |

## Governance boundary

Live public feeds are explicitly presented as **public reference**. They are useful for a working prototype and situational awareness, but they do not automatically become authoritative FCC indicators. Official heat exposure, flood probability, vulnerability, tree survival and related operational indicators should be produced only from governed datasets and approved methodologies.

## Runtime validation after merge

Run the normal backend and frontend quality gates, apply Alembic migrations, rebuild API/web/worker, then:

1. Sign in as administrator and open **User Management**.
2. Create a Climate Analyst, Executive User and Data Steward account and verify permission-aware navigation.
3. Open **Dashboards** and confirm live KPI cards plus temperature/rainfall charts.
4. Open **Heat** and verify the temperature surface plus Open-Meteo/NASA charts.
5. Open **Flood** and verify precipitation heatmap plus OSM waterways.
6. Open **Trees** and verify mapped OSM tree points.
7. Open **GIS Explorer** and toggle individual layers independently.
8. Open **Vulnerability** and confirm World Bank context remains separate from governed vulnerability outputs.
9. Open **Processing**, choose **Configure public connectors**, and verify active public connector schedules while legacy SLMET sandbox rows remain inactive/history only.
10. Configure `COPERNICUS_CDS_KEY` in the server `.env` and confirm Advanced Analytics reports CDS status as READY.
