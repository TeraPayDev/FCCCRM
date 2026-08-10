# CRAM RBAC Seed Matrix v0.1

This is the Milestone 5 placeholder permission matrix. It is deliberately data-driven and may be changed without rewriting endpoint authorization logic. The final institutional permission matrix remains subject to stakeholder approval.

## Permission namespaces

- `users.read`, `users.manage`
- `datasets.read`, `datasets.manage`
- `gis.read`, `gis.manage`
- `analytics.read`, `analytics.manage`
- `citizen_reports.read`, `citizen_reports.manage`
- `reports.read`, `reports.manage`
- `audit.read`

## Placeholder role matrix

| Role | Placeholder permissions |
| --- | --- |
| System Administrator | All Milestone 5 permission namespaces |
| FCC Administrator | All Milestone 5 permission namespaces |
| Data Steward | datasets read/manage; GIS read/manage; analytics read; reports read; audit read |
| Climate Analyst | datasets read; GIS read; analytics read/manage; reports read/manage |
| Agency Analyst | datasets read; GIS read; analytics read; reports read |
| Executive User | datasets read; GIS read; analytics read; reports read |
| Public User | None of the protected Milestone 5 permissions |

## Authorization rule

Protected endpoints depend on permission codes such as `users.read`. They do not authorize by comparing a hard-coded role name.

## Account controls

- Passwords are stored only as modern password hashes using `pwdlib` recommended hashing.
- Access and refresh JWTs are distinct token types.
- Expiration is enforced during JWT decoding.
- Logout increments a per-user token version, revoking existing access and refresh tokens.
- Disabled accounts cannot authenticate.
- Repeated invalid logins trigger a temporary account lock.
