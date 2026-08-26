from dataclasses import dataclass
import math

import numpy as np

from .rerun_paths import analysis_product, data_child, plot_child, telemetry_series


TIME_AXIS_KINDS = frozenset({"time", "sequence"})
AXIS_KINDS = TIME_AXIS_KINDS | {"continuous"}
TIME_UNIT_TO_SECONDS = {
    "s": 1.0,
    "ms": 1.0e-3,
    "us": 1.0e-6,
    "ns": 1.0e-9,
}

TIME_SERIES_VIEW = "time_series"
SPATIAL_2D_VIEW = "spatial_2d"
SPATIAL_3D_VIEW = "spatial_3d"
TEXT_VIEW = "text"

SCALAR_SOURCE = "scalar"
VECTOR_SOURCE = "vector"
CURVE_SOURCE = "curve"
GRID_SOURCE = "grid"
SNAPSHOT_SOURCE = "snapshot"


@dataclass(frozen=True, slots=True)
class ProductRecord:
    """Normalized data returned by one semantic result-type reader."""

    item: object
    entity: object | None
    axis: object | None
    coordinates: object | None
    values: np.ndarray
    metadata: object | None
    section: str
    view_type: str
    source_type: str
    unit: str
    default_rank: int


@dataclass(frozen=True, slots=True)
class ViewSpec:
    """One validated result item and the Rerun view that presents it."""

    section: str
    view_type: str
    source_type: str
    item: object
    entity: object | None
    axis: object | None
    coordinates: object | None
    values: np.ndarray
    metadata: object | None
    base_path: str
    data_path: str
    plot_path: str
    name: str
    unit: str
    group: str
    order: int
    sequence: int

    @property
    def owner_id(self):
        return self.entity.id if self.entity is not None else 0

    @property
    def display_sort_key(self):
        # Zero means automatic placement after explicitly ordered products.
        return (self.order == 0, self.order, self.sequence)


@dataclass(frozen=True, slots=True)
class ViewCatalog:
    """Validated metadata shared by result logging and blueprint generation."""

    entity_items: tuple
    entities: dict
    axes: dict
    views: tuple[ViewSpec, ...]

    def in_section(self, section):
        return tuple(view for view in self.views if view.section == section)


@dataclass(frozen=True, slots=True)
class CatalogContext:
    entities: dict
    axes: dict
    axis_values: dict


def _items(result, attribute):
    # Cache each pybind STL collection once; its getter otherwise copies it.
    return tuple(getattr(result, attribute, ()))


def _numeric_array(values, *, shape=None):
    array = np.asarray(values, dtype=np.float64)
    if shape is not None:
        array = array.reshape(shape)
    array.setflags(write=False)
    return array


def _vector_array(series):
    return _numeric_array(
        [[value.x, value.y, value.z] for value in series.values],
        shape=(-1, 3),
    )


def _index_unique(items, attribute, description):
    indexed = {}
    for item in items:
        key = getattr(item, attribute)
        if key in indexed:
            raise ValueError(f"Duplicate {description}: {key}")
        indexed[key] = item
    return indexed


def _validate_identifier(value, description):
    if not isinstance(value, str) or not value or "/" in value:
        raise ValueError(
            f"{description} must be a nonempty path-safe string: {value!r}"
        )


def _validate_axis(axis, description, *, monotonic=False):
    _validate_identifier(axis.key, f"{description} key")
    if axis.kind not in AXIS_KINDS:
        raise ValueError(
            f"{description} {axis.key} has unsupported kind {axis.kind!r}"
        )
    if axis.kind == "time" and axis.unit not in TIME_UNIT_TO_SECONDS:
        raise ValueError(
            f"Time axis {axis.key} must use one of "
            f"{tuple(TIME_UNIT_TO_SECONDS)}"
        )

    values = _numeric_array(axis.values)
    if not np.isfinite(values).all():
        raise ValueError(f"{description} {axis.key} contains non-finite values")
    if axis.kind == "sequence" and not np.equal(values, np.floor(values)).all():
        raise ValueError(f"Sequence axis {axis.key} must contain integer values")
    if (monotonic or axis.kind in TIME_AXIS_KINDS) and len(values) > 1:
        differences = np.diff(values)
        increasing = bool(np.all(differences > 0))
        decreasing = bool(np.all(differences < 0))
        if axis.kind in TIME_AXIS_KINDS and not increasing:
            raise ValueError(f"Timeline axis {axis.key} must be strictly increasing")
        if monotonic and not (increasing or decreasing):
            raise ValueError(f"{description} {axis.key} must be strictly monotonic")
    return values


