"""Exercise the logger's result contract without running incomplete models."""

import os
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace as Data

import numpy as np
import pytest
import rerun as rr
import rerun.blueprint as rrb

from analysis.catalog import ARRAY_SERIES, CURVE, METRIC_TABLE, build_analysis_catalog
from visualization.rerun_adapter import _log_result, _log_scenario
from visualization.rerun_blueprint import _view_from_spec
from visualization.telemetry_catalog import TEXT_SOURCE, build_telemetry_catalog


def _series(key, values, **metadata):
    return Data(
        entity_id=7, system="custom", key=key, name=key, unit="",
        axis_key="simulation_time", values=values,
        presentation=Data(group="", order=0), **metadata,
    )


def _result():
    return Data(
        entities=[Data(id=7, key="vehicle", display_name="Vehicle", type="test", team="blue")],
        axes=[Data(
            key="simulation_time", name="Time", kind="time", unit="s", values=[0, 1, 2, 3]
        )],
        scalars=[_series("unfamiliar_field", [np.nan, 4.0, 5.0, np.nan])],
        vectors=[_series(
            "direction", [Data(x=index, y=index + 1, z=index + 2) for index in range(4)],
            frame="local",
        )],
        texts=[_series("mode", [None, "survey", "", None])],
        arrays=[_series("signal", [
            None,
            Data(rows=0, columns=3, values=[]),
            Data(rows=2, columns=2, values=[1 + 2j, 3 - 4j, -5j, 6]),
            Data(rows=1, columns=3, values=[7j, 8 + 9j, 10]),
        ])],
        curves=[], grid_series=[], metric_tables=[],
    )


def test_logged_fields_automatically_become_analysis_products():
    products = build_analysis_catalog(_result()).products[1:]
    assert [(product.kind, product.key) for product in products] == [
        (CURVE, "history/unfamiliar_field"),
        (CURVE, "history/direction/x"),
        (CURVE, "history/direction/y"),
        (CURVE, "history/direction/z"),
        (METRIC_TABLE, "history/mode"),
        (ARRAY_SERIES, "history/signal"),
    ]
    assert all(product.entity_id == 7 for product in products)
    assert all(product.axes[0].values.tolist() == [0, 1, 2, 3] for product in products)
    assert np.isnan(products[0].values[[0, 3]]).all()
    assert products[2].values.tolist() == [1, 2, 3, 4]
    assert products[4].metrics[0].values.tolist() == [None, "survey", "", None]


def test_entity_description_combines_only_constant_configuration():
    result = _result()
    for key, values in (
        ("motion_type", [1, 1, 1, 1]),
        ("mass", [1, 2, 3, 4]),
    ):
        item = _series(key, values)
        item.system = "entity"
        result.scalars.append(item)
    radar = _series("name:search/params/frequency_hz", [None, 10, 10, None])
    # Numeric missing samples use NaN in the logger contract.
    radar.values = [np.nan, 10, 10, np.nan]
    radar.system = "radars"
    radar.presentation.group = "Search / Parameters"
    result.scalars.append(radar)
    flat_state = _series("target_range_m", [0, 0, 0, 0])
    flat_state.system = "radars"
    result.scalars.append(flat_state)

    products = build_analysis_catalog(result).products
    description = products[0]
    assert description.name == "Description"
    assert len(description.axes[0].values) == 0
    metrics = {metric.key: metric for metric in description.metrics}
    assert metrics["id"].values.tolist() == [7]
    assert metrics["display_name"].values.tolist() == ["Vehicle"]
    assert metrics["motion_type"].values.tolist() == ["FreeFlight"]
    assert metrics[radar.key].values.tolist() == [10]
    assert metrics[radar.key].name.startswith("Search / Parameters / ")
    keys = {product.key for product in products}
    assert "history/mass" in keys
    assert "history/target_range_m" in keys
    assert "history/motion_type" not in keys
    assert f"history/{radar.key}" not in keys
    assert result.scalars[-2].values == radar.values


def test_array_histories_preserve_complex_values_missing_empty_and_changed_dimensions():
    result = _result()
    product = next(
        item for item in build_analysis_catalog(result).products if item.kind == ARRAY_SERIES
    )
    missing, empty, square, resized = product.samples
    assert missing is None
    assert empty.shape == (0, 3)
    assert square.shape == (2, 2)
    assert resized.shape == (1, 3)
    assert square.dtype == np.complex128
    assert square.tolist() == [[1 + 2j, 3 - 4j], [-5j, 6]]
    assert resized.tolist() == [[7j, 8 + 9j, 10]]
    result.arrays[0].values[2].values[0] = 999
    assert square[0, 0] == 1 + 2j
    assert all(not sample.flags.writeable for sample in product.samples if sample is not None)


