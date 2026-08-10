# CRAM Definition of Done

This Definition of Done implements the engineering quality gate defined in the CRAM roadmap.

A development task may be marked complete only when the conditions relevant to that task are satisfied.

## Roadmap and scope

- The work belongs to the current roadmap milestone, or is an explicitly recorded blocker.
- The task satisfies the acceptance criterion it was intended to address.
- Later-milestone features have not been introduced silently.

## Code quality

- Frontend linting passes for frontend changes.
- Frontend formatting checks pass for frontend changes.
- Frontend TypeScript type checking passes for frontend changes.
- Frontend automated tests pass for frontend changes.
- Backend Ruff linting passes for backend changes.
- Backend Ruff formatting checks pass for backend changes.
- Backend mypy type checking passes for backend changes.
- Backend Pytest tests pass for backend changes.

## Database changes

- When Alembic migrations exist, migration validation must pass in CI.
- A migration failure is a failed quality gate.
- Schema changes are not considered complete without the migration required by the applicable roadmap milestone.

## Containers

- API and web Docker images build successfully in CI when their build context changes.

## Security and dependencies

- No runtime `.env` file, credential, secret, or production access token is committed.
- Dependency/security scan results are reviewed.
- Known high-impact dependency findings are resolved or explicitly recorded before merge.

## Documentation and review

- Relevant API, operational, architecture, or developer documentation is updated.
- The pull-request checklist is completed.
- The change has been reviewed before merge.
- Required CI checks are green.

## Completion rule

A task is **not done** when it merely works on one developer machine. It is done when the applicable automated checks pass, documentation is current, the change has been reviewed, and the current roadmap acceptance criterion is satisfied.
