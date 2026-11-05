"""Physical trajectory and range-velocity views of logged simulation data."""

import os
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace as Data

import numpy as np
import pytest

from analysis.catalog import (
    CURVE,
    RANGE_VELOCITY_MAP,
    TRAJECTORY_3D,
    build_analysis_catalog,
)


def _history(entity_id, system, key, values, *, unit="", frame=""):
    return Data(
        entity_id=entity_id, system=system, key=key, name=key,
        axis_key="simulation_time", values=values, unit=unit, frame=frame,
        presentation=Data(group="", order=0),
    )


def _result():
    return Data(
        entities=[
            Data(id=index, key=f"vehicle_{index}", display_name=f"Vehicle {index}",
                 type="test", team="blue")
            for index in (1, 2)
        ],
        axes=[Data(key="simulation_time", name="Time", kind="time", unit="s",
                   values=[0.0, 2.0])],
        scalars=[], vectors=[], texts=[], arrays=[],
        curves=[], grid_series=[], metric_tables=[],
    )


def test_each_entity_xyz_history_is_one_spatial_trajectory():
    result = _result()
    for entity_id in (1, 2):
        for field, unit in (("position", "m"), ("velocity", "m/s"), ("acceleration", "m/s^2")):
            result.vectors.append(_history(
                entity_id, "kinematics", field,
                [Data(x=entity_id + step, y=10 + step, z=-20 + step)
                 for step in (0, 3)],
                unit=unit, frame="eci",
            ))

    products = build_analysis_catalog(result).products
    trajectories = [product for product in products if product.kind == TRAJECTORY_3D]
    assert [(product.entity_id, product.key) for product in trajectories] == [
        (entity_id, f"history/{field}")
        for entity_id in (1, 2) for field in ("position", "velocity", "acceleration")
    ]
    units = {"history/position": "m", "history/velocity": "m/s", "history/acceleration": "m/s^2"}
    for product in trajectories:
        assert product.coordinate_frame == "eci"
        assert product.value_unit == units[product.key]
        assert len(product.axes) == 1
        np.testing.assert_array_equal(product.axes[0].values, [0, 2])
        np.testing.assert_array_equal(product.values, [
            [product.entity_id, 10, -20], [product.entity_id + 3, 13, -17],
        ])
        assert not product.values.flags.writeable
    assert not any(product.kind == CURVE for product in products)


def _add_radar(result, name, wavelengths, pris, minimum_ranges, maximum_ranges):
    prefix = f"name:{name}"
    for field, values in (
        ("wavelength_m", wavelengths), ("pri_s", pris),
        ("mdr_m", minimum_ranges), ("mur_m", maximum_ranges),
    ):
        result.scalars.append(_history(1, "radars", f"{prefix}/params/{field}", values))
    samples = []
    for rows, columns in ((2, 4), (3, 5)):
        amplitudes = np.arange(rows * columns).reshape(rows, columns) + 1
        values = amplitudes + 1j * amplitudes[::-1]
        samples.append(Data(rows=rows, columns=columns, values=values.ravel().tolist()))
    result.arrays.append(_history(
        1, "radars", f"{prefix}/state/range_velocity_map", samples,
    ))
    return samples


