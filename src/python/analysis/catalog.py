"""Small normalized contract between bound simulation results and Qt renderers."""

from dataclasses import dataclass

import numpy as np


CURVE = "curve"
GRID_SERIES = "grid_series"
METRIC_TABLE = "metric_table"


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
    array = np.asarray(values, dtype=np.float64)
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
    presentation = item.presentation
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
    values.setflags(write=False)
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
    metrics = []
    for metric in item.metrics:
        values = _array(metric.values)
        valid_lengths = {1, len(time_axis.values)} if len(time_axis.values) else {0, 1}
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
        for item in tuple(getattr(result, collection_name)):
            products.append(reader(item, entity_lookup, len(products)))

    identities = [product.identity for product in products]
    if len(set(identities)) != len(identities):
        raise ValueError("Analysis product identities must be unique")
    products.sort(key=lambda product: product.display_sort_key)
    return AnalysisCatalog(entities, tuple(products))
