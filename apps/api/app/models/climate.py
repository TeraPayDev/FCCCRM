from __future__ import annotations

import uuid
from datetime import date, datetime

from geoalchemy2 import Geometry
from sqlalchemy import (
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class ProvenanceMixin:
    dataset_version_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("cram.dataset_versions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    methodology_version: Mapped[str | None] = mapped_column(String(120), nullable=True)


class WeatherObservation(UUIDPrimaryKeyMixin, TimestampMixin, ProvenanceMixin, Base):
    __tablename__ = "weather_observations"
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    station_code: Mapped[str | None] = mapped_column(String(120), nullable=True)
    geographic_area_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("cram.geographic_areas.id", ondelete="SET NULL"),
        nullable=True,
    )
    temperature_c: Mapped[float | None] = mapped_column(Float, nullable=True)
    humidity_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    heat_index_c: Mapped[float | None] = mapped_column(Float, nullable=True)
    location: Mapped[object | None] = mapped_column(
        Geometry("POINT", srid=4326, spatial_index=False), nullable=True
    )
    source_row_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    __table_args__ = (
        Index("ix_weather_observations_observed_at", "observed_at"),
        Index("ix_weather_observations_dataset_version_id", "dataset_version_id"),
        Index("ix_weather_observations_geographic_area_id", "geographic_area_id"),
        Index("ix_weather_observations_location_gist", "location", postgresql_using="gist"),
    )


class HeatIndicator(UUIDPrimaryKeyMixin, TimestampMixin, ProvenanceMixin, Base):
    __tablename__ = "heat_indicators"
    geographic_area_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("cram.geographic_areas.id", ondelete="SET NULL"),
        nullable=True,
    )
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    indicator_code: Mapped[str] = mapped_column(String(120), nullable=False)
    value: Mapped[float] = mapped_column(Float, nullable=False)
    unit: Mapped[str] = mapped_column(String(80), nullable=False)
    classification: Mapped[str | None] = mapped_column(String(120), nullable=True)
    methodology_metadata: Mapped[dict[str, object]] = mapped_column(
        JSONB, nullable=False, default=dict, server_default="{}"
    )
    __table_args__ = (
        Index("ix_heat_indicators_dataset_version_id", "dataset_version_id"),
        Index("ix_heat_indicators_period_start", "period_start"),
        Index("ix_heat_indicators_geographic_area_id", "geographic_area_id"),
    )


class FloodIncident(UUIDPrimaryKeyMixin, TimestampMixin, ProvenanceMixin, Base):
    __tablename__ = "flood_incidents"
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    geographic_area_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("cram.geographic_areas.id", ondelete="SET NULL"),
        nullable=True,
    )
    severity: Mapped[str | None] = mapped_column(String(80), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    location: Mapped[object | None] = mapped_column(
        Geometry("POINT", srid=4326, spatial_index=False), nullable=True
    )
    __table_args__ = (
        Index("ix_flood_incidents_dataset_version_id", "dataset_version_id"),
        Index("ix_flood_incidents_occurred_at", "occurred_at"),
        Index("ix_flood_incidents_location_gist", "location", postgresql_using="gist"),
    )


class FloodZone(UUIDPrimaryKeyMixin, TimestampMixin, ProvenanceMixin, Base):
    __tablename__ = "flood_zones"
    code: Mapped[str] = mapped_column(String(120), nullable=False)
    name: Mapped[str] = mapped_column(String(240), nullable=False)
    geometry: Mapped[object] = mapped_column(
        Geometry("MULTIPOLYGON", srid=4326, spatial_index=False), nullable=False
    )
    risk_class: Mapped[str | None] = mapped_column(String(120), nullable=True)
    __table_args__ = (
        UniqueConstraint("dataset_version_id", "code", name="uq_flood_zones_version_code"),
        Index("ix_flood_zones_geometry_gist", "geometry", postgresql_using="gist"),
    )


class FloodRiskIndicator(UUIDPrimaryKeyMixin, TimestampMixin, ProvenanceMixin, Base):
    __tablename__ = "flood_risk_indicators"
    geographic_area_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("cram.geographic_areas.id", ondelete="SET NULL"),
        nullable=True,
    )
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    indicator_code: Mapped[str] = mapped_column(String(120), nullable=False)
    value: Mapped[float] = mapped_column(Float, nullable=False)
    unit: Mapped[str] = mapped_column(String(80), nullable=False)
    classification: Mapped[str | None] = mapped_column(String(120), nullable=True)
    methodology_metadata: Mapped[dict[str, object]] = mapped_column(
        JSONB, nullable=False, default=dict, server_default="{}"
    )


