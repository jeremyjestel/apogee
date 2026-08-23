import numpy as np
import pytest
import rerun as rr

import apogee
from parameter_window import create_params_from_text, default_parameter_values
from visualization import save_result
from visualization.chart_renderer import render_xy_chart
from visualization.rerun_adapter import _log_result


def _parameter_leaves(value, prefix=""):
    leaves = {}
    for name, descriptor in vars(type(value)).items():
        if not isinstance(descriptor, property):
            continue

        child = getattr(value, name)
        path = f"{prefix}.{name}" if prefix else name
        if isinstance(child, (int, float)):
            leaves[path] = child
        else:
            leaves.update(_parameter_leaves(child, path))
    return leaves


def _axis(key, values, *, name="Axis", unit=""):
    axis = apogee.Axis()
    axis.key = key
    axis.name = name
    axis.unit = unit
    axis.kind = "continuous"
    axis.values = values
    return axis


def _vector(x, y, z):
    value = apogee.Vec3()
    value.x = x
    value.y = y
    value.z = z
    return value


def test_parameter_schema_defaults_and_text_round_trip():
    specs = apogee.parameter_specs()
    paths = [spec.path for spec in specs]
    defaults = _parameter_leaves(apogee.Params())
    displayed = default_parameter_values()

    assert len(paths) == len(set(paths))
    assert set(paths) == set(defaults)
    assert displayed.keys() == defaults.keys()
    assert all(spec.group and spec.name for spec in specs)
    assert {
        "blue_radar.radar.frequency_hz",
        "blue_radar.max_range_m",
        "red_missile.radar_cross_section_dbsm",
    } <= set(paths)

    edited_text = {
        path: str(value + 0.125)
        for path, value in defaults.items()
    }
    edited = _parameter_leaves(create_params_from_text(edited_text))

    for path, original in defaults.items():
        assert float(displayed[path]) == pytest.approx(original)
        assert edited[path] == pytest.approx(original + 0.125)


def test_edited_run_contains_the_fixed_four_entities():
    values = default_parameter_values()
    values["simulation.dt_s"] = "0.25"
    values["simulation.duration_s"] = "0.5"
    values["blue_radar.initial_kinematics.pos_m.x"] = "7000000"

    params = create_params_from_text(values)
    result = apogee.run_sim(params)

    expected_keys = {
        "blue_radar",
        "blue_satellite",
        "red_missile",
        "blue_interceptor",
    }
    assert len(result.entities) == 4
    assert {entity.key for entity in result.entities} == expected_keys

    axes = {axis.key: axis for axis in result.axes}
    simulation_time = axes["simulation_time"].values
    assert simulation_time == pytest.approx([0.0, 0.25])

    radar = next(entity for entity in result.entities if entity.key == "blue_radar")
    radar_position = next(
        series
        for series in result.vectors
        if series.entity_id == radar.id and series.key == "position"
    )
    assert radar_position.values[0].x == pytest.approx(7000000.0)

    for entity in result.entities:
        vectors = [
            series
            for series in result.vectors
            if series.entity_id == entity.id and series.system == "kinematics"
        ]
        speeds = [
            series
            for series in result.scalars
            if series.entity_id == entity.id and series.key == "speed"
        ]

        assert [series.key for series in vectors] == [
            "position",
            "velocity",
            "acceleration",
        ]
        assert all(series.frame == "eci" for series in vectors)
        assert all(len(series.values) == len(simulation_time) for series in vectors)
        assert len(speeds) == 1
        assert len(speeds[0].values) == len(simulation_time)


def test_radar_analysis_uses_radar_and_missile_parameters():
    params = apogee.Params()
    params.simulation.duration_s = 0.0
    params.blue_radar.max_range_m = 30.0
    params.blue_radar.range_step_m = 10.0

    baseline = apogee.run_sim(params)
    range_axis = next(axis for axis in baseline.axes if axis.key == "radar_range_km")
    baseline_snr = next(
        series.values for series in baseline.scalars if series.key == "snr"
    )

    params.blue_radar.radar.power_dbw += 10.0
    powered = apogee.run_sim(params)
    powered_snr = next(
        series.values for series in powered.scalars if series.key == "snr"
    )

    params.red_missile.radar_cross_section_dbsm += 10.0
    larger_target = apogee.run_sim(params)
    larger_target_snr = next(
        series.values for series in larger_target.scalars if series.key == "snr"
    )

    params.blue_radar.radar.frequency_hz *= 2.0
    higher_frequency = apogee.run_sim(params)
    higher_frequency_snr = next(
        series.values for series in higher_frequency.scalars if series.key == "snr"
    )

    assert range_axis.values == pytest.approx([0.01, 0.02, 0.03])
    assert baseline_snr[0] == pytest.approx(129.5353053321)
    assert np.subtract(powered_snr, baseline_snr) == pytest.approx([10.0] * 3)
    assert np.subtract(larger_target_snr, powered_snr) == pytest.approx([10.0] * 3)
    assert np.subtract(higher_frequency_snr, larger_target_snr) == pytest.approx(
        [-6.0205999133] * 3
    )


@pytest.mark.parametrize(
    ("dt_s", "duration_s"),
    [
        (0.0, 0.0),
        (-0.1, 0.0),
        (float("nan"), 0.0),
        (0.1, -1.0),
        (0.1, float("inf")),
    ],
)
def test_invalid_simulation_time_is_rejected(dt_s, duration_s):
    params = apogee.Params()
    params.simulation.dt_s = dt_s
    params.simulation.duration_s = duration_s

    with pytest.raises(ValueError):
        apogee.run_sim(params)


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


def test_real_result_saves_to_rrd(tmp_path):
    output = tmp_path / "simulation.rrd"

    saved_path = save_result(apogee.run_sim(apogee.Params()), output)

    assert saved_path == output.resolve()
    assert output.stat().st_size > 0


def test_real_result_logs_data_to_memory():
    recording = rr.RecordingStream("apogee-tests")
    memory = recording.memory_recording()

    try:
        _log_result(apogee.run_sim(apogee.Params()), recording)
        assert memory.num_msgs() > 0
        assert len(memory.drain_as_bytes()) > 0
    finally:
        recording.disconnect()


def test_grid_and_3d_analysis_save_to_rrd(tmp_path):
    result = apogee.Result()
    result.axes = [
        _axis(
            "look_angle_rad",
            [0.0, 0.5, 1.0],
            name="Look Angle",
            unit="rad",
        )
    ]

    response = apogee.VectorSeries3()
    response.entity_id = 0
    response.system = "radar"
    response.key = "response_3d"
    response.name = "3D Response"
    response.unit = "dB"
    response.frame = "analysis_space"
    response.axis_key = "look_angle_rad"
    response.values = [
        _vector(0.0, 0.0, -20.0),
        _vector(0.5, 0.25, -10.0),
        _vector(1.0, 1.0, -5.0),
    ]
    result.vectors = [response]

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
    result.grids = [grid]

    output = tmp_path / "analysis.rrd"
    save_result(result, output)

    assert output.stat().st_size > 0
