from __future__ import annotations

import uuid

from geoalchemy2 import Geometry
from sqlalchemy import ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class GeographicArea(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "geographic_areas"
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("cram.geographic_areas.id", ondelete="SET NULL"),
        nullable=True,
    )
    code: Mapped[str] = mapped_column(String(120), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(240), nullable=False)
    area_type: Mapped[str] = mapped_column(String(100), nullable=False)
    geometry: Mapped[object | None] = mapped_column(
        Geometry("MULTIPOLYGON", srid=4326, spatial_index=False), nullable=True
    )
    centroid: Mapped[object | None] = mapped_column(
        Geometry("POINT", srid=4326, spatial_index=False), nullable=True
    )
    area_metadata: Mapped[dict[str, object]] = mapped_column(
        JSONB, nullable=False, default=dict, server_default="{}"
    )
    __table_args__ = (
        Index("ix_geographic_areas_parent_id", "parent_id"),
        Index("ix_geographic_areas_area_type", "area_type"),
        Index("ix_geographic_areas_geometry_gist", "geometry", postgresql_using="gist"),
    )


class SpatialLayer(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "spatial_layers"
    dataset_version_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("cram.dataset_versions.id", ondelete="SET NULL"),
        nullable=True,
    )
    name: Mapped[str] = mapped_column(String(240), nullable=False)
    workspace: Mapped[str | None] = mapped_column(String(160), nullable=True)
    store_name: Mapped[str | None] = mapped_column(String(160), nullable=True)
    layer_name: Mapped[str | None] = mapped_column(String(240), nullable=True)
    geometry_type: Mapped[str | None] = mapped_column(String(80), nullable=True)
    srid: Mapped[int | None] = mapped_column(Integer, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    __table_args__ = (
        Index("ix_spatial_layers_dataset_version_id", "dataset_version_id"),
        Index("ix_spatial_layers_name", "name"),
    )
