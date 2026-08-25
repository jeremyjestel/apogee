from pathlib import Path

import apogee
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
METERS_TO_KILOMETERS = 1.0 / apogee.constants.meters_per_kilometer

TEAM_COLORS = {
    "blue": [40, 110, 255, 255],
    "red": [255, 55, 55, 255],
}
DEFAULT_ENTITY_COLOR = [200, 200, 200, 255]
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
    # Convert bound Vec3 objects into the contiguous Nx3 layout expected by Rerun.
    return np.asarray(
        [[value.x, value.y, value.z] for value in series.values],
        dtype=np.float64,
    ).reshape((-1, 3))


def validate_result(result):
    # Index shared metadata once so each series can resolve its owner and axis by ID.
    entities = {entity.id: entity for entity in result.entities}
    axes = {axis.key: axis for axis in result.axes}
    used_paths = set()

    # Confirm every scalar sample has a matching coordinate on its declared axis.
    for series in result.scalars:
        axis = axes[series.axis_key]
        if len(series.values) != len(axis.values):
            raise ValueError(
                f"Scalar series {series.key} has {len(series.values)} values but axis "
                f"{series.axis_key} has {len(axis.values)}"
            )
        _claim_path(used_paths, series)

    # Apply the same axis-length requirement to each vector sample.
    for series in result.vectors:
        axis = axes[series.axis_key]
        if len(series.values) != len(axis.values):
            raise ValueError(
                f"Vector series {series.key} has {len(series.values)} values but axis "
                f"{series.axis_key} has {len(axis.values)}"
            )
        _claim_path(used_paths, series)

    # Confirm flattened grids and both coordinate axes agree with the declared shape.
    for grid in result.grids:
        if (
            len(grid.values) != grid.rows * grid.columns
            or len(grid.x_axis.values) != grid.columns
            or len(grid.y_axis.values) != grid.rows
        ):
            raise ValueError(f"Grid {grid.key} data does not match its shape")
        _claim_path(used_paths, grid)

    return entities, axes


def _claim_path(used_paths, item):
    # Mirror the final Rerun namespace to catch series that would overwrite each other.
    area = "telemetry" if item.system == "kinematics" else "analysis"
    path = (area, item.entity_id, item.system, item.key)
    if path in used_paths:
        raise ValueError(f"Multiple series map to the same path: {path}")
    used_paths.add(path)


def _time_column(axis):
    # Preserve integer sequence axes while treating all other timelines as durations.
    values = np.asarray(axis.values, dtype=np.float64)
    if axis.kind == "sequence":
        return rr.TimeColumn(axis.key, sequence=values.astype(np.int64))
    return rr.TimeColumn(axis.key, duration=values)


def _entity_color(entity):
    if entity is None:
        return DEFAULT_ENTITY_COLOR
    return TEAM_COLORS.get(entity.team.lower(), DEFAULT_ENTITY_COLOR)


def _log_entity_metadata(recording, entity):
    # Store descriptive fields once because they remain fixed throughout the recording.
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
    # Establish the world coordinate convention for every child transform and geometry.
    recording.log(
        "/world",
        rr.ViewCoordinates.RIGHT_HAND_Z_UP,
        static=True,
    )

    # Draw Earth at its mean physical radius in the kilometer-based ECI scene.
    recording.log(
        "/world/earth",
        rr.Ellipsoids3D(
            centers=[[0.0, 0.0, 0.0]],
            radii=[
                apogee.constants.earth_mean_radius_m * METERS_TO_KILOMETERS
            ],
            colors=[[45, 105, 180, 255]],
            labels=["Earth"],
        ),
        static=True,
    )

    # Index vector series so each entity can quickly find its kinematic quantities.
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

        # Convert only the 3D display coordinates; stored simulation values remain meters.
        positions = _vector_array(position) * METERS_TO_KILOMETERS
        if len(positions) == 0:
            continue

        position_axis = axes[position.axis_key]
        # Define marker styling once while its absolute ECI position changes over time.
        recording.log(
            root,
            rr.Points3D.from_fields(
                colors=[color],
                radii=rr.Radius.ui_points(8.0),
                labels=[entity.display_name],
                show_labels=True,
                point_shading="flat",
            ),
            static=True,
        )
        recording.send_columns(
            root,
            indexes=[_time_column(position_axis)],
            columns=rr.Points3D.columns(positions=positions),
        )
        # Draw the complete path as static context around the animated marker.
        recording.log(
            world_trajectory(entity),
            rr.LineStrips3D(
                [positions],
                colors=[color],
                radii=rr.Radius.ui_points(2.0),
            ),
            static=True,
        )

        # Display velocity and acceleration as scaled arrows anchored to each position.
        for quantity in ("velocity", "acceleration"):
            series = vector_lookup.get((entity.id, "kinematics", quantity))
            if series is None or len(series.values) == 0:
                continue

            vectors = (
                _vector_array(series)
                * METERS_TO_KILOMETERS
                * VECTOR_DISPLAY_SCALES[quantity]
            )
            path = world_vector(entity, series)
            # Define arrow styling once, then send changing origins and vectors by column.
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
    # Represent each kinematic Vec3 as three synchronized X, Y, and Z scalar lines.
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
    # Render non-kinematic vectors as static 3D points or paths rather than timelines.
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

        # Retain the independent analysis axis and units alongside the rendered geometry.
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
    # Route scalar data to entity telemetry or analysis paths according to its system.
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

        # Render non-timeline XY data as a labeled image because Rerun plots use timelines.
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
            # Store the source labels so the image remains machine-describable in Rerun.
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
        # Use Rerun's native line-series representation for sequence and time axes.
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
    # Reshape each flattened C++ grid into the row-major tensor expected by Rerun.
    for grid in result.grids:
        entity = entities.get(grid.entity_id)
        path = analysis_grid(entity, grid)
        values = np.asarray(grid.values, dtype=np.float32).reshape(
            (grid.rows, grid.columns)
        )
        # Name tensor dimensions after their physical axes and honor an optional color range.
        tensor_args = {
            "dim_names": (grid.y_axis.key, grid.x_axis.key),
        }
        if grid.has_display_range:
            tensor_args["value_range"] = (grid.display_min, grid.display_max)

        # Keep physical coordinate arrays and units next to the displayed tensor.
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


def _log_result(result, recording, blueprint=None):
    # Validate and index the result before writing any data into the recording.
    entities, axes = validate_result(result)
    blueprint = blueprint or build_blueprint(result)

    # Populate every visualization area before installing the matching saved layout.
    _log_scenario(recording, result, axes)
    _log_vector_telemetry(recording, result, entities, axes)
    _log_vector_analysis(recording, result, entities, axes)
    _log_scalar_series(recording, result, entities, axes)
    _log_grids(recording, result, entities)

    recording.send_blueprint(blueprint)
    recording.flush()


def save_result(result, path):
    # Resolve the output and create parent folders before connecting Rerun to the file.
    blueprint = build_blueprint(result)
    output_path = Path(path).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Own an isolated recording stream so repeated simulations cannot share stale state.
    recording = rr.RecordingStream(APPLICATION_ID)
    try:
        recording.save(str(output_path))
        _log_result(result, recording, blueprint)
    finally:
        # Always release the file-backed stream, including when logging raises an error.
        recording.disconnect()

    return output_path
