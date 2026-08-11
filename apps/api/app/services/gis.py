from __future__ import annotations

import json

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.gis import GeographicArea, SpatialLayer


def list_spatial_layers(session: Session) -> list[SpatialLayer]:
    return list(session.scalars(select(SpatialLayer).order_by(SpatialLayer.name)).all())


def list_geographic_areas(
    session: Session,
    *,
    area_type: str | None = None,
    bbox: tuple[float, float, float, float] | None = None,
) -> list[dict[str, object]]:
    query = select(
        GeographicArea,
        func.ST_AsGeoJSON(GeographicArea.geometry),
        func.ST_AsGeoJSON(GeographicArea.centroid),
    )
    if area_type:
        query = query.where(GeographicArea.area_type == area_type)
    if bbox:
        minx, miny, maxx, maxy = bbox
        envelope = func.ST_MakeEnvelope(minx, miny, maxx, maxy, 4326)
        query = query.where(func.ST_Intersects(GeographicArea.geometry, envelope))
    rows = session.execute(query.order_by(GeographicArea.name)).all()
    result: list[dict[str, object]] = []
    for area, geometry_json, centroid_json in rows:
        result.append(
            {
                "id": area.id,
                "parent_id": area.parent_id,
                "code": area.code,
                "name": area.name,
                "area_type": area.area_type,
                "metadata": area.area_metadata,
                "geometry": json.loads(geometry_json) if geometry_json else None,
                "centroid": json.loads(centroid_json) if centroid_json else None,
            }
        )
    return result
