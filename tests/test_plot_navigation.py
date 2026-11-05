"""Exercise plot navigation through Qt mouse events."""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import numpy as np
import pytest
from PySide6.QtCore import QEvent, QPoint, QPointF, Qt
from PySide6.QtGui import QMouseEvent, QWheelEvent
from PySide6.QtWidgets import QApplication

from analysis.catalog import AnalysisProduct, AxisData, ARRAY_SERIES, CURVE, TRAJECTORY_3D, RANGE_VELOCITY_MAP
from analysis.renderers import ArraySeriesWidget, RangeVelocityMapWidget, Trajectory3DWidget, render_curve


@pytest.fixture
def app():
    return QApplication.instance() or QApplication([])


def show(widget, app):
    widget.resize(1000, 700)
    widget.show()
    app.processEvents()
    widget.canvas.draw()
    box = widget.plot.bbox
    return QPointF((box.x0 + box.x1) / 2,
                   widget.canvas.height() - (box.y0 + box.y1) / 2)


def drag(widget, app, start, button=Qt.MouseButton.LeftButton):
    end = start + QPointF(60, 35)
    for kind, point, changed, held in (
        (QEvent.Type.MouseButtonPress, start, button, button),
        (QEvent.Type.MouseMove, end, Qt.MouseButton.NoButton, button),
        (QEvent.Type.MouseButtonRelease, end, button, Qt.MouseButton.NoButton),
    ):
        app.sendEvent(widget.canvas, QMouseEvent(
            kind, point, point, changed, held, Qt.KeyboardModifier.NoModifier,
        ))
    app.processEvents()


def wheel(widget, app, point):
    app.sendEvent(widget.canvas, QWheelEvent(
        point, point, QPoint(), QPoint(0, 120), Qt.MouseButton.NoButton,
        Qt.KeyboardModifier.NoModifier, Qt.ScrollPhase.ScrollUpdate, False,
    ))
    app.processEvents()


def test_3d_drag_rotates_and_wheel_zooms_without_time_reset(app):
    axis = AxisData("time", "Time", "s", "time", np.arange(3.0))
    widget = Trajectory3DWidget(AnalysisProduct(
        TRAJECTORY_3D, None, "kinematics", "position", "Position",
        axes=(axis,), values=np.array([[0, 0, 0], [1, 2, 3], [2, 4, 6]]),
    ))
    try:
        point = show(widget, app)
        angles = widget.plot.elev, widget.plot.azim
        drag(widget, app, point)
        assert not np.allclose((widget.plot.elev, widget.plot.azim), angles)
        limits = np.array([widget.plot.get_xlim(), widget.plot.get_ylim(), widget.plot.get_zlim()])
        wheel(widget, app, point)
        zoomed = np.array([widget.plot.get_xlim(), widget.plot.get_ylim(), widget.plot.get_zlim()])
        assert np.all(np.diff(zoomed, axis=1) < np.diff(limits, axis=1))
        rotated = widget.plot.elev, widget.plot.azim
        widget.time_control.slider.setValue(2)
        np.testing.assert_allclose((widget.plot.elev, widget.plot.azim), rotated)
        np.testing.assert_allclose(widget.plot.get_xlim(), zoomed[0])
    finally:
        widget.close()


def test_curve_default_drag_pans_and_wheel_zooms(app):
    axis = AxisData("time", "Time", "s", "time", np.arange(3.0))
    widget = render_curve(AnalysisProduct(
        CURVE, None, "kinematics", "speed", "Speed", axes=(axis,), values=np.array([1, 3, 2]),
    ))
    widget.plot = widget.figure.axes[0]
    try:
        point = show(widget, app)
        original = widget.plot.get_xlim()
        drag(widget, app, point)
        assert not np.allclose(widget.plot.get_xlim(), original)
        span = np.ptp(widget.plot.get_xlim())
        wheel(widget, app, point)
        assert np.ptp(widget.plot.get_xlim()) < span
        span = np.ptp(widget.plot.get_xlim())
        widget.toolbar.zoom()
        drag(widget, app, point)
        assert np.ptp(widget.plot.get_xlim()) < span
        widget.toolbar.home()
        np.testing.assert_allclose(widget.plot.get_xlim(), original)
    finally:
        widget.close()


def test_velocity_map_keeps_zoom_across_frames_and_resets_for_new_axes(app):
    axis = AxisData("time", "Time", "s", "time", np.arange(3.0))
    velocity = AxisData("velocity", "Velocity", "m/s", "continuous", np.arange(-6, 6))
    distance = AxisData("range", "Range", "km", "continuous", np.arange(10.0))
    farther = AxisData("range", "Range", "km", "continuous", np.arange(10.0) + 100)
    widget = RangeVelocityMapWidget(AnalysisProduct(
        RANGE_VELOCITY_MAP, None, "radars", "rv", "RV", axes=(axis,),
        samples=tuple(np.ones((10, 12), complex) for _ in range(3)),
        sample_axes=((velocity, distance), (velocity, distance), (velocity, farther)),
        sample_x_limits=((-6, 6),) * 3,
    ))
    try:
        point = show(widget, app)
        wheel(widget, app, point)
        zoomed = widget.plot.get_xlim()
        assert np.ptp(zoomed) < 12
        widget.time_control.slider.setValue(1)
        np.testing.assert_allclose(widget.plot.get_xlim(), zoomed)
        widget.component.setCurrentText("Magnitude")
        np.testing.assert_allclose(widget.plot.get_xlim(), zoomed)
        widget.time_control.slider.setValue(2)
        np.testing.assert_allclose(widget.plot.get_xlim(), [-6, 6])
    finally:
        widget.close()


def test_map_preserves_navigation_when_time_or_component_changes(app):
    axis = AxisData("time", "Time", "s", "time", np.arange(2.0))
    widget = ArraySeriesWidget(AnalysisProduct(
        ARRAY_SERIES, None, "custom", "map", "Map", axes=(axis,),
        samples=(np.ones((10, 12), complex), 2j * np.ones((10, 12), complex)),
    ))
    try:
        point = show(widget, app)
        wheel(widget, app, point)
        zoomed = widget.plot.get_xlim(), widget.plot.get_ylim()
        assert np.ptp(zoomed[0]) < 12
        widget.time_control.slider.setValue(1)
        np.testing.assert_allclose(widget.plot.get_xlim(), zoomed[0])
        np.testing.assert_allclose(widget.plot.get_ylim(), zoomed[1])
        widget.component.setCurrentText("Imaginary")
        np.testing.assert_allclose(widget.plot.get_xlim(), zoomed[0])
        np.testing.assert_allclose(widget.plot.get_ylim(), zoomed[1])
    finally:
        widget.close()
