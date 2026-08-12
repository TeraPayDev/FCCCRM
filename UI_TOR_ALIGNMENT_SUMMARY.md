# CRAM prototype upgrade — TOR alignment summary

The web presentation layer has been upgraded from table-first engineering surfaces to a decision-support prototype with live charts, spatial heat surfaces, role-based navigation and user administration.

Key new source files:

- `apps/web/src/components/analytics/Charts.tsx`
- `apps/web/src/components/analytics/ClimateMap.tsx`
- `apps/web/src/pages/UserManagementPage.tsx`
- updated `DashboardsPage.tsx`, `MapPage.tsx`, `RoadmapModulePage.tsx`, `AppLayout.tsx`
- `apps/api/app/api/v1/endpoints/users.py`
- `apps/api/app/services/users.py`
- `apps/api/app/schemas/users.py`
- migration `20260812_0008_retire_legacy_sandbox.py`

See `docs/ui/tor-aligned-decision-support-ui.md` for the runtime demo checklist and governance boundary.
