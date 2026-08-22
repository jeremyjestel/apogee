import math
import os
from pathlib import Path

os.environ.setdefault("WGPU_BACKEND", "gl")

import numpy as np
import rerun as rr

from .chart_renderer import render_xy_chart
from .rerun_blueprint import build_blueprint
from .rerun_paths import (
    analysis_grid,
    analysis_series,
    telemetry_series,
    validate_path_token,
    world_entity,
    world_trajectory,
    world_vector,
)


APPLICATION_ID = "apogee"

TEAM_COLORS = {
    "blue": [40, 110, 255],
    "red": [255, 55, 55],
}
DEFAULT_ENTITY_COLOR = [200, 200, 200]
XYZ_COLORS = [[255, 75, 75], [75, 220, 100], [75, 140, 255]]
VECTOR_COLORS = {
    "velocity": [60, 230, 100],
    "acceleration": [255, 180, 40],
}
VECTOR_DISPLAY_SCALES = {
    "velocity": 1.0,
    "acceleration": 10.0,
}


def _require_text(value, context):
    if not value:
        raise ValueError(f"{context} cannot be empty")


def _finite_array(values, context):
    array = np.asarray(values, dtype=np.float64)
    if not np.all(np.isfinite(array)):
        raise ValueError(f"{context} contains non-finite values")
    return array


def _vector_array(series):
    values = np.asarray(
        [[value.x, value.y, value.z] for value in series.values],
        dtype=np.float64,
    )
    if values.size == 0:
        return np.empty((0, 3), dtype=np.float64)
    return values.reshape((-1, 3))