class TreeSpecies(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "tree_species"
    code: Mapped[str] = mapped_column(String(120), nullable=False, unique=True)
    common_name: Mapped[str] = mapped_column(String(240), nullable=False)
    scientific_name: Mapped[str | None] = mapped_column(String(240), nullable=True)


class TreeCatchment(UUIDPrimaryKeyMixin, TimestampMixin, ProvenanceMixin, Base):
    __tablename__ = "tree_catchments"
    code: Mapped[str] = mapped_column(String(120), nullable=False)
    name: Mapped[str] = mapped_column(String(240), nullable=False)
    geometry: Mapped[object | None] = mapped_column(
        Geometry("MULTIPOLYGON", srid=4326, spatial_index=False), nullable=True
    )
    __table_args__ = (
        Index("ix_tree_catchments_geometry_gist", "geometry", postgresql_using="gist"),
    )


class TreePlantingBatch(UUIDPrimaryKeyMixin, TimestampMixin, ProvenanceMixin, Base):
    __tablename__ = "tree_planting_batches"
    batch_code: Mapped[str] = mapped_column(String(120), nullable=False)
    planted_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    catchment_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("cram.tree_catchments.id", ondelete="SET NULL"),
        nullable=True,
    )
    expected_tree_count: Mapped[int | None] = mapped_column(Integer, nullable=True)


class Tree(UUIDPrimaryKeyMixin, TimestampMixin, ProvenanceMixin, Base):
    __tablename__ = "trees"
    tree_code: Mapped[str] = mapped_column(String(160), nullable=False)
    species_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("cram.tree_species.id", ondelete="SET NULL"),
        nullable=True,
    )
    batch_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("cram.tree_planting_batches.id", ondelete="SET NULL"),
        nullable=True,
    )
    catchment_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("cram.tree_catchments.id", ondelete="SET NULL"),
        nullable=True,
    )
    planted_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    location: Mapped[object | None] = mapped_column(
        Geometry("POINT", srid=4326, spatial_index=False), nullable=True
    )
    __table_args__ = (
        UniqueConstraint("dataset_version_id", "tree_code", name="uq_trees_version_tree_code"),
        Index("ix_trees_location_gist", "location", postgresql_using="gist"),
    )


class TreeInspection(UUIDPrimaryKeyMixin, TimestampMixin, ProvenanceMixin, Base):
    __tablename__ = "tree_inspections"
    tree_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("cram.trees.id", ondelete="CASCADE"), nullable=False
    )
    inspected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String(60), nullable=False)
    height_m: Mapped[float | None] = mapped_column(Float, nullable=True)
    diameter_cm: Mapped[float | None] = mapped_column(Float, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    __table_args__ = (
        Index("ix_tree_inspections_tree_id", "tree_id"),
        Index("ix_tree_inspections_inspected_at", "inspected_at"),
    )


class SocioEconomicIndicator(UUIDPrimaryKeyMixin, TimestampMixin, ProvenanceMixin, Base):
    __tablename__ = "socio_economic_indicators"
    geographic_area_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("cram.geographic_areas.id", ondelete="RESTRICT"),
        nullable=False,
    )
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    indicator_code: Mapped[str] = mapped_column(String(120), nullable=False)
    value: Mapped[float] = mapped_column(Float, nullable=False)
    unit: Mapped[str] = mapped_column(String(80), nullable=False)


class VulnerabilityIndicator(UUIDPrimaryKeyMixin, TimestampMixin, ProvenanceMixin, Base):
    __tablename__ = "vulnerability_indicators"
    geographic_area_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("cram.geographic_areas.id", ondelete="RESTRICT"),
        nullable=False,
    )
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    value: Mapped[float] = mapped_column(Float, nullable=False)
    classification: Mapped[str | None] = mapped_column(String(120), nullable=True)
    methodology_metadata: Mapped[dict[str, object]] = mapped_column(
        JSONB, nullable=False, default=dict, server_default="{}"
    )
