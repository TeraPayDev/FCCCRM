from __future__ import annotations

from geoalchemy2.elements import WKTElement
from sqlalchemy import select

from app.db.session import get_session_factory
from app.models.gis import GeographicArea, SpatialLayer

SAMPLE_CODE = "CRAM-SAMPLE-AREA"
SAMPLE_LAYER = "CRAM Sample Area"


def seed_gis_sample() -> None:
    """Seed a synthetic geometry for architecture verification only.

    This is deliberately not an official Freetown planning hierarchy or authoritative boundary.
    """
    factory = get_session_factory()
    with factory() as session, session.begin():
        area = session.scalar(select(GeographicArea).where(GeographicArea.code == SAMPLE_CODE))
        if area is None:
            area = GeographicArea(
                code=SAMPLE_CODE,
                name="CRAM Synthetic GIS Acceptance Area",
                area_type="sample",
                geometry=WKTElement(
                    "MULTIPOLYGON(((-13.30 8.40,-13.20 8.40,-13.20 8.50,-13.30 8.50,-13.30 8.40)))",
                    srid=4326,
                ),
                centroid=WKTElement("POINT(-13.25 8.45)", srid=4326),
                area_metadata={
                    "synthetic": True,
                    "authoritative": False,
                    "purpose": "Milestone 8 architecture verification",
                },
            )
            session.add(area)
        layer = session.scalar(select(SpatialLayer).where(SpatialLayer.name == SAMPLE_LAYER))
        if layer is None:
            session.add(
                SpatialLayer(
                    name=SAMPLE_LAYER,
                    workspace="cram",
                    store_name="cram_postgis",
                    layer_name="geographic_areas",
                    geometry_type="MultiPolygon",
                    srid=4326,
                    description="Synthetic CRAM acceptance layer; not an authoritative administrative boundary.",
                )
            )


if __name__ == "__main__":
    seed_gis_sample()
    print("CRAM synthetic GIS acceptance data ready.")
