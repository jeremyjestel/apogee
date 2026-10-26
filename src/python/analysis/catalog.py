"""Small normalized contract between bound simulation results and Qt renderers."""

from dataclasses import dataclass, replace

import numpy as np


CURVE = "curve"
GRID_SERIES = "grid_series"
METRIC_TABLE = "metric_table"
ARRAY_SERIES = "array_series"
RANGE_PULSE_MAP = "range_pulse_map"
DESCRIPTION_KEY = "description"

# Configuration fields in the current entity contract. Flat state signals are
# deliberately excluded: an inactive model still needs its time history.
ENTITY_CONFIGURATION = {
    "id", "key", "display_name", "type", "team", "motion_type",
    "mass", "drag_coeff", "area_m2", "radar_signature_dbsm",
}


@dataclass(frozen=True, slots=True)
class EntityData:
    id: int
    key: str
    name: str
    type: str
    team: str


@dataclass(frozen=True, slots=True)
class AxisData:
    key: str
    name: str
    unit: str
    kind: str
    values: np.ndarray


@dataclass(frozen=True, slots=True)
class MetricData:
    key: str
    name: str
    unit: str
    values: np.ndarray


@dataclass(frozen=True, slots=True)
class AnalysisProduct:
    kind: str
    entity: EntityData | None
    system: str
    key: str
    name: str
    axes: tuple[AxisData, ...] = ()
    values: np.ndarray | None = None
    metrics: tuple[MetricData, ...] = ()
    value_unit: str = ""
    display_range: tuple[float, float] | None = None
    group: str = ""
    order: int = 0
    sequence: int = 0
    samples: tuple[np.ndarray | None, ...] = ()

    @property
    def entity_id(self):
        return self.entity.id if self.entity else 0

    @property
    def owner_key(self):
        return self.entity.key if self.entity else "global"

    @property
    def owner_name(self):
        return self.entity.name if self.entity else "Global"

    @property
    def identity(self):
        return self.entity_id, self.system, self.key

    @property
    def display_sort_key(self):
        return self.order == 0, self.order, self.sequence


@dataclass(frozen=True, slots=True)
class AnalysisCatalog:
    entities: tuple[EntityData, ...]
    products: tuple[AnalysisProduct, ...]


def _array(values):
    array = np.array(values, dtype=np.float64, copy=True)
    array.setflags(write=False)
    return array


def _axis(axis):
    values = _array(axis.values)
    if values.ndim != 1:
        raise ValueError(f"Axis {axis.key!r} must be one-dimensional")
    return AxisData(
        key=str(axis.key),
        name=str(axis.name),
        unit=str(axis.unit),
        kind=str(axis.kind),
        values=values,
    )


def _presentation(item):
    presentation = getattr(item, "presentation", None)
    if presentation is None:
        return "", 0
    return str(presentation.group).strip(), int(presentation.order)


def _base(item, entities, kind, sequence, **data):
    entity_id = int(item.entity_id)
    if entity_id and entity_id not in entities:
        raise ValueError(f"{item.system}/{item.key} references entity {entity_id}")
    group, order = _presentation(item)
    return AnalysisProduct(
        kind=kind,
        entity=entities.get(entity_id),
        system=str(item.system),
        key=str(item.key),
        name=str(item.name),
        group=group,
        order=order,
        sequence=sequence,
        **data,
    )


def _curve(item, entities, sequence):
    axis = _axis(item.x_axis)
    values = _array(item.values)
    if values.shape != axis.values.shape:
        raise ValueError(f"Curve {item.key} axis and values do not match")
    return _base(
        item,
        entities,
        CURVE,
        sequence,
        axes=(axis,),
        values=values,
        value_unit=str(item.value_unit),
    )


def _grid_series(item, entities, sequence):
    time_axis = _axis(item.time_axis)
    x_axis = _axis(item.x_axis)
    y_axis = _axis(item.y_axis)
    shape = (len(time_axis.values), int(item.rows), int(item.columns))
    if not all(shape):
        raise ValueError(f"Grid series {item.key} cannot be empty")
    values = _array(item.values)
    if values.size != np.prod(shape, dtype=np.int64):
        raise ValueError(f"Grid series {item.key} axes and values do not match")
    values = values.reshape(shape)
    if shape[1:] != (len(y_axis.values), len(x_axis.values)):
        raise ValueError(f"Grid series {item.key} spatial axes do not match")
    display_range = (
        (float(item.display_min), float(item.display_max))
        if item.has_display_range
        else None
    )
    return _base(
        item,
        entities,
        GRID_SERIES,
        sequence,
        axes=(time_axis, x_axis, y_axis),
        values=values,
        value_unit=str(item.value_unit),
        display_range=display_range,
    )


def _metric_table(item, entities, sequence):
    time_axis = _axis(item.time_axis)
    valid_lengths = {1, len(time_axis.values)}
    metrics = []
    for metric in item.metrics:
        values = _array(metric.values)
        if values.ndim != 1 or len(values) not in valid_lengths:
            raise ValueError(
                f"Metric {metric.key} must be constant or match its time axis"
            )
        metrics.append(
            MetricData(
                key=str(metric.key),
                name=str(metric.name),
                unit=str(metric.unit),
                values=values,
            )
        )
    return _base(
        item,
        entities,
        METRIC_TABLE,
        sequence,
        axes=(time_axis,),
        metrics=tuple(metrics),
    )


READERS = (
    ("curves", _curve),
    ("grid_series", _grid_series),
    ("metric_tables", _metric_table),
)


