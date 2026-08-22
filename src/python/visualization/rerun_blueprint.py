import rerun as rr
import rerun.blueprint as rrb

from .rerun_paths import analysis_grid, analysis_series, telemetry_series


def _axis_label(axis):
    return f"{axis.name} ({axis.unit})" if axis.unit else axis.name


def _series_label(series):
    return f"{series.name} ({series.unit})" if series.unit else series.name


def _telemetry_container(result, axes):
    entity_grids = []

    for entity in result.entities:
        views = []

        for series in result.vectors:
            if (
                series.entity_id != entity.id
                or series.system != "kinematics"
                or not series.values
            ):
                continue
            path = telemetry_series(entity, series)
            views.append(
                rrb.TimeSeriesView(
                    origin=path,
                    contents=[path],
                    name=_series_label(series),
                )
            )

        for series in result.scalars:
            if (
                series.entity_id != entity.id
                or series.system != "kinematics"
                or not series.values
            ):
                continue
            axis = axes[series.axis_key]
            if axis.kind not in {"time", "sequence"}:
                continue
            path = telemetry_series(entity, series)
            views.append(
                rrb.TimeSeriesView(
                    origin=path,
                    contents=[path],
                    name=_series_label(series),
                )
            )

        if views:
            entity_grids.append(
                rrb.Grid(
                    *views,
                    grid_columns=2,
                    name=entity.display_name,
                )
            )

    if not entity_grids:
        return None

    return rrb.Tabs(*entity_grids, name="Telemetry")


def _analysis_container(result, entities, axes):
    views_by_owner = {entity.id: [] for entity in result.entities}
    views_by_owner[0] = []

    for series in result.scalars:
        if series.system == "kinematics" or not series.values:
            continue

        entity = entities.get(series.entity_id)
        path = analysis_series(entity, series)
        axis = axes[series.axis_key]
        owner = entity.display_name if entity is not None else "Global"
        view_name = f"{owner} — {series.name}"

        if axis.kind == "continuous":
            views_by_owner[series.entity_id].append(
                rrb.Spatial2DView(
                    origin=path,
                    contents=[path],
                    name=f"{view_name} [{_axis_label(axis)}]",
                    background=[244, 246, 248],
                )
            )
        else:
            views_by_owner[series.entity_id].append(
                rrb.TimeSeriesView(
                    origin=path,
                    contents=[path],
                    name=view_name,
                )
            )

    for series in result.vectors:
        if series.system == "kinematics" or not series.values:
            continue

        entity = entities.get(series.entity_id)
        path = analysis_series(entity, series)
        views_by_owner[series.entity_id].append(
            rrb.Spatial3DView(
                origin=path,
                contents=[path],
                name=_series_label(series),
                line_grid=True,
            )
        )

    for grid in result.grids:
        entity = entities.get(grid.entity_id)
        path = analysis_grid(entity, grid)
        owner = entity.display_name if entity is not None else "Global"
        views_by_owner[grid.entity_id].append(
            rrb.TensorView(
                origin=path,
                contents=[path],
                name=f"{owner} — {grid.name}",
                slice_selection=rrb.TensorSliceSelection(
                    width=1,
                    height=rr.TensorDimensionSelection(
                        dimension=0,
                        invert=True,
                    ),
                ),
                scalar_mapping=rrb.TensorScalarMapping(
                    colormap="turbo",
                    gamma=1.0,
                    mag_filter="nearest",
                ),
                view_fit="fill",
            )
        )

    owner_grids = []
    for entity in result.entities:
        views = views_by_owner[entity.id]
        if views:
            owner_grids.append(
                rrb.Grid(*views, grid_columns=2, name=entity.display_name)
            )

    global_views = views_by_owner[0]
    if global_views:
        owner_grids.append(rrb.Grid(*global_views, grid_columns=2, name="Global"))

    if not owner_grids:
        return None

    return rrb.Tabs(*owner_grids, name="Analysis")


def build_blueprint(result):
    entities = {entity.id: entity for entity in result.entities}
    axes = {axis.key: axis for axis in result.axes}

    tabs = [
        rrb.Spatial3DView(
            origin="/world",
            contents="/world/**",
            name="Scenario",
            line_grid=True,
        )
    ]

    telemetry = _telemetry_container(result, axes)
    if telemetry is not None:
        tabs.append(telemetry)

    analysis = _analysis_container(result, entities, axes)
    if analysis is not None:
        tabs.append(analysis)

    items = [rrb.Tabs(*tabs, name="Apogee")]
    if "simulation_time" in axes:
        items.append(
            rrb.TimePanel(timeline="simulation_time", expanded=True)
        )

    return rrb.Blueprint(*items, collapse_panels=True)
