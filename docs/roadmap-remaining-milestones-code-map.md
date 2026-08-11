# CRAM Remaining Milestones Code Map (Roadmap v1.8 Unchanged)

This implementation pack does not edit, renumber, reorder, or mark complete any item in the approved CRAM Engineering Roadmap v1.8. It adds source-code foundations for Milestones 13 through 26 while preserving the roadmap's acceptance gates and external-dependency rules. A milestone remains incomplete until its own acceptance criteria are demonstrated in the target environment.

## Milestone 13 — ETL / Processing Framework

Implemented: durable `ProcessingJob` and `ProcessingJobLog` models; standard stages; idempotency key; retries/failure state; database-backed worker queue using PostgreSQL `FOR UPDATE SKIP LOCKED`; pluggable processor registry; job API; worker container; structured logs. The existing Redis service is retained as infrastructure but is not required by the worker queue.

## Milestone 14 — Heat Vertical Slice

Implemented: `WeatherObservation`, `HeatIndicator`, weather CSV processor, time-series/filter API, source-version provenance, methodology version fields, and Heat UI surface. No scientific heat formula is invented. Indicator creation requires a methodology version; authoritative geographic aggregation and spatial heat methodology remain governed external dependencies.

## Milestone 15 — MVP Integration Gate

No roadmap gate is auto-passed by code. The source contains the complete route chain needed to demonstrate Authentication → Organisation/RBAC → Catalogue → Upload → Validation → Approval → ETL → GIS → Heat → Dashboard → Audit, but deployment/UAT evidence must still be produced before the gate can be marked complete.

## Milestone 16 — Flood

Implemented: flood incident, zone, and risk-indicator models; CSV processors for incidents and WKT flood zones; read APIs and UI surface; source-version and methodology provenance. Flood probability is deliberately not implemented until the approved model/methodology and thresholds exist.

## Milestone 17 — Trees

Implemented: tree, species, planting batch, catchment, and inspection models; registry and inspection CSV processors; longitudinal inspection preservation; read APIs and UI surface. Survival/canopy formulas are not invented; the approved denominator and remote-sensing methodology remain required.

## Milestone 18 — Vulnerability

Implemented: socio-economic and vulnerability indicator models; socio-economic CSV processor; provenance fields; read APIs and UI surface. Composite weighting/normalization is not implemented without the approved vulnerability methodology.

## Milestone 19 — Citizen Reporting

Implemented: public citizen report API; GPS point support; privacy-separated personal fields; moderation lifecycle; JPEG/PNG attachment upload with type and size controls; assignment model/API; public visibility endpoint; audit events; responsive UI surface. Stakeholder policy remains required for anonymous/registered reporting and final moderation/privacy rules.

## Milestone 20 — Notifications

Implemented: separate `Alert` and `Notification` records; in-app delivery records; user notification API; read state; resource link fields; delivery status/error fields. Email/SMS providers are intentionally not hard-coded pending approved provider, budget, privacy, and workflow decisions.

## Milestone 21 — Dashboards

Implemented: permission-aware dashboard definitions, seeded role-facing dashboard entries, dashboard API, shared frontend module shell/filter-ready layout, module routes, source-aware data views, and server-side permission filtering. Domain calculations remain in backend services rather than React.

## Milestone 22 — Reporting

Implemented: report model with parameters/requester/source dataset versions/file reference; background report processor; report history API/UI; audit event; original artifacts stored in S3-compatible storage. CSV is enabled immediately. PDF/XLSX templates remain gated by the roadmap's approved-output requirement rather than guessed.

## Milestone 23 — Knowledge Hub

Implemented: content metadata model, tags, ownership/visibility, links to datasets/reports, permission-aware search/retrieval APIs, public endpoint, and UI surface.

## Milestone 24 — Administration and Operations

Implemented: controlled non-secret settings model/API, processing-job operational view, dashboard seed/control surfaces, audited setting changes, and backup/restore scripts. Existing identity, organisation, dataset, GIS, approval, notification, and audit administration APIs remain reusable control-plane components.

## Milestone 25 — Advanced Analytics

Implemented: versioned methodology registry, model-run and scenario-run persistence foundations, assumptions/validation/uncertainty fields, and methodology API/UI. No predictive model is presented as authoritative or executed without an approved methodology and suitable data.

## Milestone 26 — Production Hardening

Implemented in code: security headers, API safety-net rate limiting, stricter citizen upload handling, durable worker retries, backup and restore scripts, and secret-safe packaging. Production completion still requires environment-specific vulnerability scanning, penetration testing, load testing, RPO/RTO agreement, backup-restore demonstration, monitoring/alerting validation, UAT, deployment/rollback sign-off, training, and FCC handover.

## External dependencies intentionally not invented

The code intentionally leaves the following as governed configuration/approval dependencies: authoritative geographic boundaries/CRS, heat methodology/thresholds, flood probability model, vulnerability normalization/weights, tree survival/canopy methodology, citizen privacy/moderation rules, final RBAC/approval matrix, production cloud/data-residency/RPO/RTO/MFA/SSO decisions, and report/knowledge-hub templates.


## Post-Milestone-26 engineering extension

The completed Milestones 0-26 baseline is preserved. Additional production-readiness engineering is implemented as Extensions 27-32:

- Predictive/scenario engines: `apps/api/app/services/predictive.py` and `/api/v1/analytics/predict/*`.
- Mobile/offline citizen reporting: `apps/web/src/pages/CitizenReportPage.tsx` at `/report-hazard`.
- ETL scheduling/monitoring: `processing_schedules`, worker scheduling, `/api/v1/processing/schedules`, `/api/v1/processing/monitoring`.
- Reporting/executive: authenticated report download and `/api/v1/dashboards/executive-summary`.
- Production readiness: `load-smoke.py`, `disaster-recovery-drill.sh`, and operations guidance.
- Institutional sandbox adapters: `integration_connectors`, `integration_runs`, and `/api/v1/integrations/connectors`.
- Schema migration: `20260811_0006_engineering_extension.py`.

Live institutional activation, scientific calibration/approval, production HA topology, formal load targets and isolated DR acceptance remain governed external/environment gates.
