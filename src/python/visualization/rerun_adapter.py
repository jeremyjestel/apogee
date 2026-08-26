from pathlib import Path

import apogee
import numpy as np
import rerun as rr

from .chart_renderer import encode_png, render_grid_chart, render_xy_chart
from .rerun_blueprint import build_blueprint
from .rerun_paths import (
    axis_child,
    metadata_child,
    world_entity,
    world_trajectory,
    world_vector,
)
from .view_catalog import (
    CURVE_SOURCE,
    GRID_SOURCE,
    SCALAR_SOURCE,
    SNAPSHOT_SOURCE,
    VECTOR_SOURCE,
    TIME_UNIT_TO_SECONDS,
    build_view_catalog,
    validate_result,
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


def _time_column(axis, values=None):
    if values is None:
        values = axis.values
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


def _log_xy_data(recording, view, x_values, y_values):
    samples = np.column_stack((x_values, y_values)).astype(np.float64, copy=False)
    recording.log(
        view.data_path,
        rr.Tensor(samples, dim_names=["sample", "component"]),
        static=True,
    )
    recording.log(
        metadata_child(view.data_path),
        rr.AnyValues(
            component_keys=[view.axis.key, view.item.key],
            component_names=[view.axis.name, view.name],
            component_units=[view.axis.unit, view.unit],
        ),
        static=True,
    )


def _log_series_metadata(recording, view, **extra):
    recording.log(
        metadata_child(view.data_path),
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
        f"{world_entity(entity)}/metadata",
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
        for view in catalog.in_section("telemetry")
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
            series_axis = series_view.axis
            origins = _positions_on_axis(
                position_axis,
                position_view.coordinates,
                positions,
                series_axis,
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
                indexes=[_time_column(series_axis, series_view.coordinates)],
                columns=rr.Arrows3D.columns(origins=origins, vectors=vectors),
            )


def _log_scalar(recording, view):
    values = view.values
    color = _entity_color(view.entity)
    recording.log(
        view.plot_path,
        rr.SeriesLines(names=view.name, colors=[color]),
        static=True,
    )
    recording.send_columns(
        view.plot_path,
        indexes=[_time_column(view.axis, view.coordinates)],
        columns=rr.Scalars.columns(scalars=values),
    )
    if view.data_path != view.plot_path:
        _log_xy_data(
            recording,
            view,
            view.coordinates,
            values,
        )
    else:
        _log_series_metadata(recording, view)


def _log_vector(recording, view):
    values = view.values
    if view.section == "telemetry":
        recording.log(
            view.plot_path,
            rr.SeriesLines(names=["X", "Y", "Z"], colors=XYZ_COLORS),
            static=True,
        )
        recording.send_columns(
            view.plot_path,
            indexes=[_time_column(view.axis, view.coordinates)],
            columns=rr.Scalars.columns(scalars=values),
        )
        _log_series_metadata(recording, view, frame=view.item.frame)
        return

    color = _entity_color(view.entity)
    if len(values) == 1:
        artifact = rr.Points3D(
            values,
            colors=[color],
            radii=rr.Radius.ui_points(5.0),
            labels=[view.name],
        )
    else:
        artifact = rr.LineStrips3D(
            [values],
            colors=[color],
            radii=rr.Radius.ui_points(2.0),
            labels=[view.name],
        )
    recording.log(view.plot_path, artifact, static=True)
    recording.log(
        view.data_path,
        rr.Tensor(values, dim_names=["sample", "xyz"]),
        static=True,
    )
    recording.log(
        axis_child(view.data_path, "sample"),
        rr.Tensor(
            view.coordinates,
            dim_names=[view.axis.key],
        ),
        static=True,
    )
    _log_series_metadata(recording, view, frame=view.item.frame)


def _log_curve(recording, view):
    values = view.values
    color = _entity_color(view.entity)
    chart = render_xy_chart(
        view.coordinates,
        values,
        x_name=view.axis.name,
        x_unit=view.axis.unit,
        y_name=view.name,
        y_unit=view.unit,
        color=color,
    )
    recording.log(
        view.plot_path,
        rr.EncodedImage(contents=encode_png(chart), media_type="image/png"),
        static=True,
    )
    _log_xy_data(
        recording,
        view,
        view.coordinates,
        values,
    )


def _log_grid(recording, view):
    grid = view.item
    values = view.values
    x_values, y_values = view.coordinates
    chart = render_grid_chart(
        values,
        x_values=x_values,
        y_values=y_values,
        title=grid.name,
        x_name=grid.x_axis.name,
        x_unit=grid.x_axis.unit,
        y_name=grid.y_axis.name,
        y_unit=grid.y_axis.unit,
        value_unit=grid.value_unit,
        value_min=grid.display_min if grid.has_display_range else None,
        value_max=grid.display_max if grid.has_display_range else None,
    )
    recording.log(
        view.plot_path,
        rr.EncodedImage(contents=encode_png(chart), media_type="image/png"),
        static=True,
    )
    recording.log(
        view.data_path,
        rr.Tensor(values, dim_names=[grid.y_axis.key, grid.x_axis.key]),
        static=True,
    )
    recording.log(
        axis_child(view.data_path, "x"),
        rr.Tensor(
            x_values,
            dim_names=[grid.x_axis.key],
        ),
        static=True,
    )
    recording.log(
        axis_child(view.data_path, "y"),
        rr.Tensor(
            y_values,
            dim_names=[grid.y_axis.key],
        ),
        static=True,
    )
    recording.log(
        metadata_child(view.data_path),
        rr.AnyValues(
            rows=int(grid.rows),
            columns=int(grid.columns),
            x_name=grid.x_axis.name,
            x_unit=grid.x_axis.unit,
            y_name=grid.y_axis.name,
            y_unit=grid.y_axis.unit,
            value_unit=grid.value_unit,
        ),
        static=True,
    )


def _snapshot_markdown(name, metrics):
    lines = [
        f"# {name}",
        "",
        "| State | Value | Unit |",
        "| --- | ---: | --- |",
    ]
    for metric in metrics:
        lines.append(
            f"| {metric.name} | {float(metric.value):,.6g} | {metric.unit or '—'} |"
        )
    return "\n".join(lines)


def _log_snapshot(recording, view):
    snapshot = view.item
    metrics = view.metadata
    recording.log(
        view.plot_path,
        rr.TextDocument(
            _snapshot_markdown(snapshot.name, metrics),
            media_type=rr.MediaType.MARKDOWN,
        ),
        static=True,
    )
    recording.log(
        view.data_path,
        rr.Tensor(
            view.values,
            dim_names=["metric"],
        ),
        static=True,
    )
    recording.log(
        metadata_child(view.data_path),
        rr.AnyValues(
            metric_keys=[metric.key for metric in metrics],
            metric_names=[metric.name for metric in metrics],
            metric_units=[metric.unit for metric in metrics],
        ),
        static=True,
    )


VIEW_LOGGERS = {
    SCALAR_SOURCE: _log_scalar,
    VECTOR_SOURCE: _log_vector,
    CURVE_SOURCE: _log_curve,
    GRID_SOURCE: _log_grid,
    SNAPSHOT_SOURCE: _log_snapshot,
}


def _log_result(result, recording, blueprint=None):
    catalog = build_view_catalog(result)
    if blueprint is None:
        blueprint = build_blueprint(catalog)

    _log_scenario(recording, catalog)
    for view in catalog.views:
        VIEW_LOGGERS[view.source_type](recording, view)

    recording.send_blueprint(blueprint)
    recording.flush()


def save_result(result, path):
    output_path = Path(path).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    recording = rr.RecordingStream(APPLICATION_ID)
    try:
        recording.save(str(output_path))
        _log_result(result, recording)
    finally:
        recording.disconnect()

    return output_path
