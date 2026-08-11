# CRAM Production-Readiness Engineering Extension

This extension preserves Milestones 0-26 and adds engineering work that can be completed before institutional production integrations are available.

## Implemented controls
- Configurable predictive/scenario baseline engines for heat, flood, canopy and vulnerability. These are engineering engines, not approved scientific policy; coefficients/weights remain governed inputs.
- Database-backed ETL schedules, worker-side due-job enqueueing, retry backoff and processing monitoring.
- Sandbox connector framework for SL-Met, NDMA, NaCSA and Statistics Sierra Leone; live execution remains disabled until approved endpoints/credentials are supplied.
- Citizen mobile/offline queue, browser geolocation and image capture/upload workflow.
- Report generation remains asynchronous and source-version aware; executive dashboard surfaces are expanded by the UI workstream.
- Dependency-free HTTP load smoke probe and a controlled DR drill wrapper around the existing backup/restore assets.

## Production gates still requiring environment/stakeholder input
- Calibrate and formally approve scientific models/thresholds.
- Configure real institution endpoints, authentication and data-sharing rules.
- Execute load targets against production-sized infrastructure and datasets.
- Execute full restore into an isolated UAT/DR environment and record RTO/RPO.
- Configure external monitoring/alert delivery and HA topology appropriate to the production hosting decision.
