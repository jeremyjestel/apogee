import math

import numpy as np
from PIL import Image, ImageDraw, ImageFont


_WIDTH = 880
_HEIGHT = 495
_PLOT_LEFT = 88
_PLOT_RIGHT = 850
_PLOT_TOP = 62
_PLOT_BOTTOM = 420

_FIGURE_COLOR = (244, 246, 248)
_AXES_COLOR = (255, 255, 255)
_TEXT_COLOR = (24, 33, 43)
_GRID_COLOR = (216, 222, 232)
_SPINE_COLOR = (104, 117, 135)


def _axis_label(name, unit):
    return f"{name} ({unit})" if unit else name


def _line_color(rgb):
    return tuple(int(value) for value in rgb)


def _nice_axis_limits(values, target_tick_count=6):
    # Expand a constant series so it still has a visible plotting range.
    minimum = float(np.min(values))
    maximum = float(np.max(values))
    if minimum == maximum:
        padding = max(abs(minimum) * 0.1, 1.0)
        minimum -= padding
        maximum += padding

    # Round the raw interval to a conventional 1, 2, 2.5, 5, or 10 tick step.
    span = maximum - minimum
    rough_step = span / max(target_tick_count - 1, 1)
    magnitude = 10.0 ** math.floor(math.log10(rough_step))
    fraction = rough_step / magnitude
    for candidate in (1.0, 2.0, 2.5, 5.0, 10.0):
        if fraction <= candidate:
            step = candidate * magnitude
            break

    # Snap both limits outward to exact multiples of the chosen step.
    lower = math.floor(minimum / step) * step
    upper = math.ceil(maximum / step) * step
    tick_count = int(round((upper - lower) / step)) + 1
    ticks = [lower + index * step for index in range(tick_count)]
    return lower, upper, step, ticks


def _format_tick(value, step):
    # Suppress floating-point noise around zero before choosing display precision.
    if abs(value) < max(abs(step) * 1e-10, 1e-14):
        value = 0.0
    if abs(value) >= 1e7 or (0.0 < abs(value) < 1e-4):
        return f"{value:.2e}"
    if abs(step) >= 1.0:
        return f"{value:,.0f}"

    # Derive the decimal count from the tick spacing while keeping labels compact.
    digits = min(
        6,
        max(1, int(math.ceil(-math.log10(abs(step)))) + 1),
    )
    return f"{value:.{digits}f}".rstrip("0").rstrip(".")


def _centered_text(draw, xy, text, font, fill):
    # Measure rendered bounds because Pillow positions text from its top-left corner.
    bounds = draw.textbbox((0, 0), text, font=font)
    width = bounds[2] - bounds[0]
    height = bounds[3] - bounds[1]
    draw.text(
        (xy[0] - width / 2.0, xy[1] - height / 2.0),
        text,
        font=font,
        fill=fill,
    )


