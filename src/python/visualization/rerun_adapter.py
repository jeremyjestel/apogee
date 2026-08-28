import socket

import apogee
import numpy as np
import rerun as rr

from .rerun_blueprint import build_blueprint
from .rerun_paths import (
    metadata_child,
    world_entity,
    world_trajectory,
    world_vector,
)
from .telemetry_catalog import (
    SCALAR_SOURCE,
    TIME_UNIT_TO_SECONDS,
    VECTOR_SOURCE,
    build_telemetry_catalog,
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


def _time_column(axis, values):
    values = np.asarray(values, dtype=np.float64)
    if axis.kind == "sequence":
        return rr.TimeColumn(axis.key, sequence=values.astype(np.int64))
    if axis.kind == "time":
        return rr.TimeColumn(
            axis.key,
            duration=values * TIME_UNIT_TO_SECONDS[axis.unit],
        )
    raise ValueError(f"Axis {axis.key} is not a timeline: {axis.kind}")


def _positions_on_axis(
    position_axis,
    position_coordinates,
    positions,
    target_axis,
    target_coordinates,
):
    """Align scenario arrow origins when a vector has its own timeline."""

    source = np.asarray(position_coordinates, dtype=np.float64).copy()
    target = np.asarray(target_coordinates, dtype=np.float64).copy()
    if position_axis.kind != target_axis.kind:
        raise ValueError("Scenario vectors must use compatible timeline kinds")
    if position_axis.kind == "time":
        source *= TIME_UNIT_TO_SECONDS[position_axis.unit]
        target *= TIME_UNIT_TO_SECONDS[target_axis.unit]
    if np.array_equal(source, target):
        return positions
    if target.size and (target[0] < source[0] or target[-1] > source[-1]):
        raise ValueError("Scenario vector timeline extends beyond position history")
    return np.column_stack(
        [np.interp(target, source, positions[:, component]) for component in range(3)]
    )


def _log_series_metadata(recording, view, **extra):
    recording.log(
        metadata_child(view.path),
        rr.AnyValues(
            axis_key=view.axis.key,
            axis_name=view.axis.name,
            axis_unit=view.axis.unit,
            value_key=view.item.key,
            value_name=view.name,
            value_unit=view.unit,
            **extra,
        ),
        static=True,
    )


def _entity_color(entity):
    if entity is None:
        return DEFAULT_ENTITY_COLOR
    return TEAM_COLORS.get(entity.team.lower(), DEFAULT_ENTITY_COLOR)


def _log_entity_metadata(recording, entity):
    recording.log(
        metadata_child(world_entity(entity)),
        rr.AnyValues(
            entity_id=entity.id,
            display_name=entity.display_name,
            entity_type=entity.type,
            team=entity.team,
        ),
        static=True,
    )


def _log_scenario(recording, catalog):
    recording.log("/world", rr.ViewCoordinates.RIGHT_HAND_Z_UP, static=True)
    recording.log(
        "/world/earth",
        rr.Ellipsoids3D(
            centers=[[0.0, 0.0, 0.0]],
            radii=[apogee.constants.earth_mean_radius_m * METERS_TO_KILOMETERS],
            colors=[[45, 105, 180, 255]],
            labels=["Earth"],
        ),
        static=True,
    )

    vector_lookup = {
        (view.item.entity_id, view.item.system, view.item.key): view
        for view in catalog.views
        if view.source_type == VECTOR_SOURCE
    }
    for entity in catalog.entity_items:
        _log_entity_metadata(recording, entity)
        color = _entity_color(entity)
        root = world_entity(entity)
        position_view = vector_lookup.get((entity.id, "kinematics", "position"))
        if position_view is None:
            continue

        position = position_view.item
        positions = position_view.values * METERS_TO_KILOMETERS
        if len(positions) == 0:
            continue

        position_axis = position_view.axis
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
            indexes=[_time_column(position_axis, position_view.coordinates)],
            columns=rr.Points3D.columns(positions=positions),
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
            series_view = vector_lookup.get((entity.id, "kinematics", quantity))
            if series_view is None:
                continue
            series = series_view.item
            vectors = (
                series_view.values
                * METERS_TO_KILOMETERS
                * VECTOR_DISPLAY_SCALES[quantity]
            )
            if series.frame != position.frame:
                raise ValueError(
                    f"Scenario vectors {position.key} and {series.key} use "
                    f"different frames"
                )
            origins = _positions_on_axis(
                position_axis,
                position_view.coordinates,
                positions,
                series_view.axis,
                series_view.coordinates,
            )
            path = world_vector(entity, series)
            recording.log(
                path,
                rr.Arrows3D.from_fields(colors=[VECTOR_COLORS[quantity]]),
                static=True,
            )
            recording.send_columns(
                path,
                indexes=[_time_column(series_view.axis, series_view.coordinates)],
                columns=rr.Arrows3D.columns(origins=origins, vectors=vectors),
            )


def _log_scalar(recording, view):
    recording.log(
        view.path,
        rr.SeriesLines(names=view.name, colors=[_entity_color(view.entity)]),
        static=True,
    )
    recording.send_columns(
        view.path,
        indexes=[_time_column(view.axis, view.coordinates)],
        columns=rr.Scalars.columns(scalars=view.values),
    )
    _log_series_metadata(recording, view)


def _log_vector(recording, view):
    recording.log(
        view.path,
        rr.SeriesLines(names=["X", "Y", "Z"], colors=XYZ_COLORS),
        static=True,
    )
    recording.send_columns(
        view.path,
        indexes=[_time_column(view.axis, view.coordinates)],
        columns=rr.Scalars.columns(scalars=view.values),
    )
    _log_series_metadata(recording, view, frame=view.item.frame)


VIEW_LOGGERS = {
    SCALAR_SOURCE: _log_scalar,
    VECTOR_SOURCE: _log_vector,
}


def _log_result(result, recording, blueprint=None):
    """Log only the scene and timeline telemetry from a simulation result."""

    catalog = build_telemetry_catalog(result)
    if blueprint is None:
        blueprint = build_blueprint(catalog)

    _log_scenario(recording, catalog)
    for view in catalog.views:
        VIEW_LOGGERS[view.source_type](recording, view)

    recording.send_blueprint(blueprint)
    recording.flush()


def view_rerun(result):
    """Open a detached viewer and send one completed scene and telemetry result."""

    with socket.socket() as available_port:
        available_port.bind(("127.0.0.1", 0))
        port = available_port.getsockname()[1]
    recording = rr.RecordingStream(APPLICATION_ID)
    try:
        recording.spawn(port=port, hide_welcome_screen=True)
        _log_result(result, recording)
    finally:
        recording.disconnect()