def test_velocity_and_range_axes_follow_each_radars_parameters_for_each_frame():
    result = _result()
    search_samples = _add_radar(
        result, "search", [0.03, 0.06], [0.001, 0.002],
        [1500, 3000], [150000, 300000],
    )
    _add_radar(result, "track", [0.12, 0.08], [0.001, 0.001],
               [4000, 5000], [200000, 250000])
    products = {
        product.key: product for product in build_analysis_catalog(result).products
        if product.kind == RANGE_VELOCITY_MAP
    }
    assert len(products) == 2
    for name, wavelengths, pris, minimum_ranges, maximum_ranges in (
        ("search", [0.03, 0.06], [0.001, 0.002], [1500, 3000], [150000, 300000]),
        ("track", [0.12, 0.08], [0.001, 0.001], [4000, 5000], [200000, 250000]),
    ):
        product = products[f"history/name:{name}/state/range_velocity_map"]
        assert [axis.key for axis in product.axes] == ["simulation_time"]
        for index, (rows, columns) in enumerate(((2, 4), (3, 5))):
            velocity, distance = product.sample_axes[index]
            assert velocity.unit == "m/s"
            assert distance.unit == "km"
            expected_velocity = (
                (np.arange(columns) - columns // 2)
                * wavelengths[index] / (2 * columns * pris[index])
            )
            expected_distance = np.linspace(
                minimum_ranges[index], maximum_ranges[index], rows,
            ) / 1000
            np.testing.assert_allclose(velocity.values, expected_velocity)
            np.testing.assert_allclose(distance.values, expected_distance)
            assert velocity.values[columns // 2] == 0
            assert product.sample_x_limits[index] == pytest.approx((
                -wavelengths[index] / (4 * pris[index]),
                wavelengths[index] / (4 * pris[index]),
            ))
            assert not velocity.values.flags.writeable
            assert not distance.values.flags.writeable

    product = products["history/name:search/state/range_velocity_map"]
    for recorded, sample in zip(search_samples, product.samples):
        np.testing.assert_array_equal(sample.ravel(), recorded.values)
        assert sample.dtype == np.complex128
        assert not sample.flags.writeable
    search_samples[0].values[0] = 999
    assert product.samples[0][0, 0] != 999


def _run_offscreen(script):
    environment = os.environ.copy()
    environment["QT_QPA_PLATFORM"] = "offscreen"
    completed = subprocess.run(
        [sys.executable, "-c", script],
        cwd=Path(__file__).resolve().parents[1] / "src" / "python",
        env=environment, capture_output=True, text=True, timeout=60, check=False,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr


def test_offscreen_trajectory_slider_shows_progress_and_current_position():
    _run_offscreen("""
import matplotlib
matplotlib.use('agg')
import numpy as np
from PySide6.QtWidgets import QApplication
from analysis.catalog import TRAJECTORY_3D, AnalysisProduct, AxisData
from analysis.renderers import RENDERERS

app = QApplication([])
positions = np.array([[1, 5, 9], [2, 6, 10], [3, 7, 11]], dtype=float)
time = AxisData('time', 'Time', 's', 'time', np.array([0, 2, 4]))
product = AnalysisProduct(
    TRAJECTORY_3D, None, 'kinematics', 'history/position', 'Position',
    axes=(time,), values=positions, value_unit='m', coordinate_frame='eci',
)
widget = RENDERERS[TRAJECTORY_3D](product)
assert widget.plot.name == '3d'
widget.time_control.slider.setValue(1)
np.testing.assert_array_equal(
    np.array(widget.trajectory_line.get_data_3d()).T, positions[:2],
)
np.testing.assert_array_equal(
    np.array(widget.current_point.get_data_3d()).T, positions[1:2],
)
widget.time_control.slider.setValue(2)
np.testing.assert_array_equal(
    np.array(widget.trajectory_line.get_data_3d()).T, positions,
)
np.testing.assert_array_equal(
    np.array(widget.current_point.get_data_3d()).T, positions[-1:],
)
assert '4 s' in widget.plot.get_title()
assert 'X' in widget.plot.get_xlabel() and 'm' in widget.plot.get_xlabel()
assert 'Y' in widget.plot.get_ylabel() and 'm' in widget.plot.get_ylabel()
assert 'Z' in widget.plot.get_zlabel() and 'm' in widget.plot.get_zlabel()
app.processEvents()
widget.close()
""")


def test_offscreen_velocity_map_uses_signed_centers_and_per_frame_velocity_bounds():
    _run_offscreen("""
import matplotlib
matplotlib.use('agg')
import numpy as np
from PySide6.QtWidgets import QApplication
from analysis.catalog import RANGE_VELOCITY_MAP, AnalysisProduct, AxisData
from analysis.renderers import RENDERERS

app = QApplication([])
time = AxisData('time', 'Time', 's', 'time', np.array([0, 2]))
axes = tuple(
    (
        AxisData('velocity', 'Radial velocity', 'm/s', 'continuous', velocities),
        AxisData('range', 'Range', 'km', 'continuous', np.array([10., 11.])),
    )
    for velocities in (np.array([-15., -7.5, 0, 7.5]), np.array([-8., -4., 0, 4., 8.]))
)
product = AnalysisProduct(
    RANGE_VELOCITY_MAP, None, 'radars', 'map', 'Range-Velocity Map', axes=(time,),
    samples=(np.ones((2, 4), complex), 2j * np.ones((2, 5), complex)),
    sample_axes=axes, sample_x_limits=((-15., 15.), (-10., 10.)),
)
widget = RENDERERS[RANGE_VELOCITY_MAP](product)
assert 'velocity' in widget.plot.get_xlabel().lower()
assert 'm/s' in widget.plot.get_xlabel()
assert 'km' in widget.plot.get_ylabel()
np.testing.assert_allclose(widget.plot.get_xlim(), [-15., 15.])
for frame, centers in enumerate(([-15., -7.5, 0, 7.5], [-8., -4., 0, 4., 8.])):
    widget.time_control.slider.setValue(frame)
    image = widget.plot.images[0]
    left, right, bottom, top = image.get_extent()
    columns = len(centers)
    pixels = left + (np.arange(columns) + .5) * (right - left) / columns
    np.testing.assert_allclose(pixels, centers)
    np.testing.assert_allclose([bottom, top], [9.5, 11.5])
    np.testing.assert_allclose(image.get_array(), frame + 1)
np.testing.assert_allclose(widget.plot.get_xlim(), [-10., 10.])
assert '2 s' in widget.plot.get_title()
app.processEvents()
widget.close()
""")
