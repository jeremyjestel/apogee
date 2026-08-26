import math
from io import BytesIO

import numpy as np
from PIL import Image, ImageDraw, ImageFont


_WIDTH = 880
_HEIGHT = 495
_PLOT_TOP = 62
_PLOT_BOTTOM = 420
_PLOT_LEFT = 88
_LINE_PLOT_RIGHT = 850
_GRID_PLOT_RIGHT = 748
_COLORBAR_LEFT = 782
_COLORBAR_RIGHT = 806

_FIGURE_COLOR = (244, 246, 248)
_AXES_COLOR = (255, 255, 255)
_TEXT_COLOR = (24, 33, 43)
_GRID_COLOR = (216, 222, 232)
_SPINE_COLOR = (104, 117, 135)


def _axis_label(name, unit):
    return f"{name} ({unit})" if unit else name


def encode_png(rgb_image):
    """Encode a rendered RGB image compactly for storage in an RRD."""
    output = BytesIO()
    image = (
        rgb_image
        if isinstance(rgb_image, Image.Image)
        else Image.fromarray(np.asarray(rgb_image, dtype=np.uint8))
    )
    image.save(
        output,
        format="PNG",
        optimize=True,
    )
    return output.getvalue()


def _font(size):
    try:
        return ImageFont.truetype("DejaVuSans.ttf", size=size)
    except OSError:
        try:
            return ImageFont.load_default(size=size)
        except TypeError:
            return ImageFont.load_default()


def _centered_text(draw, xy, label, font, fill=_TEXT_COLOR):
    bounds = draw.textbbox((0, 0), label, font=font)
    draw.text(
        (
            xy[0] - (bounds[2] - bounds[0]) / 2.0,
            xy[1] - (bounds[3] - bounds[1]) / 2.0,
        ),
        label,
        font=font,
        fill=fill,
    )


def _numeric_vector(values, name, *, require_finite=True):
    vector = np.asarray(values, dtype=np.float64)
    if vector.ndim != 1 or vector.size == 0:
        raise ValueError(f"{name} must be a nonempty one-dimensional array")
    if require_finite and not np.isfinite(vector).all():
        raise ValueError(f"{name} must contain only finite values")
    if not require_finite and not np.isfinite(vector).any():
        raise ValueError(f"{name} must contain at least one finite value")
    return vector


def _nice_limits(values, target_ticks=6):
    finite = np.asarray(values)[np.isfinite(values)]
    lower = float(np.min(finite))
    upper = float(np.max(finite))
    if lower == upper:
        padding = max(abs(lower) * 0.1, 1.0)
        lower -= padding
        upper += padding

    rough_step = (upper - lower) / max(target_ticks - 1, 1)
    magnitude = 10.0 ** math.floor(math.log10(rough_step))
    fraction = rough_step / magnitude
    step = next(
        candidate * magnitude
        for candidate in (1.0, 2.0, 2.5, 5.0, 10.0)
        if fraction <= candidate
    )
    lower = math.floor(lower / step) * step
    upper = math.ceil(upper / step) * step
    ticks = np.arange(lower, upper + step * 0.5, step, dtype=np.float64)
    return lower, upper, step, ticks


def _format_tick(value, step):
    if abs(value) < max(abs(step) * 1.0e-10, 1.0e-14):
        value = 0.0
    if abs(value) >= 1.0e7 or (0.0 < abs(value) < 1.0e-4):
        return f"{value:.2e}"
    if abs(step) >= 1.0:
        return f"{value:,.0f}"
    digits = min(6, max(1, int(math.ceil(-math.log10(abs(step)))) + 1))
    return f"{value:.{digits}f}".rstrip("0").rstrip(".")


def _linear_map(domain_min, domain_max, pixel_min, pixel_max):
    scale = (pixel_max - pixel_min) / (domain_max - domain_min)
    return lambda value: pixel_min + (float(value) - domain_min) * scale


