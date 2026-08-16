import math

import matplotlib.pyplot as plt


#May have to update for color plots but fine for now

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


def _plot_simulation(simulation):
    outputs = list(simulation.outputs)
    if not outputs:
        return None

    rows, columns = _subplot_shape(len(outputs))
    figure, axes = plt.subplots(
        rows,
        columns,
        figsize=(7 * columns, 4 * rows),
        squeeze=False,
    )

    times_s = list(simulation.times_s)
    for axis, output in zip(axes.flat, outputs):
        values = list(output.values)
        _validate_lengths(
            f"Simulation output '{output.name}'",
            times_s=times_s,
            values=values,
        )

        axis.plot(times_s, values)
        axis.set_title(output.name)
        axis.set_xlabel("Time (s)")
        axis.set_ylabel(_axis_label(output.name, output.unit))
        axis.grid(True)

    for unused_axis in list(axes.flat)[len(outputs):]:
        unused_axis.set_visible(False)

    figure.suptitle(simulation.name or "Simulation Data")
    figure.tight_layout()
    return figure


def _plot_analyses_2d(analyses):
    plots = [
        (analysis, y_series)
        for analysis in analyses
        for y_series in analysis.y
    ]
    if not plots:
        return None

    rows, columns = _subplot_shape(len(plots))
    figure, axes = plt.subplots(
        rows,
        columns,
        figsize=(7 * columns, 4 * rows),
        squeeze=False,
    )

    for axis, (analysis, y_series) in zip(axes.flat, plots):
        x_values = list(analysis.x.values)
        y_values = list(y_series.values)
        _validate_lengths(
            f"2D analysis '{analysis.name}' / '{y_series.name}'",
            x=x_values,
            y=y_values,
        )

        axis.plot(x_values, y_values)
        axis.set_title(analysis.name or y_series.name)
        axis.set_xlabel(_axis_label(analysis.x.name, analysis.x.unit))
        axis.set_ylabel(_axis_label(y_series.name, y_series.unit))
        axis.grid(True)

    for unused_axis in list(axes.flat)[len(plots):]:
        unused_axis.set_visible(False)

    figure.suptitle("2D Analysis")
    figure.tight_layout()
    return figure


def _plot_analyses_3d(analyses):
    analyses = list(analyses)
    if not analyses:
        return None

    rows, columns = _subplot_shape(len(analyses))
    figure = plt.figure(figsize=(7 * columns, 5 * rows))

    for index, analysis in enumerate(analyses, start=1):
        x_values = list(analysis.x.values)
        y_values = list(analysis.y.values)
        z_values = list(analysis.z.values)
        _validate_lengths(
            f"3D analysis '{analysis.name}'",
            x=x_values,
            y=y_values,
            z=z_values,
        )

        axis = figure.add_subplot(rows, columns, index, projection="3d")
        axis.scatter(x_values, y_values, z_values)
        axis.set_title(analysis.name)
        axis.set_xlabel(_axis_label(analysis.x.name, analysis.x.unit))
        axis.set_ylabel(_axis_label(analysis.y.name, analysis.y.unit))
        axis.set_zlabel(_axis_label(analysis.z.name, analysis.z.unit))

    figure.suptitle("3D Analysis")
    figure.tight_layout()
    return figure


def plot_result(result):
    """Plot every populated section of an Apogee Result."""
    figures = [
        _plot_simulation(result.simulation),
        _plot_analyses_2d(result.analysis_2d),
        _plot_analyses_3d(result.analysis_3d),
    ]
    figures = [figure for figure in figures if figure is not None]

    if figures:
        plt.show()

    return figures
