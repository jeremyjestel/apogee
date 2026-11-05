"""Qt/Matplotlib renderers for completed analysis and logged state histories."""

import numpy as np
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg, NavigationToolbar2QT
from matplotlib.figure import Figure
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDoubleSpinBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QSlider,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from .catalog import (
    ARRAY_SERIES, CURVE, GRID_SERIES, METRIC_TABLE,
    RANGE_DOPPLER_MAP, RANGE_PULSE_MAP, RANGE_VELOCITY_MAP, TRAJECTORY_3D,
    AnalysisProduct,
)


TEAM_COLORS = {"blue": "#286eff", "red": "#ff3737"}
DEFAULT_COLOR = "#356ea8"


def _label(name, unit):
    return f"{name} ({unit})" if unit else name


def _cell_edges(coordinates):
    coordinates = np.asarray(coordinates, dtype=np.float64)
    if len(coordinates) == 1:
        spacing = max(abs(float(coordinates[0])) * 0.1, 1.0)
        return coordinates[0] + np.asarray([-spacing / 2.0, spacing / 2.0])
    differences = np.diff(coordinates)
    return np.concatenate(
        ([coordinates[0] - differences[0] / 2.0],
         coordinates[:-1] + differences / 2.0,
         [coordinates[-1] + differences[-1] / 2.0])
    )


class FigureWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.figure = Figure(figsize=(10, 6))
        self.figure.subplots_adjust(left=0.09, right=0.92, bottom=0.11, top=0.9)
        self.canvas = FigureCanvasQTAgg(self.figure)
        self.canvas.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.toolbar = NavigationToolbar2QT(self.canvas, self)
        self.canvas.mpl_connect("scroll_event", self._scroll_zoom)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.toolbar)
        layout.addWidget(self.canvas, 1)

    def enable_navigation(self, plot):
        plot.set_navigate(True)
        if hasattr(plot, "get_zlim"):
            plot.mouse_init(rotate_btn=1, pan_btn=2, zoom_btn=3)
        elif not self.toolbar.mode:
            # Make ordinary left-drag pan without requiring a toolbar selection.
            self.toolbar.pan()

    def _scroll_zoom(self, event):
        plot = event.inaxes
        if plot is None or not plot.get_navigate():
            return
        self.canvas.setFocus()
        if self.toolbar._nav_stack() is None:
            self.toolbar.push_current()
        scale = 1.2 ** (-event.step)
        if hasattr(plot, "get_zlim"):
            dimensions = ((plot.get_xlim, plot.set_xlim, None),
                          (plot.get_ylim, plot.set_ylim, None),
                          (plot.get_zlim, plot.set_zlim, None))
        else:
            dimensions = ((plot.get_xlim, plot.set_xlim, event.xdata),
                          (plot.get_ylim, plot.set_ylim, event.ydata))
        for get_limits, set_limits, center in dimensions:
            lower, upper = get_limits()
            center = (lower + upper) / 2 if center is None else center
            set_limits(center + (lower - center) * scale,
                       center + (upper - center) * scale)
        self.toolbar.push_current()
        self.canvas.draw_idle()