def _validate_item(item, context):
    _validate_identifier(item.system, "Result system")
    _validate_identifier(item.key, f"{item.system} product key")
    if item.entity_id == 0:
        return None
    try:
        return context.entities[item.entity_id]
    except KeyError as error:
        raise ValueError(
            f"{item.system}/{item.key} references unknown entity {item.entity_id}"
        ) from error


def _series_axis(series, context):
    try:
        return context.axes[series.axis_key]
    except KeyError as error:
        raise ValueError(
            f"Series {series.system}/{series.key} references unknown axis "
            f"{series.axis_key}"
        ) from error


def _series_record(series, context, *, is_vector):
    entity = _validate_item(series, context)
    axis = _series_axis(series, context)
    coordinates = context.axis_values[series.axis_key]
    values = _vector_array(series) if is_vector else _numeric_array(series.values)
    if len(values) != len(coordinates):
        raise ValueError(
            f"Series {series.system}/{series.key} has {len(values)} values but axis "
            f"{series.axis_key} has {len(coordinates)}"
        )

    telemetry = series.system == "kinematics"
    if telemetry and axis.kind not in TIME_AXIS_KINDS:
        raise ValueError(f"Telemetry series {series.key} requires a time axis")
    timeline = axis.kind in TIME_AXIS_KINDS
    return ProductRecord(
        item=series,
        entity=entity,
        axis=axis,
        coordinates=coordinates,
        values=values,
        metadata=None,
        section="telemetry" if telemetry else "analysis",
        view_type=(
            TIME_SERIES_VIEW
            if telemetry or (timeline and not is_vector)
            else SPATIAL_3D_VIEW if is_vector else SPATIAL_2D_VIEW
        ),
        source_type=(
            VECTOR_SOURCE
            if is_vector
            else SCALAR_SOURCE if telemetry or timeline else CURVE_SOURCE
        ),
        unit=series.unit,
        default_rank=(
            (10 if is_vector else 20)
            if telemetry
            else (30 if is_vector else 20)
        ),
    )


def _read_scalar(series, context):
    return _series_record(series, context, is_vector=False)


def _read_vector(series, context):
    return _series_record(series, context, is_vector=True)


def _read_curve(curve, context):
    entity = _validate_item(curve, context)
    coordinates = _validate_axis(curve.x_axis, f"Curve {curve.key} x-axis")
    values = _numeric_array(curve.values)
    if len(values) != len(coordinates):
        raise ValueError(
            f"Curve {curve.key} has {len(values)} values but its x-axis has "
            f"{len(coordinates)}"
        )
    return ProductRecord(
        item=curve,
        entity=entity,
        axis=curve.x_axis,
        coordinates=coordinates,
        values=values,
        metadata=None,
        section="analysis",
        view_type=SPATIAL_2D_VIEW,
        source_type=CURVE_SOURCE,
        unit=curve.value_unit,
        default_rank=10,
    )


def _read_grid(grid, context):
    entity = _validate_item(grid, context)
    x_values = _validate_axis(
        grid.x_axis, f"Grid {grid.key} x-axis", monotonic=True
    )
    y_values = _validate_axis(
        grid.y_axis, f"Grid {grid.key} y-axis", monotonic=True
    )
    flat_values = _numeric_array(grid.values)
    if (
        flat_values.size != grid.rows * grid.columns
        or len(x_values) != grid.columns
        or len(y_values) != grid.rows
    ):
        raise ValueError(f"Grid {grid.key} data does not match its shape")
    if grid.has_display_range and not (
        math.isfinite(grid.display_min)
        and math.isfinite(grid.display_max)
        and grid.display_min < grid.display_max
    ):
        raise ValueError(f"Grid {grid.key} has an invalid display range")
    return ProductRecord(
        item=grid,
        entity=entity,
        axis=None,
        coordinates=(x_values, y_values),
        values=flat_values.reshape((int(grid.rows), int(grid.columns))),
        metadata=None,
        section="analysis",
        view_type=SPATIAL_2D_VIEW,
        source_type=GRID_SOURCE,
        unit=grid.value_unit,
        default_rank=40,
    )


