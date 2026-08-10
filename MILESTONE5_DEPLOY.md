# CRAM Milestone 5 Deployment Bundle

Copy this bundle over the repository root, preserving paths and overwriting the included files only.

Then run:

```bash
cd /opt/cram/source/cram-platform
chmod +x infrastructure/scripts/milestone5-deploy-test.sh
./infrastructure/scripts/milestone5-deploy-test.sh
```

The script generates development-only authentication secrets inside the already ignored `.env` when they do not yet exist. It does not commit them.

When the local acceptance script passes, create the Milestone 5 feature branch/commit/PR and let the existing five required CI gates run.

The final institutional permission matrix remains subject to stakeholder approval. This bundle implements only the flexible Milestone 5 authorization framework and placeholder RBAC matrix already required by the roadmap.