def _draw_axes(
    draw,
    *,
    plot_right,
    title,
    x_label,
    y_label,
    x_ticks,
    y_ticks,
    x_step,
    y_step,
    display_x,
    display_y,
    fill_plot=True,
):
    title_font = _font(18)
    label_font = _font(15)
    tick_font = _font(13)
    rect = (_PLOT_LEFT, _PLOT_TOP, plot_right, _PLOT_BOTTOM)
    draw.rectangle(
        rect,
        fill=_AXES_COLOR if fill_plot else None,
        outline=_SPINE_COLOR,
        width=2,
    )

    for tick in x_ticks:
        position = display_x(tick)
        if _PLOT_LEFT <= position <= plot_right:
            draw.line(
                (position, _PLOT_TOP, position, _PLOT_BOTTOM),
                fill=_GRID_COLOR,
            )
            _centered_text(
                draw,
                (position, _PLOT_BOTTOM + 18),
                _format_tick(tick, x_step),
                tick_font,
            )

    for tick in y_ticks:
        position = display_y(tick)
        if _PLOT_TOP <= position <= _PLOT_BOTTOM:
            draw.line(
                (_PLOT_LEFT, position, plot_right, position),
                fill=_GRID_COLOR,
            )
            label = _format_tick(tick, y_step)
            bounds = draw.textbbox((0, 0), label, font=tick_font)
            draw.text(
                (_PLOT_LEFT - (bounds[2] - bounds[0]) - 10, position - 7),
                label,
                font=tick_font,
                fill=_TEXT_COLOR,
            )

    draw.rectangle(rect, outline=_SPINE_COLOR, width=2)
    _centered_text(draw, (_WIDTH / 2.0, 28), title, title_font)
    _centered_text(
        draw,
        ((_PLOT_LEFT + plot_right) / 2.0, _HEIGHT - 22),
        x_label,
        label_font,
    )
    draw.text(
        (_PLOT_LEFT, _PLOT_TOP - 25),
        y_label,
        font=label_font,
        fill=_TEXT_COLOR,
    )


def render_xy_chart(
    x_values,
    y_values,
    *,
    x_name,
    x_unit,
    y_name,
    y_unit,
    color,
):
    """Render a formal static X/Y analysis chart as an RGB image."""
    x = _numeric_vector(x_values, "Chart X values")
    y = _numeric_vector(y_values, "Chart Y values", require_finite=False)
    if len(x) != len(y):
        raise ValueError("Chart axes must have matching lengths")

    x_min, x_max, x_step, x_ticks = _nice_limits(x)
    y_min, y_max, y_step, y_ticks = _nice_limits(y)
    display_x = _linear_map(x_min, x_max, _PLOT_LEFT, _LINE_PLOT_RIGHT)
    display_y = _linear_map(y_min, y_max, _PLOT_BOTTOM, _PLOT_TOP)

    image = Image.new("RGB", (_WIDTH, _HEIGHT), _FIGURE_COLOR)
    draw = ImageDraw.Draw(image)
    _draw_axes(
        draw,
        plot_right=_LINE_PLOT_RIGHT,
        title=f"{y_name} vs {x_name}",
        x_label=_axis_label(x_name, x_unit),
        y_label=_axis_label(y_name, y_unit),
        x_ticks=x_ticks,
        y_ticks=y_ticks,
        x_step=x_step,
        y_step=y_step,
        display_x=display_x,
        display_y=display_y,
    )

    chart_color = tuple(int(channel) for channel in color[:3])
    finite = np.isfinite(y)
    start = 0
    while start < len(x):
        while start < len(x) and not finite[start]:
            start += 1
        end = start
        while end < len(x) and finite[end]:
            end += 1
        points = [(display_x(x[i]), display_y(y[i])) for i in range(start, end)]
        if len(points) == 1:
            px, py = points[0]
            draw.ellipse((px - 3, py - 3, px + 3, py + 3), fill=chart_color)
        elif points:
            draw.line(points, fill=chart_color, width=3, joint="curve")
        start = end

    legend_font = _font(14)
    bounds = draw.textbbox((0, 0), y_name, font=legend_font)
    legend_left = _LINE_PLOT_RIGHT - (bounds[2] - bounds[0]) - 58
    draw.rounded_rectangle(
        (legend_left, _PLOT_TOP + 12, _LINE_PLOT_RIGHT - 12, _PLOT_TOP + 42),
        radius=4,
        fill=_AXES_COLOR,
        outline=_GRID_COLOR,
    )
    draw.line(
        (legend_left + 10, _PLOT_TOP + 27, legend_left + 34, _PLOT_TOP + 27),
        fill=chart_color,
        width=3,
    )
    draw.text(
        (legend_left + 40, _PLOT_TOP + 18),
        y_name,
        font=legend_font,
        fill=_TEXT_COLOR,
    )
    return image


