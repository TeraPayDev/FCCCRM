# CRAM Milestones 9-12 deployment and acceptance

Run from repository root:

```bash
chmod +x infrastructure/scripts/milestone9-12-deploy-test.sh
./infrastructure/scripts/milestone9-12-deploy-test.sh
```

The script verifies backend/frontend quality, container rebuild, migration `20260811_0004`, RBAC seed updates, catalogue metadata, CSV ingestion/object preservation, validation results, lifecycle controls, audit events, and final migration/service state.

The sample CSV is controlled synthetic acceptance data and is not an official SL-Met contract.
