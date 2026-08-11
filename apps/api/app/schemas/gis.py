from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel


class SpatialLayerResponse(BaseModel):
    id: uuid.UUID
    dataset_version_id: uuid.UUID | None
    name: str
    workspace: str | None
    store_name: str | None
    layer_name: str | None
    geometry_type: str | None
    srid: int | None
    description: str | None
    created_at: datetime
    updated_at: datetime


class GeographicAreaResponse(BaseModel):
    id: uuid.UUID
    parent_id: uuid.UUID | None
    code: str
    name: str
    area_type: str
    metadata: dict[str, object]
    geometry: dict[str, object] | None
    centroid: dict[str, object] | None
