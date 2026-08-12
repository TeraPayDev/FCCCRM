from __future__ import annotations

from collections.abc import Callable
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from app.models.identity import User
from app.security.dependencies import require_permission
from app.services.public_data import (
    PublicDataError,
    copernicus_cds_readiness,
    copernicus_stac_freetown,
    gis_reference_features,
    nasa_power_freetown,
    open_meteo_freetown,
    open_meteo_freetown_grid,
    open_meteo_historical_freetown,
    osm_freetown,
    usgs_stac_freetown,
    world_bank_climate_resources,
    world_bank_sierra_leone,
)

router = APIRouter(prefix="/public-data", tags=["public-reference-data"])
AnalyticsReader = Annotated[User, Depends(require_permission("analytics.read"))]
GISReader = Annotated[User, Depends(require_permission("gis.read"))]
ReportsReader = Annotated[User, Depends(require_permission("reports.read"))]


def _safe(loader: Callable[[], dict[str, object]]) -> dict[str, object]:
    try:
        return loader()
    except PublicDataError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.get("/weather/open-meteo")
def weather_open_meteo(_: AnalyticsReader) -> dict[str, object]:
    return _safe(open_meteo_freetown)


@router.get("/weather/history")
def weather_history(_: AnalyticsReader) -> dict[str, object]:
    return _safe(open_meteo_historical_freetown)


@router.get("/weather/grid")
def weather_grid(_: AnalyticsReader) -> dict[str, object]:
    return _safe(open_meteo_freetown_grid)


@router.get("/climate/copernicus-cds")
def climate_copernicus_cds(_: AnalyticsReader) -> dict[str, object]:
    return copernicus_cds_readiness()


@router.get("/weather/nasa-power")
def weather_nasa_power(_: AnalyticsReader) -> dict[str, object]:
    return _safe(nasa_power_freetown)


@router.get("/spatial/osm")
def spatial_osm(_: AnalyticsReader) -> dict[str, object]:
    return _safe(osm_freetown)


@router.get("/vulnerability/world-bank")
def vulnerability_world_bank(_: AnalyticsReader) -> dict[str, object]:
    return _safe(world_bank_sierra_leone)


@router.get("/knowledge/world-bank")
def knowledge_world_bank(_: ReportsReader) -> dict[str, object]:
    return _safe(world_bank_climate_resources)


@router.get("/earth-observation/copernicus")
def earth_observation_copernicus(_: AnalyticsReader) -> dict[str, object]:
    return _safe(copernicus_stac_freetown)


@router.get("/earth-observation/usgs")
def earth_observation_usgs(_: AnalyticsReader) -> dict[str, object]:
    return _safe(usgs_stac_freetown)


@router.get("/gis/reference")
def gis_reference(_: GISReader) -> dict[str, object]:
    return _safe(gis_reference_features)