def _read_snapshot(snapshot, context):
    entity = _validate_item(snapshot, context)
    metrics = tuple(snapshot.metrics)
    metric_keys = [metric.key for metric in metrics]
    if len(metric_keys) != len(set(metric_keys)):
        raise ValueError(f"Snapshot {snapshot.key} has duplicate metric keys")
    for metric_key in metric_keys:
        _validate_identifier(metric_key, f"Snapshot {snapshot.key} metric key")
    return ProductRecord(
        item=snapshot,
        entity=entity,
        axis=None,
        coordinates=None,
        values=_numeric_array([metric.value for metric in metrics]),
        metadata=metrics,
        section="analysis",
        view_type=TEXT_VIEW,
        source_type=SNAPSHOT_SOURCE,
        unit="",
        default_rank=50,
    )


# Adding a new semantic result shape requires one reader here and one logger in
# rerun_adapter; individual products require no Python changes.
PRODUCT_READERS = (
    ("scalars", _read_scalar),
    ("vectors", _read_vector),
    ("curves", _read_curve),
    ("grids", _read_grid),
    ("snapshots", _read_snapshot),
)


def _presentation(item):
    presentation = getattr(item, "presentation", None)
    if presentation is None:
        return "", 0
    group = presentation.group.strip()
    if "/" in group:
        raise ValueError(f"Presentation group cannot contain '/': {group!r}")
    return group, int(presentation.order)


def _make_view(record, sequence):
    path_builder = (
        telemetry_series if record.section == "telemetry" else analysis_product
    )
    base_path = path_builder(record.entity, record.item)
    data_path = base_path if record.section == "telemetry" else data_child(base_path)
    plot_path = base_path if record.section == "telemetry" else plot_child(base_path)
    group, order = _presentation(record.item)
    return ViewSpec(
        section=record.section,
        view_type=record.view_type,
        source_type=record.source_type,
        item=record.item,
        entity=record.entity,
        axis=record.axis,
        coordinates=record.coordinates,
        values=record.values,
        metadata=record.metadata,
        base_path=base_path,
        data_path=data_path,
        plot_path=plot_path,
        name=record.item.name,
        unit=record.unit,
        group=group,
        order=order,
        sequence=sequence,
    )


def _validate_entities(items):
    entities = _index_unique(items, "id", "entity id")
    if any(entity_id <= 0 for entity_id in entities):
        raise ValueError("Entity ids must be positive; 0 is reserved for global results")
    keys = _index_unique(items, "key", "entity key")
    for key in keys:
        _validate_identifier(key, "Entity key")
        if key == "global":
            raise ValueError("Entity key 'global' is reserved for ownerless results")
    return entities


def build_view_catalog(result):
    """Validate a Result and classify every visible item exactly once."""

    entity_items = _items(result, "entities")
    entities = _validate_entities(entity_items)
    axis_items = _items(result, "axes")
    axes = _index_unique(axis_items, "key", "axis key")
    axis_values = {
        axis.key: _validate_axis(axis, "Axis")
        for axis in axis_items
    }
    context = CatalogContext(entities, axes, axis_values)

    records = []
    source_sequence = 0
    for collection_name, reader in PRODUCT_READERS:
        for item in _items(result, collection_name):
            records.append((reader(item, context), source_sequence))
            source_sequence += 1

    section_rank = {"telemetry": 0, "analysis": 1}
    records.sort(
        key=lambda entry: (
            section_rank[entry[0].section],
            entry[0].default_rank,
            entry[1],
        )
    )

    paths = set()
    views = []
    for sequence, (record, _) in enumerate(records):
        view = _make_view(record, sequence)
        if view.base_path in paths:
            raise ValueError(
                f"Multiple result items map to {view.base_path}: "
                f"{record.item.system}/{record.item.key}"
            )
        paths.add(view.base_path)
        if record.values.size:
            views.append(view)

    views.sort(
        key=lambda view: (
            section_rank[view.section],
            *view.display_sort_key,
        )
    )
    return ViewCatalog(entity_items, entities, axes, tuple(views))


def as_view_catalog(result_or_catalog):
    if isinstance(result_or_catalog, ViewCatalog):
        return result_or_catalog
    return build_view_catalog(result_or_catalog)


def validate_result(result):
    """Validate a result and retain the adapter's original indexing contract."""

    catalog = build_view_catalog(result)
    return catalog.entities, catalog.axes