def _cell_edges(coordinates):
    if len(coordinates) == 1:
        spacing = max(abs(float(coordinates[0])) * 0.1, 1.0)
        return np.asarray(
            [coordinates[0] - spacing / 2.0, coordinates[0] + spacing / 2.0]
        )
    differences = np.diff(coordinates)
    if not (np.all(differences > 0.0) or np.all(differences < 0.0)):
        raise ValueError("Grid coordinates must be strictly monotonic")
    return np.concatenate(
        (
            [coordinates[0] - differences[0] / 2.0],
            coordinates[:-1] + differences / 2.0,
            [coordinates[-1] + differences[-1] / 2.0],
        )
    )


def _turbo(values):
    # Google's Turbo polynomial approximation, evaluated for an arbitrary array.
    coefficients = np.asarray(
        [
            [0.13572138, 4.61539260, -42.66032258, 132.13108234, -152.94239396, 59.28637943],
            [0.09140261, 2.19418839, 4.84296658, -14.18503333, 4.27729857, 2.82956604],
            [0.10667330, 12.64194608, -60.58204836, 110.36276771, -89.90310912, 27.34824973],
        ],
        dtype=np.float64,
    )
    rgb = np.zeros(values.shape + (3,), dtype=np.float64)
    power = np.ones_like(values, dtype=np.float64)
    for exponent in range(6):
        rgb += power[..., None] * coefficients[:, exponent]
        power *= values
    return np.asarray(np.clip(rgb, 0.0, 1.0) * 255.0, dtype=np.uint8)


def _heatmap_raster(data, x, y, lower, upper):
    if x[0] > x[-1]:
        x = x[::-1]
        data = data[:, ::-1]
    if y[0] > y[-1]:
        y = y[::-1]
        data = data[::-1, :]
    x_edges = _cell_edges(x)
    y_edges = _cell_edges(y)

    width = _GRID_PLOT_RIGHT - _PLOT_LEFT - 1
    height = _PLOT_BOTTOM - _PLOT_TOP - 1
    x_pixels = np.linspace(x_edges[0], x_edges[-1], width, endpoint=False)
    y_pixels = np.linspace(y_edges[-1], y_edges[0], height, endpoint=False)
    columns = np.clip(np.searchsorted(x_edges, x_pixels) - 1, 0, len(x) - 1)
    rows = np.clip(np.searchsorted(y_edges, y_pixels) - 1, 0, len(y) - 1)
    sampled = data[rows[:, None], columns[None, :]]
    normalized = np.clip((sampled - lower) / (upper - lower), 0.0, 1.0)
    rgb = _turbo(np.nan_to_num(normalized, nan=0.0, posinf=1.0, neginf=0.0))
    rgb[~np.isfinite(sampled)] = _AXES_COLOR
    return Image.fromarray(rgb), x_edges, y_edges


