"""Qt/Matplotlib renderers for the three supported analysis shapes."""

import matplotlib

matplotlib.use("qtagg")

import numpy as np
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg, NavigationToolbar2QT
from matplotlib.figure import Figure
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
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

from .catalog import CURVE, GRID_SERIES, METRIC_TABLE, AnalysisProduct


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
        self.toolbar = NavigationToolbar2QT(self.canvas, self)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.toolbar)
        layout.addWidget(self.canvas, 1)


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
    widget.canvas.draw()
    return widget


class GridSeriesWidget(FigureWidget):
    def __init__(self, product):
        super().__init__()
        self.product = product
        time_axis, x_axis, y_axis = product.axes
        self.plot = self.figure.add_subplot()
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
                text = f"{value:,.6g}"
            else:
                text = "—"
            cell = QTableWidgetItem(text)
            cell.setTextAlignment(
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
            )
            self.table.setItem(row, 1, cell)


RENDERERS = {
    CURVE: render_curve,
    GRID_SERIES: GridSeriesWidget,
    METRIC_TABLE: MetricTableWidget,
}
