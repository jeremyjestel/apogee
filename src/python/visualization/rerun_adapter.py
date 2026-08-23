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


def _vector_array(series):
    return np.asarray(
        [[value.x, value.y, value.z] for value in series.values],
        dtype=np.float64,
    ).reshape((-1, 3))


def validate_result(result):
    entities = {entity.id: entity for entity in result.entities}
    axes = {axis.key: axis for axis in result.axes}
    used_paths = set()

    for series in result.scalars:
        axis = axes[series.axis_key]
        if len(series.values) != len(axis.values):
            raise ValueError(
                f"Scalar series {series.key} has {len(series.values)} values but axis "
                f"{series.axis_key} has {len(axis.values)}"
            )
        _claim_path(used_paths, series)

    for series in result.vectors:
        axis = axes[series.axis_key]
        if len(series.values) != len(axis.values):
            raise ValueError(
                f"Vector series {series.key} has {len(series.values)} values but axis "
                f"{series.axis_key} has {len(axis.values)}"
            )
        _claim_path(used_paths, series)

    for grid in result.grids:
        if len(grid.values) != grid.rows * grid.columns:
            raise ValueError(f"Grid {grid.key} data does not match its shape")
        _claim_path(used_paths, grid)

    return entities, axes


def _claim_path(used_paths, item):
    area = "telemetry" if item.system == "kinematics" else "analysis"
    path = (area, item.entity_id, item.system, item.key)
    if path in used_paths:
        raise ValueError(f"Multiple series map to the same path: {path}")
    used_paths.add(path)


def _time_column(axis):
    values = np.asarray(axis.values, dtype=np.float64)
    if axis.kind == "sequence":
        return rr.TimeColumn(axis.key, sequence=values.astype(np.int64))
    return rr.TimeColumn(axis.key, duration=values)


def _entity_color(entity):
    if entity is None:
        return DEFAULT_ENTITY_COLOR
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
    )


def _log_scenario(recording, result, axes):
    recording.log(
        "/world",
        rr.ViewCoordinates.RIGHT_HAND_Z_UP,
        static=True,
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
        )
        recording.log(
            world_trajectory(entity),
            rr.LineStrips3D(
                [positions],
                colors=[color],
                radii=rr.Radius.ui_points(2.0),
            ),
            static=True,
        )

        for quantity in ("velocity", "acceleration"):
            series = vector_lookup.get((entity.id, "kinematics", quantity))
            if series is None or len(series.values) == 0:
                continue

            vectors = _vector_array(series) * VECTOR_DISPLAY_SCALES[quantity]
            path = world_vector(entity, series)
            recording.log(
                path,
                rr.Arrows3D.from_fields(colors=[VECTOR_COLORS[quantity]]),
                static=True,
            )
            recording.send_columns(
                path,
                indexes=[_time_column(position_axis)],
                columns=rr.Arrows3D.columns(origins=positions, vectors=vectors),
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
        )
        recording.send_columns(
            path,
            indexes=[_time_column(axes[series.axis_key])],
            columns=rr.Scalars.columns(scalars=values),
        )


def _log_vector_analysis(recording, result, entities, axes):
    for series in result.vectors:
        if series.system == "kinematics":
            continue

        entity = entities.get(series.entity_id)
        axis = axes[series.axis_key]
        path = analysis_series(entity, series)
        values = _vector_array(series)
        color = _entity_color(entity)

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
        color = _entity_color(entity)
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
            )
            continue

        if len(values) == 0:
            continue
        recording.log(
            path,
            rr.SeriesLines(names=series.name, colors=[color]),
            static=True,
        )
        recording.send_columns(
            path,
            indexes=[_time_column(axis)],
            columns=rr.Scalars.columns(scalars=values),
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
        )


def log_result(result, recording, *, blueprint=None):
    entities, axes = validate_result(result)
    blueprint = blueprint or build_blueprint(result)

    _log_scenario(recording, result, axes)
    _log_vector_telemetry(recording, result, entities, axes)
    _log_vector_analysis(recording, result, entities, axes)
    _log_scalar_series(recording, result, entities, axes)
    _log_grids(recording, result, entities)

    recording.send_blueprint(blueprint)
    recording.flush()
    return blueprint


def show_result(result):
    blueprint = build_blueprint(result)
    recording = rr.RecordingStream(APPLICATION_ID)
    recording.spawn(default_blueprint=blueprint)
    log_result(result, recording, blueprint=blueprint)
    return recording


def save_result(result, path):
    blueprint = build_blueprint(result)
    output_path = Path(path).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    recording = rr.RecordingStream(APPLICATION_ID)
    recording.save(str(output_path), default_blueprint=blueprint)
    log_result(result, recording, blueprint=blueprint)
    recording.disconnect()
    return output_path
