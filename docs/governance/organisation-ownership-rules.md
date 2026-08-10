# CRAM Organisation Ownership Rules

## Milestone 6 scope

Milestone 6 represents FCC and the approved partner institutions as first-class governance entities. It does not implement the later dataset catalogue, approval workflow, audit framework, or GIS publishing milestones.

## Seeded institutions

The controlled seed set remains:

- FCC — Freetown City Council
- NaCSA — NaCSA
- NDMA — NDMA
- SL-Met — SL-Met
- Stats-SL — Statistics Sierra Leone
- ONS — ONS

## Ownership relationships

- `users.organisation_id` identifies the institution to which a user is currently linked. The relationship is nullable so an account can exist before institutional assignment is finalized.
- `datasets.owner_organisation_id` identifies the institution that owns/governs a dataset. This field is required by the database foundation.
- `dataset_sources.provider_organisation_id` identifies the institution that provides a dataset source. It may be null when the provider is not yet known.
- Organisation codes are treated as stable integration identifiers. Administrative updates change the display name or active state rather than silently rewriting the code.

## Administration behavior

Organisation administration endpoints require the existing `users.read` or `users.manage` permissions. This keeps Milestone 6 inside the permission-based RBAC framework established in Milestone 5 and avoids hard-coded role-name authorization.

An organisation that is no longer operational should normally be deactivated. Hard deletion is allowed only when database constraints permit it; referenced ownership records intentionally prevent unsafe deletion.

Users may be assigned or unassigned from organisations by an authorized administrator. Assignment to an inactive organisation is rejected.

## Organisation-aware permission and approval preparation

`organisation_scope_allows()` provides a reusable organisation-boundary check for later workflows. A caller supplies:

1. the permission code required for the operation;
2. the resource organisation ID; and
3. whether that specific workflow deliberately allows cross-organisation access.

The helper first requires the permission and, by default, also requires the user's organisation to match the resource organisation. It does not inspect role-name strings.

This prepares CRAM for organisation-aware review and approval logic without implementing Milestone 12 early. The final institutional RBAC and approval matrix remains subject to stakeholder approval.
