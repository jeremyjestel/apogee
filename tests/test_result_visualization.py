import numpy as np
import pytest
import rerun as rr

import apogee
from parameter_window import create_params_from_text, default_parameter_values
from visualization import log_result, save_result
from visualization.chart_renderer import render_xy_chart


@pytest.fixture(scope="module")
def simulation_result():
    return apogee.run_sim(apogee.Params())


@pytest.fixture
def memory_recording():
    recording = rr.RecordingStream("apogee-tests")
    memory = recording.memory_recording()
    yield recording, memory
    recording.disconnect()


def _axis(key, values, *, kind="continuous", name="Axis", unit=""):
    axis = apogee.Axis()
    axis.key = key
    axis.name = name
    axis.unit = unit
    axis.kind = kind
    axis.values = values
    return axis


def _grid():
    grid = apogee.Grid2D()
    grid.entity_id = 0
    grid.system = "radar"
    grid.key = "range_doppler"
    grid.name = "Range-Doppler Map"
    grid.x_axis = _axis(
        "range_m",
        [1000.0, 2000.0, 3000.0],
        name="Range",
        unit="m",
    )
    grid.y_axis = _axis(
        "doppler_hz",
        [-100.0, 100.0],
        name="Doppler",
        unit="Hz",
    )
    grid.value_unit = "dB"
    grid.rows = 2
    grid.columns = 3
    grid.values = [-90.0, -80.0, -70.0, -60.0, -50.0, -40.0]
    grid.has_display_range = True
    grid.display_min = -100.0
    grid.display_max = 0.0
    return grid


def _vector(x, y, z):
    value = apogee.Vec3()
    value.x = x
    value.y = y
    value.z = z
    return value


def _parameter_leaves(value, prefix=""):
    leaves = {}
    for name, descriptor in vars(type(value)).items():
        if not isinstance(descriptor, property):
            continue

        child = getattr(value, name)
        path = f"{prefix}.{name}" if prefix else name
        if isinstance(child, (str, int, float, bool)):
            leaves[path] = child
        else:
            leaves.update(_parameter_leaves(child, path))
    return leaves


def test_continuous_analysis_chart_renders():
    image = render_xy_chart(
        [10.0, 1000.0, 5000.0, 10000.0],
        [90.0, 45.0, 20.0, -15.0],
        x_name="Range",
        x_unit="m",
        y_name="SNR",
        y_unit="dB",
        color=[40, 110, 255],
    )

    assert image.ndim == 3
    assert image.shape[2] == 3
    assert image.dtype == np.uint8
    assert image.std() > 10.0


def test_parameter_metadata_covers_every_cpp_parameter():
    specs = apogee.parameter_specs()
    paths = [spec.path for spec in specs]
    bound_parameters = _parameter_leaves(apogee.Params())

    assert len(paths) == len(set(paths))
    assert set(paths) == set(bound_parameters)
    assert all(spec.group and spec.name for spec in specs)
    assert {
        "blue_radar.target_range_m",
        "blue_radar.target_velocity_mps",
        "blue_radar.target_RCS_dbsm",
    } <= set(paths)


def test_parameter_window_defaults_match_cpp_defaults():
    bound_parameters = _parameter_leaves(apogee.Params())
    displayed_values = default_parameter_values()

    assert apogee.Params().red_missile.mass_kg == pytest.approx(1000.0)
    assert displayed_values.keys() == bound_parameters.keys()
    for path, expected in bound_parameters.items():
        if isinstance(expected, str):
            assert displayed_values[path] == expected
        else:
            assert float(displayed_values[path]) == pytest.approx(expected)


def test_every_parameter_round_trips_from_text():
    original = _parameter_leaves(apogee.Params())
    values = default_parameter_values()
    expected = {}

    for path, current in original.items():
        replacement = (
            f"{current}_edited"
            if isinstance(current, str)
            else current + 0.125
        )
        values[path] = str(replacement)
        expected[path] = replacement

    edited = _parameter_leaves(create_params_from_text(values))

    assert edited.keys() == expected.keys()
    for path, expected_value in expected.items():
        if isinstance(expected_value, str):
            assert edited[path] == expected_value
        else:
            assert edited[path] == pytest.approx(expected_value)


