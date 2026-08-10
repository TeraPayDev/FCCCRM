# CRAM Milestone 6 Deployment Bundle

This bundle contains only the files affected by **Milestone 6 - Organisations and Institutional Ownership**.

Copy the bundle over the repository root, preserving paths and overwriting the included files only.

Then run:

```bash
cd /opt/cram/source/cram-platform
chmod +x infrastructure/scripts/milestone6-deploy-test.sh
./infrastructure/scripts/milestone6-deploy-test.sh
```

Milestone 6 deliberately reuses the database relationships established in Milestone 4:

- `users.organisation_id`
- `datasets.owner_organisation_id`
- `dataset_sources.provider_organisation_id`

Therefore this milestone does **not** introduce a new schema migration. The existing migration head remains `20260810_0002` from Milestone 5.

The implementation does not introduce Milestone 7 audit behavior, Milestone 9 dataset catalogue APIs/UI, Milestone 12 approval workflow, or other later roadmap functionality.

After local acceptance passes, perform the normal controlled closeout: feature branch, commit, push, PR into `main`, required CI checks, merge, synchronize `main`, then update the roadmap/completion report.
