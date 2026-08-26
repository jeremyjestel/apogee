import rerun.blueprint as rrb

from .view_catalog import (
    SPATIAL_2D_VIEW,
    SPATIAL_3D_VIEW,
    TEXT_VIEW,
    TIME_SERIES_VIEW,
    as_view_catalog,
)


def _view_label(view):
    return f"{view.name} ({view.unit})" if view.unit else view.name


def _view_from_spec(view):
    common = {
        "origin": view.plot_path,
        "contents": [view.plot_path],
        "name": _view_label(view),
    }
    if view.view_type == TIME_SERIES_VIEW:
        return rrb.TimeSeriesView(**common)
    if view.view_type == SPATIAL_2D_VIEW:
        return rrb.Spatial2DView(**common, background=[244, 246, 248])
    if view.view_type == SPATIAL_3D_VIEW:
        return rrb.Spatial3DView(**common, line_grid=True)
    if view.view_type == TEXT_VIEW:
        return rrb.TextDocumentView(**common)
    raise ValueError(f"Unsupported catalog view type: {view.view_type}")


def _owner_groups(catalog, section):
    by_owner = {}
    for view in catalog.in_section(section):
        by_owner.setdefault(view.owner_id, []).append(view)

    groups = []
    for entity in catalog.entity_items:
        owner_views = by_owner.get(entity.id, ())
        if owner_views:
            groups.append((entity.display_name, owner_views))
    if by_owner.get(0):
        groups.append(("Global", by_owner[0]))
    return groups


def _telemetry_container(catalog):
    # Telemetry retains compact grids within one tab per owner.
    owner_grids = [
        rrb.Grid(
            *(_view_from_spec(view) for view in views),
            grid_columns=2,
            name=owner_name,
        )
        for owner_name, views in _owner_groups(catalog, "telemetry")
    ]
    if not owner_grids:
        return None
    return rrb.Tabs(*owner_grids, name="Telemetry")


def _analysis_container(catalog):
    # Every analysis product gets a full-size tab nested below its owner.
    owner_tabs = []
    for owner_name, views in _owner_groups(catalog, "analysis"):
        grouped = {}
        nodes = []
        for view in views:
            if view.group:
                grouped.setdefault(view.group, []).append(view)
            else:
                nodes.append((view.display_sort_key, _view_from_spec(view)))

        for group_name, group_views in grouped.items():
            nodes.append(
                (
                    min(view.display_sort_key for view in group_views),
                    rrb.Tabs(
                        *(_view_from_spec(view) for view in group_views),
                        name=group_name,
                    ),
                )
            )

        nodes.sort(key=lambda node: node[0])
        owner_tabs.append(
            rrb.Tabs(*(node[1] for node in nodes), name=owner_name)
        )
    if not owner_tabs:
        return None
    return rrb.Tabs(*owner_tabs, name="Analysis")


def build_blueprint(result_or_catalog):
    # Reusing a catalog prevents logging and layout from classifying data separately.
    catalog = as_view_catalog(result_or_catalog)

    tabs = [
        rrb.Spatial3DView(
            origin="/world",
            contents="/world/**",
            name="Scenario (ECI km)",
            line_grid=True,
        )
    ]

    telemetry = _telemetry_container(catalog)
    if telemetry is not None:
        tabs.append(telemetry)

    analysis = _analysis_container(catalog)
    if analysis is not None:
        tabs.append(analysis)

    items = [
        rrb.Tabs(*tabs, name="Apogee"),
        rrb.BlueprintPanel(expanded=True),
    ]
    if "simulation_time" in catalog.axes:
        items.append(rrb.TimePanel(timeline="simulation_time", expanded=True))

    return rrb.Blueprint(*items, collapse_panels=False)