class TimeControl(QWidget):
    """Shared nearest-sample control for any time-indexed analysis renderer."""

    def __init__(self, axis, select, parent=None):
        super().__init__(parent)
        self.axis = axis
        self.select = select
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.addWidget(QLabel("Time:"))

        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setRange(0, len(axis.values) - 1)
        self.slider.setPageStep(max(1, len(axis.values) // 10))
        layout.addWidget(self.slider, 1)

        self.value = QDoubleSpinBox()
        self.value.setDecimals(6)
        self.value.setRange(float(np.min(axis.values)), float(np.max(axis.values)))
        self.value.setSuffix(f" {axis.unit}" if axis.unit else "")
        self.value.setKeyboardTracking(False)
        layout.addWidget(self.value)

        self.slider.valueChanged.connect(self._set_index)
        self.value.valueChanged.connect(self._set_time)

    def _set_time(self, value):
        index = int(np.argmin(np.abs(self.axis.values - value)))
        if index == self.slider.value():
            self._set_index(index)
        else:
            self.slider.setValue(index)

    def _set_index(self, index):
        time_value = float(self.axis.values[index])
        self.value.blockSignals(True)
        self.value.setValue(time_value)
        self.value.blockSignals(False)
        self.select(int(index), time_value)


def render_curve(product: AnalysisProduct):
    widget = FigureWidget()
    plot = widget.figure.add_subplot()
    x_axis = product.axes[0]
    color = (
        TEAM_COLORS.get(product.entity.team.lower(), DEFAULT_COLOR)
        if product.entity else DEFAULT_COLOR
    )
    plot.plot(
        x_axis.values,
        np.ma.masked_invalid(product.values),
        color=color,
        linewidth=2.0,
    )
    plot.set_title(f"{product.name} vs {x_axis.name}")
    plot.set_xlabel(_label(x_axis.name, x_axis.unit))
    plot.set_ylabel(_label(product.name, product.value_unit))
    plot.grid(True, color="#d8dee8", linewidth=0.8, alpha=0.8)
    widget.enable_navigation(plot)
    widget.canvas.draw()
    return widget


class Trajectory3DWidget(FigureWidget):
    """Follow a vector history without changing the interactive camera view."""

    def __init__(self, product):
        super().__init__()
        self.product = product
        self.plot = self.figure.add_subplot(projection="3d")
        self.enable_navigation(self.plot)
        self.positions = np.where(
            np.all(np.isfinite(product.values), axis=1)[:, None],
            product.values, np.nan,
        )
        color = (
            TEAM_COLORS.get(product.entity.team.lower(), DEFAULT_COLOR)
            if product.entity else DEFAULT_COLOR
        )
        self.path_line, = self.plot.plot(
            *self.positions.T, color=color, alpha=0.22, linewidth=1.5,
        )
        self.trajectory_line, = self.plot.plot(
            [], [], [], color=color, linewidth=2.0,
        )
        self.current_point, = self.plot.plot(
            [], [], [], marker="o", linestyle="none", color=color, markersize=6,
        )
        self.plot.set_xlabel(_label("X", product.value_unit))
        self.plot.set_ylabel(_label("Y", product.value_unit))
        self.plot.set_zlabel(_label("Z", product.value_unit))
        self.plot.set_box_aspect((1, 1, 1))
        points = self.positions[np.all(np.isfinite(self.positions), axis=1)]
        if len(points):
            lower, upper = points.min(axis=0), points.max(axis=0)
            center = (lower + upper) / 2.0
            half_span = max(float(np.max(upper - lower)) * 0.55, 1.0)
            self.plot.set_xlim(center[0] - half_span, center[0] + half_span)
            self.plot.set_ylim(center[1] - half_span, center[1] + half_span)
            self.plot.set_zlim(center[2] - half_span, center[2] + half_span)
        self.time_control = TimeControl(product.axes[0], self._show_frame)
        self.layout().insertWidget(1, self.time_control)
        self.time_control._set_index(0)

    def _show_frame(self, index, time_value):
        self.trajectory_line.set_data_3d(*self.positions[:index + 1].T)
        self.current_point.set_data_3d(*self.positions[index:index + 1].T)
        unit = self.product.axes[0].unit
        frame = self.product.coordinate_frame.upper()
        self.plot.set_title(
            f"{self.product.name}{f' ({frame})' if frame else ''}"
            f" — {time_value:g}{f' {unit}' if unit else ''}"
        )
        self.canvas.draw_idle()


class GridSeriesWidget(FigureWidget):
    def __init__(self, product):
        super().__init__()
        self.product = product
        time_axis, x_axis, y_axis = product.axes
        self.plot = self.figure.add_subplot()
        self.enable_navigation(self.plot)
        limits = product.display_range or (None, None)
        self.mesh = self.plot.pcolormesh(
            _cell_edges(x_axis.values),
            _cell_edges(y_axis.values),
            np.ma.masked_invalid(product.values[0]),
            shading="flat",
            cmap="turbo",
            vmin=limits[0],
            vmax=limits[1],
        )
        self.plot.set_xlabel(_label(x_axis.name, x_axis.unit))
        self.plot.set_ylabel(_label(y_axis.name, y_axis.unit))
        colorbar = self.figure.colorbar(self.mesh, ax=self.plot)
        if product.value_unit:
            colorbar.set_label(product.value_unit)
        self.time_control = TimeControl(time_axis, self._show_frame)
        self.layout().insertWidget(1, self.time_control)
        self.time_control._set_index(0)

    def _show_frame(self, index, time_value):
        self.mesh.set_array(
            np.ma.masked_invalid(self.product.values[index]).ravel()
        )
        unit = self.product.axes[0].unit
        self.plot.set_title(
            f"{self.product.name} — {time_value:g}{f' {unit}' if unit else ''}"
        )
        self.canvas.draw_idle()


class MetricTableWidget(QWidget):
    def __init__(self, product):
        super().__init__()
        self.product = product
        layout = QVBoxLayout(self)
        title = QLabel(product.name)
        title.setObjectName("analysisTitle")
        layout.addWidget(title)

        time_axis = product.axes[0]
        if len(time_axis.values):
            self.time_control = TimeControl(time_axis, self._show_values)
            layout.addWidget(self.time_control)

        self.table = QTableWidget(len(product.metrics), 3)
        self.table.setHorizontalHeaderLabels(["State", "Value", "Unit"])
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for column in (1, 2):
            self.table.horizontalHeader().setSectionResizeMode(
                column, QHeaderView.ResizeMode.ResizeToContents
            )
        for row, metric in enumerate(product.metrics):
            self.table.setItem(row, 0, QTableWidgetItem(metric.name))
            self.table.setItem(row, 2, QTableWidgetItem(metric.unit or "—"))
        layout.addWidget(self.table, 1)
        self._show_values(0, 0.0)
        if len(time_axis.values):
            self.time_control._set_index(0)

    def _show_values(self, index, _time_value):
        for row, metric in enumerate(self.product.metrics):
            if len(metric.values):
                value = metric.values[0 if len(metric.values) == 1 else index]
                if value is None:
                    text = "—"
                elif isinstance(value, str):
                    text = value
                else:
                    text = f"{value:,.6g}" if np.isfinite(value) else "—"
            else:
                text = "—"
            cell = QTableWidgetItem(text)
            cell.setTextAlignment(
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
            )
            self.table.setItem(row, 1, cell)


class ArraySeriesWidget(FigureWidget):
    """Inspect raw array snapshots even when dimensions change between samples."""

    COMPONENTS = {"Real": np.real, "Imaginary": np.imag, "Magnitude": np.abs}
    X_LABEL = "Column index"
    Y_LABEL = "Row index"
    DEFAULT_COMPONENT = "Real"

    def __init__(self, product):
        super().__init__()
        self.product = product
        self.plot = self.figure.add_subplot()
        self.colorbar = None
        self.component = QComboBox()
        self.component.addItems(self.COMPONENTS)
        self.component.setCurrentText(self.DEFAULT_COMPONENT)
        self.layout().insertWidget(1, self.component)
        self.time_control = TimeControl(product.axes[0], self._show_frame)
        self.layout().insertWidget(1, self.time_control)
        self.component.currentTextChanged.connect(self._change_component)
        self.time_control._set_index(0)

    def _change_component(self, _component):
        self.time_control._set_index(self.time_control.slider.value())

    def _extent(self, sample):
        return None

    def _show_frame(self, index, time_value):
        previous_extent = tuple(self.plot.images[0].get_extent()) if self.plot.images else None
        previous_limits = self.plot.get_xlim(), self.plot.get_ylim()
        if self.colorbar is not None:
            self.colorbar.remove()
            self.colorbar = None
        self.plot.clear()
        sample = self.product.samples[index]
        if sample is None or not sample.size:
            text = "No sample" if sample is None else f"Empty array ({sample.shape[0]} × {sample.shape[1]})"
            self.plot.text(0.5, 0.5, text, ha="center", va="center", transform=self.plot.transAxes)
            self.plot.set_axis_off()
        else:
            self.plot.set_axis_on()
            values = self.COMPONENTS[self.component.currentText()](sample)
            image = self.plot.imshow(
                np.ma.masked_invalid(values), origin="lower", aspect="auto",
                interpolation="nearest", cmap="turbo", extent=self._extent(sample),
            )
            self.colorbar = self.figure.colorbar(image, ax=self.plot)
            if self.product.value_unit:
                self.colorbar.set_label(self.product.value_unit)
            self.plot.set_xlabel(self.X_LABEL)
            self.plot.set_ylabel(self.Y_LABEL)
            if previous_extent == tuple(image.get_extent()):
                self.plot.set_xlim(*previous_limits[0])
                self.plot.set_ylim(*previous_limits[1])
        self.enable_navigation(self.plot)
        unit = self.product.axes[0].unit
        self.plot.set_title(
            f"{self.product.name} — {time_value:g}{f' {unit}' if unit else ''}"
            f" ({self.component.currentText()})"
        )
        self.canvas.draw_idle()


class RangePulseMapWidget(ArraySeriesWidget):
    """Browse each radar's recorded range rows and pulse columns in time."""

    X_LABEL = "Pulse index"
    Y_LABEL = "Range sample index"
    DEFAULT_COMPONENT = "Magnitude"


class RangeDopplerMapWidget(ArraySeriesWidget):
    """Display FFT-shifted columns by signed bin; rows remain range samples."""

    X_LABEL = "Shifted Doppler bin"
    Y_LABEL = "Range sample index"
    DEFAULT_COMPONENT = "Magnitude"

    def _extent(self, sample):
        rows, columns = sample.shape
        first_bin = -(columns // 2)
        return first_bin - 0.5, first_bin + columns - 0.5, -0.5, rows - 0.5


class RangeVelocityMapWidget(ArraySeriesWidget):
    """Display the recorded FFT-shifted map on physical range/velocity axes."""

    DEFAULT_COMPONENT = "Magnitude"

    def _extent(self, sample):
        x_axis, y_axis = self.product.sample_axes[self._frame_index]
        x_edges, y_edges = _cell_edges(x_axis.values), _cell_edges(y_axis.values)
        if len(x_axis.values) == 1:
            x_edges = self.product.sample_x_limits[self._frame_index]
        return x_edges[0], x_edges[-1], y_edges[0], y_edges[-1]

    def _show_frame(self, index, time_value):
        previous_bounds = getattr(self, "_velocity_bounds", None)
        previous_extent = tuple(self.plot.images[0].get_extent()) if self.plot.images else None
        self._frame_index = index
        axes = self.product.sample_axes[index]
        if axes is not None:
            x_axis, y_axis = axes
            self.X_LABEL = _label(x_axis.name, x_axis.unit)
            self.Y_LABEL = _label(y_axis.name, y_axis.unit)
        super()._show_frame(index, time_value)
        limits = self.product.sample_x_limits[index]
        extent = tuple(self.plot.images[0].get_extent()) if self.plot.images else None
        if limits is not None and (limits != previous_bounds or extent != previous_extent):
            self.plot.set_xlim(*limits)
        self._velocity_bounds = limits


RENDERERS = {
    CURVE: render_curve,
    TRAJECTORY_3D: Trajectory3DWidget,
    GRID_SERIES: GridSeriesWidget,
    METRIC_TABLE: MetricTableWidget,
    ARRAY_SERIES: ArraySeriesWidget,
    RANGE_PULSE_MAP: RangePulseMapWidget,
    RANGE_DOPPLER_MAP: RangeDopplerMapWidget,
    RANGE_VELOCITY_MAP: RangeVelocityMapWidget,
}
