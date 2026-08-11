from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query

from app.db.session import get_db_session
from app.models.identity import User
from app.schemas.gis import GeographicAreaResponse, SpatialLayerResponse
from app.security.dependencies import require_permission
from app.services.gis import list_geographic_areas, list_spatial_layers

router = APIRouter(prefix="/gis", tags=["gis"])
GISReader = Annotated[User, Depends(require_permission("gis.read"))]


@router.get("/layers", response_model=list[SpatialLayerResponse])
def spatial_layers(_: GISReader) -> list[SpatialLayerResponse]:
    session = get_db_session()
    try:
        return [
            SpatialLayerResponse.model_validate(item, from_attributes=True)
            for item in list_spatial_layers(session)
        ]
    finally:
        session.close()


@router.get("/areas", response_model=list[GeographicAreaResponse])
def geographic_areas(
    _: GISReader,
    area_type: str | None = None,
    bbox: Annotated[str | None, Query(description="minx,miny,maxx,maxy in EPSG:4326")] = None,
) -> list[GeographicAreaResponse]:
    parsed_bbox: tuple[float, float, float, float] | None = None
    if bbox:
        try:
            values = tuple(float(value.strip()) for value in bbox.split(","))
            if len(values) != 4:
                raise ValueError
            parsed_bbox = (values[0], values[1], values[2], values[3])
        except ValueError as exc:
            raise HTTPException(status_code=422, detail="bbox must be minx,miny,maxx,maxy") from exc
    session = get_db_session()
    try:
        return [
            GeographicAreaResponse.model_validate(item)
            for item in list_geographic_areas(session, area_type=area_type, bbox=parsed_bbox)
        ]
    finally:
        session.close()