def test_each_radar_gets_its_own_range_pulse_map_view():
    from analysis.catalog import RANGE_PULSE_MAP

    result = _result()
    original = result.arrays[0]
    result.arrays = []
    for radar in ("search", "track"):
        item = _series(f"name:{radar}/state/range_pulse_map", original.values)
        item.system = "radars"
        item.presentation.group = f"Radars / {radar} / State"
        result.arrays.append(item)
    products = [
        product for product in build_analysis_catalog(result).products
        if product.kind == RANGE_PULSE_MAP
    ]
    assert len(products) == 2
    assert products[0].identity != products[1].identity
    assert all(product.name == "Range–Pulse Map" for product in products)
    assert all(len(product.samples) == 4 for product in products)


def test_logged_history_validation_keeps_timesteps_and_dimensions_consistent():
    result = _result()
    result.texts[0].values.pop()
    with pytest.raises(ValueError, match="does not match simulation_time"):
        build_analysis_catalog(result)
    result = _result()
    result.arrays[0].values[2].columns = 3
    with pytest.raises(ValueError, match="dimensions do not match"):
        build_analysis_catalog(result)


def test_telemetry_keeps_component_paths_distinct_and_includes_text():
    result = _result()
    result.scalars = [
        _series(f"sensors/{index}/value", [1, 2, 3, 4]) for index in range(2)
    ]
    views = build_telemetry_catalog(result).views
    paths = [view.path for view in views]
    assert len(paths) == len(set(paths)) == 4
    assert "/telemetry/entities/vehicle/custom/sensors/0/value" in paths
    assert "/telemetry/entities/vehicle/custom/sensors/1/value" in paths
    text = next(view for view in views if view.source_type == TEXT_SOURCE)
    assert text.values.tolist() == [None, "survey", "", None]
    assert not text.values.flags.writeable
    assert isinstance(_view_from_spec(text), rrb.TextLogView)


def test_rerun_records_text_timestamps_and_clears_missing_fields_without_reading_arrays():
    class NoAnalysisAccess:
        def __getattr__(self, name):
            if name in {"curves", "grid_series", "metric_tables", "arrays"}:
                raise AssertionError(f"Rerun accessed analysis data {name}")
            return getattr(result, name)

    class RecordingSpy:
        def __init__(self):
            self.logs = []
            self.times = []
            self.disabled = []

        def log(self, path, *archetypes, **kwargs):
            self.logs.extend((path, item) for item in archetypes)

        def send_columns(self, path, **kwargs):
            pass

        def set_time(self, timeline, **kwargs):
            self.times.append((timeline, kwargs))

        def disable_timeline(self, timeline):
            self.disabled.append(timeline)

        def send_blueprint(self, blueprint):
            pass

        def flush(self):
            pass

    result = _result()
    recording = RecordingSpy()
    _log_result(NoAnalysisAccess(), recording)
    path = "/telemetry/entities/vehicle/custom/mode"
    assert [type(item).__name__ for item_path, item in recording.logs if item_path == path] == [
        "Clear", "TextLog", "TextLog", "Clear",
    ]
    assert recording.times == [
        ("simulation_time", {"duration": float(index)}) for index in range(4)
    ]
    assert recording.disabled == ["simulation_time"]


def test_rerun_accepts_logged_data_in_memory():
    result = _result()
    result.scalars.extend([
        _series("name:search/params/frequency_hz", [1e9] * 4),
        _series("name:a%2Fb%2E%25%3A/params/frequency_hz", [2e9] * 4),
    ])
    for series in result.scalars[1:]:
        series.system = "radars"
    recording = rr.RecordingStream("apogee-logged-data-tests")
    memory = recording.memory_recording()
    try:
        _log_result(result, recording)
        assert memory.num_msgs() > 0
        assert memory.drain_as_bytes()
    finally:
        recording.disconnect()


