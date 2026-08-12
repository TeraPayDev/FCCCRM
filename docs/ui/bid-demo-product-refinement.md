# CRAM Bid-Demo Product Refinement

This package refines the CRAM implementation into a demonstration-oriented but governance-safe climate-risk decision-support experience. It preserves the established data lifecycle and public-reference/governed-data distinction while making the workflows more intuitive for FCC users.

## Major user-facing changes

- Public Citizen Hazard Reporting is now a responsive, offline-capable guided form with hazard selection, GPS, photo evidence, queue status and clear privacy messaging.
- User & Access Management now uses a searchable account grid plus dedicated create/edit pages. Roles and institutions remain API-driven and audit-backed.
- The top-right account control is a compact profile menu with direct sign-out, profile, system status and permission-aware access-management links.
- Reporting is now a functional Climate Risk Report Builder with purpose-defined templates, geography/date/module parameters, asynchronous job creation, report history and completed-output download.
- Generated CSV reports include a governed CRAM snapshot plus report parameters and provenance rather than only raw identifiers.
- Knowledge Hub can create governed knowledge items and retrieve climate-risk publications from the public World Bank Documents & Reports API. External resources remain clearly labelled until explicitly saved to CRAM.
- Dataset Approval has a conventional Data Catalogue action, stronger statuses and clearer decision controls.
- Audit Trail removes the unrelated Profile shortcut and adds practical filters, refresh/reset and readable detail expansion.
- Advanced Analytics now displays observed-versus-forecast temperature with a residual uncertainty band, trend direction, slope and model-fit information.
- Dashboard/chart/map motion is restrained and supports `prefers-reduced-motion`.
- GIS Explorer retains independently switchable heat/rainfall/tree/waterway/boundary/governed layers with provenance and feature popups.

## Copernicus CDS deployment

The API and worker containers now receive both of these server-side variables:

```text
COPERNICUS_CDS_URL=https://cds.climate.copernicus.eu/api
COPERNICUS_CDS_KEY=<personal-access-token>
```

The personal access token is never exposed to the browser. After setting/changing the server `.env`, rebuild/recreate `api` and `worker`. The CDS readiness tile should then show `READY`. Dataset-specific terms still need to be accepted in the CDS account before first retrieval of a protected dataset.

## Demo flow

1. Sign in as System Administrator and show the permission-aware navigation/profile menu.
2. Open Executive Climate Dashboard and demonstrate live climate charts and the integrated map.
3. Open GIS Explorer and toggle temperature, rainfall, trees, waterways and governed layers.
4. Open Heat, Flood, Trees and Vulnerability to demonstrate live/public reference data and governed output boundaries.
5. Open Advanced Analytics and run the 14-period heat trend forecast. Explain that the engineering model is intentionally labelled as non-operational until an approved methodology is registered.
6. Open Data Catalogue and demonstrate governed upload/validate/approve/publish lifecycle.
7. Open User Management, create a role-specific user, edit the user, and demonstrate role-aware navigation.
8. Open Reporting, generate an Executive Climate Risk Brief, wait for the worker to complete it, refresh, and download the CSV.
9. Open Knowledge Hub, refresh World Bank resources, open one source, then save a selected reference into CRAM.
10. Open the public `/report-hazard` route, demonstrate offline status, GPS/photo options and submission/queue behavior.

## Governance rule

Public weather, OSM, World Bank, satellite catalogue and other external feeds are situational/reference data unless they enter the governed CRAM lifecycle. The UI must not represent an engineering forecast or public reference layer as an approved FCC risk indicator.