def _history_products(result, entities, sequence):
    """Expose logged fields by shape, without subsystem-specific adapters."""

    axis_items = tuple(getattr(result, "axes", ()))
    axes = {item.key: _axis(item) for item in axis_items}
    if len(axes) != len(axis_items):
        raise ValueError("Axis keys must be unique")
    for collection in ("scalars", "vectors", "texts", "arrays"):
        for item in tuple(getattr(result, collection, ())):
            axis = axes.get(item.axis_key)
            if axis is None or axis.kind not in {"time", "sequence"}:
                raise ValueError(f"History {item.system}/{item.key} requires a timeline axis")
            samples = tuple(item.values)
            if len(samples) != len(axis.values):
                raise ValueError(f"History {item.system}/{item.key} does not match {axis.key}")
            if not samples:
                continue
            base = _base(
                item, entities, CURVE, sequence, axes=(axis,), value_unit=str(item.unit)
            )
            base = replace(base, key=f"history/{item.key}")
            if collection == "scalars":
                values = _array(samples)
                if values.ndim != 1:
                    raise ValueError(f"History {item.key} must be scalar")
                yield replace(base, values=values)
                sequence += 1
            elif collection == "vectors":
                values = _array([[value.x, value.y, value.z] for value in samples])
                for component, label in enumerate(("x", "y", "z")):
                    yield replace(
                        base, key=f"{base.key}/{label}", name=f"{base.name} {label.upper()}",
                        values=values[:, component], sequence=sequence,
                    )
                    sequence += 1
            elif collection == "texts":
                values = np.array(samples, dtype=object)
                if values.ndim != 1 or any(
                    value is not None and not isinstance(value, str) for value in samples
                ):
                    raise ValueError(f"History {item.key} must contain text or missing values")
                values.setflags(write=False)
                metric = MetricData(str(item.key), str(item.name), str(item.unit), values)
                yield replace(base, kind=METRIC_TABLE, metrics=(metric,))
                sequence += 1
            else:
                arrays = []
                for sample in samples:
                    if sample is None:
                        arrays.append(None)
                        continue
                    shape = (int(sample.rows), int(sample.columns))
                    values = np.array(sample.values, dtype=np.complex128, copy=True)
                    if min(shape) < 0 or values.ndim != 1 or values.size != shape[0] * shape[1]:
                        raise ValueError(f"Array history {item.key} sample dimensions do not match")
                    values = values.reshape(shape)
                    values.setflags(write=False)
                    arrays.append(values)
                is_range_pulse = (
                    base.system == "radars"
                    and str(item.key).endswith("/state/range_pulse_map")
                )
                yield replace(
                    base, kind=RANGE_PULSE_MAP if is_range_pulse else ARRAY_SERIES,
                    name="Range–Pulse Map" if is_range_pulse else base.name,
                    samples=tuple(arrays),
                )
                sequence += 1


def _description_products(entities, products):
    retained = []
    rows = {entity.id: {} for entity in entities}
    for product in products:
        field = product.key.removeprefix("history/")
        candidate = product.entity is not None and product.key.startswith("history/") and (
            product.system == "entity" and field in ENTITY_CONFIGURATION
            or product.system == "radars" and (
                "/params/" in field or field.endswith("/name")
            )
        )
        values = product.values if product.kind == CURVE else (
            product.metrics[0].values
            if product.kind == METRIC_TABLE and len(product.metrics) == 1 else None
        )
        present = [] if values is None else [
            value for value in values
            if value is not None and (isinstance(value, str) or np.isfinite(value))
        ]
        if not candidate or not present or any(value != present[0] for value in present):
            retained.append(product)
            continue
        value = present[0]
        if product.system == "entity" and field == "motion_type":
            value = {0: "EarthFixed", 1: "FreeFlight"}.get(value, str(value))
        name = f"{product.group} / {product.name}" if product.group else product.name
        data = np.array([value], dtype=object)
        data.setflags(write=False)
        rows[product.entity_id][(product.system, field)] = MetricData(
            field, name, product.value_unit, data
        )

    descriptions = []
    for entity in entities:
        metrics = []
        for field, name, value in (
            ("id", "ID", entity.id), ("key", "Key", entity.key),
            ("display_name", "Display name", entity.name),
            ("type", "Type", entity.type), ("team", "Team", entity.team),
        ):
            # A changing identity field retains its history and uses the initial
            # entity descriptor here. Otherwise prefer its recorded value.
            metric = rows[entity.id].pop(("entity", field), None)
            if metric is None:
                data = np.array([value], dtype=object)
                data.setflags(write=False)
                metric = MetricData(field, name, "", data)
            metrics.append(metric)
        metrics.extend(rows[entity.id].values())
        descriptions.append(AnalysisProduct(
            kind=METRIC_TABLE, entity=entity, system="entity",
            key=DESCRIPTION_KEY, name="Description",
            axes=(AxisData("", "", "", "", _array([])),), metrics=tuple(metrics),
            order=-1,
        ))
    return descriptions + retained


def build_analysis_catalog(result):
    """Copy each bound result collection once and prepare renderer-ready arrays."""

    entity_items = tuple(result.entities)
    entities = tuple(
        EntityData(
            id=int(item.id),
            key=str(item.key),
            name=str(item.display_name),
            type=str(item.type),
            team=str(item.team),
        )
        for item in entity_items
    )
    entity_lookup = {entity.id: entity for entity in entities}
    if len(entity_lookup) != len(entities):
        raise ValueError("Entity ids must be unique")

    products = []
    for collection_name, reader in READERS:
        for item in tuple(getattr(result, collection_name, ())):
            products.append(reader(item, entity_lookup, len(products)))
    products.extend(_history_products(result, entity_lookup, len(products)))

    identities = [product.identity for product in products]
    if len(set(identities)) != len(identities):
        raise ValueError("Analysis product identities must be unique")
    products = _description_products(entities, products)
    products.sort(key=lambda product: product.display_sort_key)
    return AnalysisCatalog(entities, tuple(products))
