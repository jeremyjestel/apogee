import math

import matplotlib.pyplot as plt


MAX_SUBPLOT_COLUMNS = 3


def _axis_label(name, unit):
    if name and unit:
        return f"{name} ({unit})"
    return name or unit


def _subplot_shape(count):
    columns = min(MAX_SUBPLOT_COLUMNS, count)
    rows = math.ceil(count / columns)
    return rows, columns


def _validate_lengths(context, **series):
    lengths = {name: len(values) for name, values in series.items()}
    if len(set(lengths.values())) > 1:
        details = ", ".join(f"{name}={length}" for name, length in lengths.items())
        raise ValueError(f"{context} contains mismatched series lengths: {details}")


def _group_by_entity(outputs):
    grouped_outputs = {}
    for output in outputs:
        entity_name = output.entity_name or "Unnamed Entity"
        grouped_outputs.setdefault(entity_name, []).append(output)
    return grouped_outputs


def _set_window_title(figure, title):
    manager = figure.canvas.manager
    if manager is not None:
        manager.set_window_title(title)


def _maximize_window(figure):
    manager = figure.canvas.manager
    if manager is None or not hasattr(manager, "window"):
        return

    window = manager.window
    if hasattr(window, "showMaximized"):
        window.showMaximized()
    elif hasattr(window, "state"):
        window.state("zoomed")
    elif hasattr(window, "Maximize"):
        window.Maximize(True)


def _hide_unused_axes(axes, used_count):
    for unused_axis in list(axes.flat)[used_count:]:
        unused_axis.set_visible(False)


def _plot_simulation_2d(simulation):
    figures = []
    times_s = list(simulation.times_s)

    for entity_name, outputs in _group_by_entity(simulation.outputs).items():
        rows, columns = _subplot_shape(len(outputs))
        figure, axes = plt.subplots(
            rows,
            columns,
            figsize=(7 * columns, 4 * rows),
            squeeze=False,
        )

        for axis, output in zip(axes.flat, outputs):
            values = list(output.values)
            _validate_lengths(
                f"2D simulation output '{entity_name} / {output.name}'",
                times_s=times_s,
                values=values,
            )

            axis.plot(times_s, values)
            axis.set_title(output.name)
            axis.set_xlabel("Time (s)")
            axis.set_ylabel(_axis_label(output.name, output.unit))
            axis.grid(True)

        _hide_unused_axes(axes, len(outputs))
        title = f"{simulation.name} - {entity_name}" if simulation.name else entity_name
        _set_window_title(figure, title)
        figure.suptitle(title)
        figure.tight_layout()
        _maximize_window(figure)
        figures.append(figure)

    return figures


def _plot_simulation_3d(simulation):
    figures = []
    times_s = list(simulation.times_s)

    for entity_name, outputs in _group_by_entity(simulation.outputs).items():
        rows, columns = _subplot_shape(len(outputs))
        figure = plt.figure(figsize=(7 * columns, 5 * rows))

        for index, output in enumerate(outputs, start=1):
            x_values = list(output.x)
            y_values = list(output.y)
            z_values = list(output.z)
            _validate_lengths(
                f"3D simulation output '{entity_name} / {output.name}'",
                times_s=times_s,
                x=x_values,
                y=y_values,
                z=z_values,
            )

            axis = figure.add_subplot(rows, columns, index, projection="3d")
            axis.plot(x_values, y_values, z_values)
            axis.set_title(output.name)
            axis.set_xlabel(_axis_label("X", output.unit))
            axis.set_ylabel(_axis_label("Y", output.unit))
            axis.set_zlabel(_axis_label("Z", output.unit))

        title = f"{simulation.name} - {entity_name}" if simulation.name else entity_name
        _set_window_title(figure, title)
        figure.suptitle(title)
        figure.tight_layout()
        _maximize_window(figure)
        figures.append(figure)

    return figures


def _plot_analyses_2d(analyses):
    figures = []

    for analysis in analyses:
        y_series_collection = list(analysis.y)
        if not y_series_collection:
            continue

        rows, columns = _subplot_shape(len(y_series_collection))
        figure, axes = plt.subplots(
            rows,
            columns,
            figsize=(7 * columns, 4 * rows),
            squeeze=False,
        )

        for axis, y_series in zip(axes.flat, y_series_collection):
            x_values = list(analysis.x.values)
            y_values = list(y_series.values)
            _validate_lengths(
                f"2D analysis '{analysis.name}' / '{y_series.name}'",
                x=x_values,
                y=y_values,
            )

            axis.plot(x_values, y_values)
            axis.set_title(y_series.name)
            axis.set_xlabel(_axis_label(analysis.x.name, analysis.x.unit))
            axis.set_ylabel(_axis_label(y_series.name, y_series.unit))
            axis.grid(True)

        _hide_unused_axes(axes, len(y_series_collection))
        title = analysis.name or "2D Analysis"
        _set_window_title(figure, title)
        figure.suptitle(title)
        figure.tight_layout()
        _maximize_window(figure)
        figures.append(figure)

    return figures


def _plot_analyses_3d(analyses):
    figures = []

    for analysis in analyses:
        x_values = list(analysis.x.values)
        y_values = list(analysis.y.values)
        z_values = list(analysis.z.values)
        _validate_lengths(
            f"3D analysis '{analysis.name}'",
            x=x_values,
            y=y_values,
            z=z_values,
        )

        figure = plt.figure(figsize=(7, 5))
        axis = figure.add_subplot(1, 1, 1, projection="3d")
        axis.scatter(x_values, y_values, z_values)
        axis.set_xlabel(_axis_label(analysis.x.name, analysis.x.unit))
        axis.set_ylabel(_axis_label(analysis.y.name, analysis.y.unit))
        axis.set_zlabel(_axis_label(analysis.z.name, analysis.z.unit))

        title = analysis.name or "3D Analysis"
        axis.set_title(title)
        _set_window_title(figure, title)
        figure.tight_layout()
        _maximize_window(figure)
        figures.append(figure)

    return figures


def plot_result(result):
    """Create separate figures for each simulated entity and analysis result."""
    figures = []
    figures.extend(_plot_simulation_2d(result.simulation_2d))
    figures.extend(_plot_simulation_3d(result.simulation_3d))
    figures.extend(_plot_analyses_2d(result.analysis_2d))
    figures.extend(_plot_analyses_3d(result.analysis_3d))

    if figures:
        plt.show()

    return figures