def _font(size):
    # Prefer a scalable bundled-style font, then support older Pillow default-font APIs.
    try:
        return ImageFont.truetype("DejaVuSans.ttf", size=size)
    except OSError:
        try:
            return ImageFont.load_default(size=size)
        except TypeError:
            return ImageFont.load_default()


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
    """Return an RGB image containing a labeled, independently scaled XY chart."""
    # Normalize both axes to numeric arrays before calculating their independent scales.
    x = np.asarray(x_values, dtype=np.float64)
    y = np.asarray(y_values, dtype=np.float64)
    if len(x) == 0 or len(x) != len(y):
        raise ValueError("Chart axes must be nonempty and have matching lengths")

    x_min, x_max, x_step, x_ticks = _nice_axis_limits(x)
    y_min, y_max, y_step, y_ticks = _nice_axis_limits(y)

    # Map physical X values into horizontal plot pixels.
    def display_x(value):
        fraction = (float(value) - x_min) / (x_max - x_min)
        return _PLOT_LEFT + fraction * (_PLOT_RIGHT - _PLOT_LEFT)

    # Invert Y because image coordinates increase downward from the top edge.
    def display_y(value):
        fraction = (float(value) - y_min) / (y_max - y_min)
        return _PLOT_BOTTOM - fraction * (_PLOT_BOTTOM - _PLOT_TOP)

    # Create the drawing surface and fonts used for the complete chart.
    image = Image.new("RGB", (_WIDTH, _HEIGHT), _FIGURE_COLOR)
    draw = ImageDraw.Draw(image)
    title_font = _font(18)
    label_font = _font(15)
    tick_font = _font(13)
    legend_font = _font(14)

    # Paint the plot area and its initial border over the figure background.
    draw.rectangle(
        (_PLOT_LEFT, _PLOT_TOP, _PLOT_RIGHT, _PLOT_BOTTOM),
        fill=_AXES_COLOR,
        outline=_SPINE_COLOR,
        width=2,
    )

    # Draw vertical grid lines and centered labels for the X axis.
    for tick in x_ticks:
        position = display_x(tick)
        draw.line(
            (position, _PLOT_TOP, position, _PLOT_BOTTOM),
            fill=_GRID_COLOR,
            width=1,
        )
        _centered_text(
            draw,
            (position, _PLOT_BOTTOM + 18),
            _format_tick(tick, x_step),
            tick_font,
            _TEXT_COLOR,
        )

    # Draw horizontal grid lines with right-aligned labels for the Y axis.
    for tick in y_ticks:
        position = display_y(tick)
        draw.line(
            (_PLOT_LEFT, position, _PLOT_RIGHT, position),
            fill=_GRID_COLOR,
            width=1,
        )
        label = _format_tick(tick, y_step)
        bounds = draw.textbbox((0, 0), label, font=tick_font)
        draw.text(
            (_PLOT_LEFT - (bounds[2] - bounds[0]) - 10, position - 7),
            label,
            font=tick_font,
            fill=_TEXT_COLOR,
        )

    # Redraw the border over the grid lines to keep the plot boundary crisp.
    draw.rectangle(
        (_PLOT_LEFT, _PLOT_TOP, _PLOT_RIGHT, _PLOT_BOTTOM),
        outline=_SPINE_COLOR,
        width=2,
    )

    # Convert every data pair to pixels and draw a point or connected line as appropriate.
    points = [
        (display_x(x_value), display_y(y_value))
        for x_value, y_value in zip(x, y)
    ]
    chart_color = _line_color(color)
    if len(points) == 1:
        px, py = points[0]
        draw.ellipse((px - 3, py - 3, px + 3, py + 3), fill=chart_color)
    else:
        draw.line(points, fill=chart_color, width=3, joint="curve")

    # Add the chart title and both physical axis labels outside the plot area.
    _centered_text(
        draw,
        (_WIDTH / 2.0, 28),
        f"{y_name} vs {x_name}",
        title_font,
        _TEXT_COLOR,
    )
    _centered_text(
        draw,
        ((_PLOT_LEFT + _PLOT_RIGHT) / 2.0, _HEIGHT - 22),
        _axis_label(x_name, x_unit),
        label_font,
        _TEXT_COLOR,
    )
    draw.text(
        (_PLOT_LEFT, _PLOT_TOP - 25),
        _axis_label(y_name, y_unit),
        font=label_font,
        fill=_TEXT_COLOR,
    )

    # Size and place a compact legend against the upper-right plot corner.
    legend_text_bounds = draw.textbbox((0, 0), y_name, font=legend_font)
    legend_width = legend_text_bounds[2] - legend_text_bounds[0]
    legend_left = _PLOT_RIGHT - legend_width - 58
    draw.rounded_rectangle(
        (legend_left, _PLOT_TOP + 12, _PLOT_RIGHT - 12, _PLOT_TOP + 42),
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

    # Return an owned NumPy buffer so it remains valid after the Pillow image is released.
    return np.asarray(image, dtype=np.uint8).copy()