def validate_result(result):
    entities = {}
    entity_keys = set()

    for entity in result.entities:
        if entity.id <= 0:
            raise ValueError("Entity IDs must be positive")
        if entity.id in entities:
            raise ValueError(f"Duplicate entity ID: {entity.id}")
        validate_path_token(entity.key, "entity key")
        if entity.key in entity_keys:
            raise ValueError(f"Duplicate entity key: {entity.key}")
        _require_text(entity.display_name, "entity display name")
        entities[entity.id] = entity
        entity_keys.add(entity.key)

    axes = {}
    for axis in result.axes:
        validate_path_token(axis.key, "axis key")
        if axis.key in axes:
            raise ValueError(f"Duplicate axis key: {axis.key}")
        _require_text(axis.name, f"axis {axis.key} name")
        if axis.kind not in {"time", "sequence", "continuous"}:
            raise ValueError(
                f"Axis {axis.key} has unsupported kind {axis.kind!r}"
            )

        values = _finite_array(axis.values, f"axis {axis.key}")
        if axis.kind in {"time", "sequence"}:
            if len(values) > 1 and np.any(np.diff(values) <= 0.0):
                raise ValueError(f"Axis {axis.key} must increase monotonically")
        if axis.kind == "time" and axis.unit != "s":
            raise ValueError(f"Time axis {axis.key} must use seconds")
        if axis.kind == "sequence" and not np.all(values == np.floor(values)):
            raise ValueError(f"Sequence axis {axis.key} must contain integers")
        axes[axis.key] = axis

    scalar_keys = set()
    telemetry_paths = set()
    analysis_paths = set()
    for series in result.scalars:
        if series.entity_id != 0 and series.entity_id not in entities:
            raise ValueError(
                f"Scalar series {series.key} references unknown entity {series.entity_id}"
            )
        if series.system == "kinematics" and series.entity_id == 0:
            raise ValueError(
                f"Kinematics scalar series {series.key} must belong to an entity"
            )
        validate_path_token(series.system, "scalar-series system")
        validate_path_token(series.key, "scalar-series key")
        _require_text(series.name, f"scalar series {series.key} name")
        if series.axis_key not in axes:
            raise ValueError(
                f"Scalar series {series.key} references missing axis {series.axis_key}"
            )
        identity = (series.entity_id, series.system, series.key)
        if identity in scalar_keys:
            raise ValueError(f"Duplicate scalar series: {identity}")
        scalar_keys.add(identity)

        path_keys = telemetry_paths if series.system == "kinematics" else analysis_paths
        if identity in path_keys:
            raise ValueError(f"Multiple series map to the same path: {identity}")
        path_keys.add(identity)

        values = _finite_array(series.values, f"scalar series {series.key}")
        if len(values) != len(axes[series.axis_key].values):
            raise ValueError(
                f"Scalar series {series.key} has {len(values)} values but axis "
                f"{series.axis_key} has {len(axes[series.axis_key].values)}"
            )

    vector_keys = set()
    for series in result.vectors:
        if series.entity_id != 0 and series.entity_id not in entities:
            raise ValueError(
                f"Vector series {series.key} references unknown entity {series.entity_id}"
            )
        if series.system == "kinematics" and series.entity_id == 0:
            raise ValueError(
                f"Kinematics vector series {series.key} must belong to an entity"
            )
        validate_path_token(series.system, "vector-series system")
        validate_path_token(series.key, "vector-series key")
        _require_text(series.name, f"vector series {series.key} name")
        _require_text(series.frame, f"vector series {series.key} frame")
        if series.axis_key not in axes:
            raise ValueError(
                f"Vector series {series.key} references missing axis {series.axis_key}"
            )
        if (
            series.system == "kinematics"
            and axes[series.axis_key].kind not in {"time", "sequence"}
        ):
            raise ValueError(
                f"Kinematics vector series {series.key} requires a time or sequence axis"
            )
        identity = (series.entity_id, series.system, series.key)
        if identity in vector_keys:
            raise ValueError(f"Duplicate vector series: {identity}")
        vector_keys.add(identity)

        path_keys = telemetry_paths if series.system == "kinematics" else analysis_paths
        if identity in path_keys:
            raise ValueError(f"Multiple series map to the same path: {identity}")
        path_keys.add(identity)

        values = _vector_array(series)
        if not np.all(np.isfinite(values)):
            raise ValueError(f"Vector series {series.key} contains non-finite values")
        if len(values) != len(axes[series.axis_key].values):
            raise ValueError(
                f"Vector series {series.key} has {len(values)} values but axis "
                f"{series.axis_key} has {len(axes[series.axis_key].values)}"
            )

    grid_keys = set()
    for grid in result.grids:
        if grid.entity_id != 0 and grid.entity_id not in entities:
            raise ValueError(
                f"Grid {grid.key} references unknown entity {grid.entity_id}"
            )
        validate_path_token(grid.system, "grid system")
        validate_path_token(grid.key, "grid key")
        _require_text(grid.name, f"grid {grid.key} name")
        identity = (grid.entity_id, grid.system, grid.key)
        if identity in grid_keys:
            raise ValueError(f"Duplicate grid: {identity}")
        if identity in analysis_paths:
            raise ValueError(f"Multiple analyses map to the same path: {identity}")
        grid_keys.add(identity)
        analysis_paths.add(identity)

        if grid.rows <= 0 or grid.columns <= 0:
            raise ValueError(f"Grid {grid.key} dimensions must be positive")
        for axis_name, axis in (("x", grid.x_axis), ("y", grid.y_axis)):
            validate_path_token(axis.key, f"grid {grid.key} {axis_name}-axis key")
            _require_text(axis.name, f"grid {grid.key} {axis_name}-axis name")
            if axis.kind not in {"time", "sequence", "continuous"}:
                raise ValueError(
                    f"Grid {grid.key} {axis_name}-axis has unsupported kind "
                    f"{axis.kind!r}"
                )
        if grid.x_axis.key == grid.y_axis.key:
            raise ValueError(f"Grid {grid.key} axis keys must be distinct")
        if len(grid.y_axis.values) != grid.rows:
            raise ValueError(f"Grid {grid.key} row axis length does not match rows")
        if len(grid.x_axis.values) != grid.columns:
            raise ValueError(
                f"Grid {grid.key} column axis length does not match columns"
            )
        if len(grid.values) != grid.rows * grid.columns:
            raise ValueError(f"Grid {grid.key} data does not match its shape")
        _finite_array(grid.x_axis.values, f"grid {grid.key} x axis")
        _finite_array(grid.y_axis.values, f"grid {grid.key} y axis")
        _finite_array(grid.values, f"grid {grid.key} values")
        if grid.has_display_range:
            if not math.isfinite(grid.display_min) or not math.isfinite(
                grid.display_max
            ):
                raise ValueError(f"Grid {grid.key} display range must be finite")
            if grid.display_min >= grid.display_max:
                raise ValueError(
                    f"Grid {grid.key} display minimum must be below its maximum"
                )

    return entities, axes