def render_grid_chart(
    values,
    *,
    x_values,
    y_values,
    title,
    x_name,
    x_unit,
    y_name,
    y_unit,
    value_unit,
    value_min=None,
    value_max=None,
):
    """Render a coordinate-aware heatmap with a calibrated color bar."""
    data = np.asarray(values, dtype=np.float64)
    x = _numeric_vector(x_values, "Grid X coordinates")
    y = _numeric_vector(y_values, "Grid Y coordinates")
    if data.ndim != 2 or data.size == 0:
        raise ValueError("Grid data must be a nonempty two-dimensional array")
    if data.shape != (len(y), len(x)):
        raise ValueError("Grid axes must match the data rows and columns")

    finite = data[np.isfinite(data)]
    if finite.size == 0:
        raise ValueError("Grid data must contain at least one finite value")
    lower = float(np.min(finite) if value_min is None else value_min)
    upper = float(np.max(finite) if value_max is None else value_max)
    if not np.isfinite([lower, upper]).all() or lower > upper:
        raise ValueError("Grid display range must be finite and increasing")
    if lower == upper:
        padding = max(abs(lower) * 0.1, 1.0)
        lower -= padding
        upper += padding

    raster, x_edges, y_edges = _heatmap_raster(data, x, y, lower, upper)
    x_min, x_max = float(np.min(x_edges)), float(np.max(x_edges))
    y_min, y_max = float(np.min(y_edges)), float(np.max(y_edges))
    x_ticks = np.linspace(float(np.min(x)), float(np.max(x)), min(len(x), 6))
    y_ticks = np.linspace(float(np.min(y)), float(np.max(y)), min(len(y), 6))
    x_step = max((x_ticks[-1] - x_ticks[0]) / max(len(x_ticks) - 1, 1), 1.0)
    y_step = max((y_ticks[-1] - y_ticks[0]) / max(len(y_ticks) - 1, 1), 1.0)
    display_x = _linear_map(x_min, x_max, _PLOT_LEFT, _GRID_PLOT_RIGHT)
    display_y = _linear_map(y_min, y_max, _PLOT_BOTTOM, _PLOT_TOP)

    image = Image.new("RGB", (_WIDTH, _HEIGHT), _FIGURE_COLOR)
    image.paste(raster, (_PLOT_LEFT + 1, _PLOT_TOP + 1))
    draw = ImageDraw.Draw(image)
    _draw_axes(
        draw,
        plot_right=_GRID_PLOT_RIGHT,
        title=title,
        x_label=_axis_label(x_name, x_unit),
        y_label=_axis_label(y_name, y_unit),
        x_ticks=x_ticks,
        y_ticks=y_ticks,
        x_step=x_step,
        y_step=y_step,
        display_x=display_x,
        display_y=display_y,
        fill_plot=False,
    )

    color_values = np.linspace(1.0, 0.0, _PLOT_BOTTOM - _PLOT_TOP - 1)
    colorbar = np.repeat(_turbo(color_values)[:, None, :], _COLORBAR_RIGHT - _COLORBAR_LEFT, axis=1)
    image.paste(Image.fromarray(colorbar), (_COLORBAR_LEFT, _PLOT_TOP + 1))
    draw.rectangle(
        (_COLORBAR_LEFT, _PLOT_TOP, _COLORBAR_RIGHT, _PLOT_BOTTOM),
        outline=_SPINE_COLOR,
        width=2,
    )
    color_step = (upper - lower) / 4.0
    tick_font = _font(12)
    for value in np.linspace(lower, upper, 5):
        position = _linear_map(lower, upper, _PLOT_BOTTOM, _PLOT_TOP)(value)
        draw.line((_COLORBAR_RIGHT, position, _COLORBAR_RIGHT + 5, position), fill=_SPINE_COLOR)
        draw.text(
            (_COLORBAR_RIGHT + 8, position - 7),
            _format_tick(value, color_step),
            font=tick_font,
            fill=_TEXT_COLOR,
        )
    _centered_text(
        draw,
        ((_COLORBAR_LEFT + _COLORBAR_RIGHT) / 2.0, _PLOT_TOP - 16),
        value_unit,
        _font(13),
    )
    return image
