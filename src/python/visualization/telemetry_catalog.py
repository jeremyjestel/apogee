"""Normalize completed timeline series for Rerun without reading analysis data."""

from dataclasses import dataclass

import numpy as np

from .rerun_paths import telemetry_series


TIME_AXIS_KINDS = {"time", "sequence"}
TIME_UNIT_TO_SECONDS = {"s": 1.0, "ms": 1e-3, "us": 1e-6, "ns": 1e-9}
SCALAR_SOURCE = "scalar"
VECTOR_SOURCE = "vector"


@dataclass(frozen=True, slots=True)
class TelemetryView:
    item: object
    entity: object | None
    axis: object
    coordinates: np.ndarray
    values: np.ndarray
    path: str
    source_type: str

    @property
    def owner_id(self):
        return self.entity.id if self.entity else 0

    @property
    def name(self):
        return self.item.name

    @property
    def unit(self):
        return self.item.unit


@dataclass(frozen=True, slots=True)
class TelemetryCatalog:
    entity_items: tuple
    axes: dict
    views: tuple[TelemetryView, ...]


def _values(series, source_type):
    if source_type == VECTOR_SOURCE:
        values = np.asarray(
            [[value.x, value.y, value.z] for value in series.values],
            dtype=np.float64,
        ).reshape((-1, 3))
    else:
        values = np.asarray(series.values, dtype=np.float64)
    values.setflags(write=False)
    return values


def build_telemetry_catalog(result):
    """Copy bound scene and telemetry collections exactly once."""

    entity_items = tuple(result.entities)
    entities = {entity.id: entity for entity in entity_items}
    if len(entities) != len(entity_items):
        raise ValueError("Entity ids must be unique")

    all_axes = {axis.key: axis for axis in tuple(result.axes)}
    axes = {
        key: axis for key, axis in all_axes.items() if axis.kind in TIME_AXIS_KINDS
    }
    coordinates = {}
    for key, axis in axes.items():
        if axis.kind == "time" and axis.unit not in TIME_UNIT_TO_SECONDS:
            raise ValueError(f"Unsupported time unit {axis.unit!r} for {key}")
        values = np.asarray(axis.values, dtype=np.float64)
        values.setflags(write=False)
        coordinates[key] = values

    views = []
    used_paths = set()
    for collection_name, source_type in (
        ("vectors", VECTOR_SOURCE),
        ("scalars", SCALAR_SOURCE),
    ):
        for series in tuple(getattr(result, collection_name)):
            if series.axis_key not in axes:
                raise ValueError(
                    f"Telemetry {series.system}/{series.key} requires a timeline axis"
                )
            entity = entities.get(series.entity_id)
            if series.entity_id and entity is None:
                raise ValueError(
                    f"Telemetry {series.system}/{series.key} references an unknown entity"
                )
            axis = axes[series.axis_key]
            series_values = _values(series, source_type)
            if len(series_values) != len(coordinates[axis.key]):
                raise ValueError(
                    f"Telemetry {series.system}/{series.key} does not match {axis.key}"
                )
            path = telemetry_series(entity, series)
            if path in used_paths:
                raise ValueError(f"Duplicate telemetry path: {path}")
            used_paths.add(path)
            if series_values.size:
                views.append(
                    TelemetryView(
                        item=series,
                        entity=entity,
                        axis=axis,
                        coordinates=coordinates[axis.key],
                        values=series_values,
                        path=path,
                        source_type=source_type,
                    )
                )

    return TelemetryCatalog(entity_items, axes, tuple(views))


def as_telemetry_catalog(value):
    return value if isinstance(value, TelemetryCatalog) else build_telemetry_catalog(value)