def _time_column(axis):
    values = np.asarray(axis.values, dtype=np.float64)
    if axis.kind == "time":
        return rr.TimeColumn(axis.key, duration=values)
    if axis.kind == "sequence":
        return rr.TimeColumn(axis.key, sequence=values.astype(np.int64))
    raise ValueError(f"Axis {axis.key} is not a Rerun timeline")


def _entity_color(entity):
    return TEAM_COLORS.get(entity.team.lower(), DEFAULT_ENTITY_COLOR)


def _log_entity_metadata(recording, entity):
    recording.log(
        f"{world_entity(entity)}/metadata",
        rr.AnyValues(
            entity_id=entity.id,
            display_name=entity.display_name,
            entity_type=entity.type,
            team=entity.team,
        ),
        static=True,
        strict=True,
    )


def _log_scenario(recording, result, entities, axes):
    recording.log(
        "/world",
        rr.ViewCoordinates.RIGHT_HAND_Z_UP,
        static=True,
        strict=True,
    )

    vector_lookup = {
        (series.entity_id, series.system, series.key): series
        for series in result.vectors
    }

    for entity in result.entities:
        _log_entity_metadata(recording, entity)
        color = _entity_color(entity)
        root = world_entity(entity)
        position = vector_lookup.get((entity.id, "kinematics", "position"))

        if position is None:
            continue

        positions = _vector_array(position)
        if len(positions) == 0:
            continue

        position_axis = axes[position.axis_key]
        recording.send_columns(
            root,
            indexes=[_time_column(position_axis)],
            columns=rr.Transform3D.columns(translation=positions),
            strict=True,
        )
        recording.log(
            f"{root}/marker",
            rr.Points3D(
                [[0.0, 0.0, 0.0]],
                colors=[color],
                radii=rr.Radius.ui_points(8.0),
                labels=[entity.display_name],
            ),
            static=True,
            strict=True,
        )
        recording.log(
            world_trajectory(entity),
            rr.LineStrips3D(
                [positions],
                colors=[color],
                radii=rr.Radius.ui_points(2.0),
            ),
            static=True,
            strict=True,
        )

        for quantity in ("velocity", "acceleration"):
            series = vector_lookup.get((entity.id, "kinematics", quantity))
            if series is None or len(series.values) == 0:
                continue
            if series.axis_key != position.axis_key or series.frame != position.frame:
                raise ValueError(
                    f"{entity.key} {quantity} must align with position for 3D display"
                )

            vectors = _vector_array(series) * VECTOR_DISPLAY_SCALES[quantity]
            path = world_vector(entity, series)
            recording.log(
                path,
                rr.Arrows3D.from_fields(colors=[VECTOR_COLORS[quantity]]),
                static=True,
                strict=True,
            )
            recording.send_columns(
                path,
                indexes=[_time_column(position_axis)],
                columns=rr.Arrows3D.columns(origins=positions, vectors=vectors),
                strict=True,
            )


def _log_vector_telemetry(recording, result, entities, axes):
    for series in result.vectors:
        if series.system != "kinematics":
            continue

        entity = entities[series.entity_id]
        path = telemetry_series(entity, series)
        values = _vector_array(series)

        if len(values) == 0:
            continue
        recording.log(
            path,
            rr.SeriesLines(names=["X", "Y", "Z"], colors=XYZ_COLORS),
            static=True,
            strict=True,
        )
        recording.send_columns(
            path,
            indexes=[_time_column(axes[series.axis_key])],
            columns=rr.Scalars.columns(scalars=values),
            strict=True,
        )