def test_parameter_text_runs_end_to_end():
    values = default_parameter_values()
    values["simulation.dt_s"] = "0.25"
    values["simulation.duration_s"] = "0.5"
    values["blue_radar.initial_kinematics.pos_m.x"] = "7000000"
    values["blue_radar.target_velocity_mps"] = "-321"
    values["simulation.coordinate_frame"] = "test_frame"

    params = create_params_from_text(values)
    result = apogee.run_sim(params)

    assert params.simulation.dt_s == pytest.approx(0.25)
    assert params.blue_radar.initial_kinematics.pos_m.x == pytest.approx(7000000.0)
    assert params.blue_radar.target_velocity_mps == pytest.approx(-321.0)

    time = next(axis for axis in result.axes if axis.key == "simulation_time")
    radar = next(entity for entity in result.entities if entity.key == "blue_radar_1")
    position = next(
        series for series in result.vectors
        if series.entity_id == radar.id and series.key == "position"
    )
    assert time.values == pytest.approx([0.0, 0.25])
    assert position.frame == "test_frame"
    assert position.values[0].x == pytest.approx(7000000.0)


def test_simulation_result_contains_the_expected_data(simulation_result):
    result = simulation_result
    expected_entity_keys = {
        "blue_radar_1",
        "blue_satellite_1",
        "red_missile_1",
        "blue_interceptor_1",
    }

    assert {entity.key for entity in result.entities} == expected_entity_keys
    axes = {axis.key: axis for axis in result.axes}
    simulation_time = axes["simulation_time"].values
    snr_series = next(series for series in result.scalars if series.key == "snr")

    assert len(simulation_time) > 1
    assert len(snr_series.values) == len(axes[snr_series.axis_key].values)

    for entity in result.entities:
        vectors = [
            series for series in result.vectors
            if series.entity_id == entity.id and series.system == "kinematics"
        ]
        speeds = [
            series for series in result.scalars
            if series.entity_id == entity.id and series.key == "speed"
        ]
        assert [series.key for series in vectors] == [
            "position",
            "velocity",
            "acceleration",
        ]
        assert len(speeds) == 1
        assert all(len(series.values) == len(simulation_time) for series in vectors)
        assert len(speeds[0].values) == len(simulation_time)


def test_real_result_logs_to_memory(
    simulation_result,
    memory_recording,
):
    recording, memory = memory_recording

    blueprint = log_result(simulation_result, recording)

    assert blueprint is not None
    assert memory.num_msgs() > 0
    assert len(memory.drain_as_bytes()) > 0


def test_real_result_saves_to_rrd(simulation_result, tmp_path):
    output = tmp_path / "simulation.rrd"

    saved_path = save_result(simulation_result, output)

    assert saved_path == output.resolve()
    assert output.stat().st_size > 0


def test_grid_and_3d_analysis_log_to_memory(memory_recording):
    result = apogee.Result()
    result.axes = [
        _axis(
            "look_angle_rad",
            [0.0, 0.5, 1.0],
            name="Look Angle",
            unit="rad",
        )
    ]

    series = apogee.VectorSeries3()
    series.entity_id = 0
    series.system = "radar"
    series.key = "response_3d"
    series.name = "3D Response"
    series.unit = "dB"
    series.frame = "analysis_space"
    series.axis_key = "look_angle_rad"
    series.values = [
        _vector(0.0, 0.0, -20.0),
        _vector(0.5, 0.25, -10.0),
        _vector(1.0, 1.0, -5.0),
    ]
    result.vectors = [series]
    result.grids = [_grid()]

    recording, memory = memory_recording
    blueprint = log_result(result, recording)

    assert blueprint is not None
    assert memory.num_msgs() > 0
    assert len(memory.drain_as_bytes()) > 0
