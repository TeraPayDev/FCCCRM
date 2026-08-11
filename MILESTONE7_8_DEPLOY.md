# CRAM Milestones 7 + 8 Deployment

Run `./infrastructure/scripts/milestone7-8-deploy-test.sh` from the repository root after configuring `.env` with the existing authentication/database settings and GeoServer administrator settings.

The combined cycle keeps two independent gates: Milestone 7 validates append-only audit behavior and read-only audit access; Milestone 8 validates PostGIS geometry, spatial filtering, GeoServer availability/publication prerequisites, and the MapLibre viewer. The GIS acceptance geometry is synthetic and non-authoritative.