def _log_vector_analysis(recording, result, entities, axes):
    for series in result.vectors:
        if series.system == "kinematics":
            continue

        entity = entities.get(series.entity_id)
        axis = axes[series.axis_key]
        path = analysis_series(entity, series)
        values = _vector_array(series)
        color = _entity_color(entity) if entity is not None else DEFAULT_ENTITY_COLOR

        if len(values) == 1:
            recording.log(
                path,
                rr.Points3D(
                    values,
                    colors=[color],
                    radii=rr.Radius.ui_points(5.0),
                    labels=[series.name],
                ),
                static=True,
                strict=True,
            )
        elif len(values) > 1:
            recording.log(
                path,
                rr.LineStrips3D(
                    [values],
                    colors=[color],
                    radii=rr.Radius.ui_points(2.0),
                    labels=[series.name],
                ),
                static=True,
                strict=True,
            )

        recording.log(
            f"{path}/metadata",
            rr.AnyValues(
                axis_values=np.asarray(axis.values, dtype=np.float64),
                axis_name=axis.name,
                axis_unit=axis.unit,
                quantity_name=series.name,
                quantity_unit=series.unit,
                frame=series.frame,
            ),
            static=True,
            strict=True,
        )


def _log_scalar_series(recording, result, entities, axes):
    for series in result.scalars:
        entity = entities.get(series.entity_id)
        axis = axes[series.axis_key]
        path = (
            telemetry_series(entity, series)
            if series.system == "kinematics" and entity is not None
            else analysis_series(entity, series)
        )
        color = _entity_color(entity) if entity is not None else DEFAULT_ENTITY_COLOR
        values = np.asarray(series.values, dtype=np.float64)

        if axis.kind == "continuous":
            if len(values) > 0:
                chart = render_xy_chart(
                    axis.values,
                    values,
                    x_name=axis.name,
                    x_unit=axis.unit,
                    y_name=series.name,
                    y_unit=series.unit,
                    color=color,
                )
                recording.log(
                    path,
                    rr.Image(chart),
                    static=True,
                    strict=True,
                )
            recording.log(
                f"{path}/metadata",
                rr.AnyValues(
                    x_name=axis.name,
                    x_unit=axis.unit,
                    y_name=series.name,
                    y_unit=series.unit,
                ),
                static=True,
                strict=True,
            )
            continue

        if len(values) == 0:
            continue
        recording.log(
            path,
            rr.SeriesLines(names=series.name, colors=[color]),
            static=True,
            strict=True,
        )
        recording.send_columns(
            path,
            indexes=[_time_column(axis)],
            columns=rr.Scalars.columns(scalars=values),
            strict=True,
        )


def _log_grids(recording, result, entities):
    for grid in result.grids:
        entity = entities.get(grid.entity_id)
        path = analysis_grid(entity, grid)
        values = np.asarray(grid.values, dtype=np.float32).reshape(
            (grid.rows, grid.columns)
        )
        tensor_args = {
            "dim_names": (grid.y_axis.key, grid.x_axis.key),
        }
        if grid.has_display_range:
            tensor_args["value_range"] = (grid.display_min, grid.display_max)

        recording.log(
            path,
            rr.Tensor(values, **tensor_args),
            static=True,
            strict=True,
        )
        recording.log(
            f"{path}/metadata",
            rr.AnyValues(
                x_values=np.asarray(grid.x_axis.values, dtype=np.float64),
                x_name=grid.x_axis.name,
                x_unit=grid.x_axis.unit,
                y_values=np.asarray(grid.y_axis.values, dtype=np.float64),
                y_name=grid.y_axis.name,
                y_unit=grid.y_axis.unit,
                value_unit=grid.value_unit,
            ),
            static=True,
            strict=True,
        )


def log_result(result, recording, *, blueprint=None):
    entities, axes = validate_result(result)
    blueprint = blueprint or build_blueprint(result)

    _log_scenario(recording, result, entities, axes)
    _log_vector_telemetry(recording, result, entities, axes)
    _log_vector_analysis(recording, result, entities, axes)
    _log_scalar_series(recording, result, entities, axes)
    _log_grids(recording, result, entities)

    recording.send_blueprint(blueprint)
    recording.flush()
    return blueprint


def show_result(result):
    validate_result(result)
    blueprint = build_blueprint(result)
    recording = rr.RecordingStream(APPLICATION_ID)
    recording.spawn(default_blueprint=blueprint)
    log_result(result, recording, blueprint=blueprint)
    return recording


def save_result(result, path):
    validate_result(result)
    blueprint = build_blueprint(result)
    output_path = Path(path).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    recording = rr.RecordingStream(APPLICATION_ID)
    recording.save(str(output_path), default_blueprint=blueprint)
    log_result(result, recording, blueprint=blueprint)
    return output_path
