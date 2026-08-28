import rerun.blueprint as rrb

from .telemetry_catalog import as_telemetry_catalog


def _view_label(view):
    return f"{view.name} ({view.unit})" if view.unit else view.name


def _view_from_spec(view):
    return rrb.TimeSeriesView(
        origin=view.path,
        contents=[view.path],
        name=_view_label(view),
    )


def _owner_groups(catalog):
    by_owner = {}
    for view in catalog.views:
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
    owner_layouts = [
        rrb.Grid(
            *(_view_from_spec(view) for view in views),
            grid_columns=2,
            name=owner_name,
        )
        for owner_name, views in _owner_groups(catalog)
    ]
    if not owner_layouts:
        return None
    return rrb.Tabs(*owner_layouts, name="Telemetry")


def build_blueprint(result_or_catalog):
    catalog = as_telemetry_catalog(result_or_catalog)

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

    items = [
        rrb.Tabs(*tabs, name="Apogee"),
        rrb.BlueprintPanel(expanded=True),
    ]
    timeline = (
        "simulation_time"
        if "simulation_time" in catalog.axes
        else next(iter(catalog.axes), None)
    )
    if timeline is not None:
        items.append(rrb.TimePanel(timeline=timeline, expanded=True))

    return rrb.Blueprint(*items, collapse_panels=False)