def test_scene_disappearances_clear_geometry_and_do_not_bridge_trajectory_gaps():
    class RecordingSpy:
        def __init__(self):
            self.logs = {}
            self.columns = {}

        def log(self, path, archetype, **kwargs):
            self.logs[path] = archetype

        def send_columns(self, path, **kwargs):
            self.columns[path] = kwargs["columns"]

    def vector(x):
        return Data(x=x, y=0.0, z=0.0)

    result = _result()
    result.axes[0].values = list(range(7))
    result.axes.append(Data(
        key="arrow_time", name="Arrow Time", kind="time", unit="s",
        values=np.arange(0, 6.5, 0.5),
    ))
    position = _series("position", [
        vector(x) for x in [np.nan, 1000, 2000, np.nan, 9000, 10000, np.nan]
    ], frame="eci")
    velocity = _series("velocity", [vector(100)] * 13, frame="eci")
    velocity.axis_key = "arrow_time"
    acceleration = _series("acceleration", [
        vector(x) for x in [10, 10, np.nan, 10, 10, 10, 10]
    ], frame="eci")
    result.vectors = [position, velocity, acceleration]
    for series in result.vectors:
        series.system = "kinematics"
    result.scalars, result.texts, result.arrays = [], [], []
    recording = RecordingSpy()
    _log_scenario(recording, build_telemetry_catalog(result))

    def components(columns):
        return {
            item.component_descriptor().component: item.as_arrow_array().to_pylist()
            for item in columns
        }

    points = components(recording.columns["/world/entities/vehicle"])["Points3D:positions"]
    assert points == [[], [[1, 0, 0]], [[2, 0, 0]], [], [[9, 0, 0]], [[10, 0, 0]], []]
    arrows = components(recording.columns["/world/vectors/vehicle/velocity"])
    assert [len(row) for row in arrows["Arrows3D:origins"]] == [
        0, 0, 1, 1, 1, 0, 0, 0, 1, 1, 1, 0, 0,
    ]
    assert arrows["Arrows3D:origins"][3] == [[1.5, 0, 0]]
    np.testing.assert_allclose(arrows["Arrows3D:vectors"][3], [[0.1, 0, 0]])
    acceleration = components(recording.columns["/world/vectors/vehicle/acceleration"])
    assert [len(row) for row in acceleration["Arrows3D:vectors"]] == [0, 1, 0, 0, 1, 1, 0]
    np.testing.assert_allclose(acceleration["Arrows3D:vectors"][1], [[0.1, 0, 0]])
    strips = components(
        recording.logs["/world/trajectories/vehicle"].as_component_batches()
    )["LineStrips3D:strips"]
    assert strips == [[[1, 0, 0], [2, 0, 0]], [[9, 0, 0], [10, 0, 0]]]


def test_offscreen_array_inspector_handles_missing_empty_and_resized_samples():
    script = """
import matplotlib
matplotlib.use('agg')
import numpy as np
from PySide6.QtWidgets import QApplication
from analysis.catalog import ARRAY_SERIES, METRIC_TABLE, AnalysisProduct, AxisData, MetricData
from analysis.renderers import ArraySeriesWidget, MetricTableWidget, RangePulseMapWidget

app = QApplication([])
axis = AxisData('time', 'Time', 's', 'time', np.arange(4.0))
product = AnalysisProduct(
    ARRAY_SERIES, None, 'custom', 'signal', 'Signal', axes=(axis,),
    samples=(None, np.empty((0, 3), complex), np.array([[1 + 2j, 3 - 4j]]), np.ones((2, 1))),
)
widget = ArraySeriesWidget(product)
widget.show()
assert widget.plot.texts[0].get_text() == 'No sample'
widget.time_control.slider.setValue(1)
assert 'Empty array' in widget.plot.texts[0].get_text()
widget.time_control.slider.setValue(2)
np.testing.assert_allclose(widget.plot.images[0].get_array(), [[1, 3]])
widget.component.setCurrentText('Imaginary')
np.testing.assert_allclose(widget.plot.images[0].get_array(), [[2, -4]])
widget.component.setCurrentText('Magnitude')
np.testing.assert_allclose(widget.plot.images[0].get_array(), [[np.sqrt(5), 5]])
widget.time_control.slider.setValue(3)
assert widget.plot.images[0].get_array().shape == (2, 1)
widget.time_control.slider.setValue(0)
assert widget.plot.texts[0].get_text() == 'No sample'
assert len(widget.figure.axes) == 1
radar = RangePulseMapWidget(product)
assert radar.component.currentText() == 'Magnitude'
radar.time_control.slider.setValue(2)
np.testing.assert_allclose(radar.plot.images[0].get_array(), [[np.sqrt(5), 5]])
assert radar.plot.get_xlabel() == 'Pulse index'
assert radar.plot.get_ylabel() == 'Range sample index'
radar.time_control.slider.setValue(3)
assert radar.plot.images[0].get_array().shape == (2, 1)
assert '3 s' in radar.plot.get_title()
radar.close()
text_product = AnalysisProduct(
    METRIC_TABLE, None, 'custom', 'mode', 'Mode', axes=(axis,),
    metrics=(MetricData('mode', 'Mode', '', np.array([None, 'survey', '', None], object)),),
)
table = MetricTableWidget(text_product)
assert table.table.item(0, 1).text() == '—'
table.time_control.slider.setValue(1)
assert table.table.item(0, 1).text() == 'survey'
table.time_control.slider.setValue(2)
assert table.table.item(0, 1).text() == ''
app.processEvents()
table.close()
widget.close()
"""
    environment = os.environ.copy()
    environment["QT_QPA_PLATFORM"] = "offscreen"
    completed = subprocess.run(
        [sys.executable, "-c", script],
        cwd=Path(__file__).resolve().parents[1] / "src" / "python",
        env=environment, capture_output=True, text=True, timeout=60, check=False,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
