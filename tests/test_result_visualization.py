import numpy as np
import pytest
import rerun as rr

import apogee
from plot_result import plot_result
from rerun_integration import show_in_rerun
from visualization import log_result, save_result
from visualization import show_result


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


def _grid(values):
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
    grid.values = values
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


def test_legacy_entry_points_use_the_single_rerun_pipeline():
    assert plot_result is show_result
    assert show_in_rerun is show_result


def test_real_result_contract_is_unique_aligned_and_finite(simulation_result):
    result = simulation_result
    expected_entities = {
        1: ("blue_radar_1", "Blue Radar", "radar", "blue"),
        2: ("blue_satellite_1", "Blue Satellite", "satellite", "blue"),
        3: ("red_missile_1", "Red Missile", "missile", "red"),
        4: ("blue_interceptor_1", "Blue Interceptor", "interceptor", "blue"),
    }

    assert len(result.entities) == 4
    assert len({entity.id for entity in result.entities}) == 4
    assert len({entity.key for entity in result.entities}) == 4
    assert {
        entity.id: (
            entity.key,
            entity.display_name,
            entity.type,
            entity.team,
        )
        for entity in result.entities
    } == expected_entities

    entities = {entity.id: entity for entity in result.entities}
    axes = {axis.key: axis for axis in result.axes}

    assert len(axes) == len(result.axes)
    for axis in result.axes:
        assert np.all(np.isfinite(np.asarray(axis.values, dtype=np.float64)))

    assert result.scalars
    for series in result.scalars:
        assert series.entity_id == 0 or series.entity_id in entities
        assert series.axis_key in axes
        values = np.asarray(series.values, dtype=np.float64)
        assert len(values) == len(axes[series.axis_key].values)
        assert np.all(np.isfinite(values))

    simulation_time = axes["simulation_time"].values
    radar_range = axes["radar_range_m_entity_1"].values
    assert len(simulation_time) == 100
    assert simulation_time[0] == pytest.approx(0.0)
    assert simulation_time[-1] == pytest.approx(9.9)
    assert radar_range[0] > 0.0

    assert result.vectors
    for series in result.vectors:
        assert series.entity_id in entities
        assert series.axis_key in axes
        values = np.asarray(
            [[value.x, value.y, value.z] for value in series.values],
            dtype=np.float64,
        )
        assert values.shape == (len(axes[series.axis_key].values), 3)
        assert np.all(np.isfinite(values))


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


def test_nonfinite_radar_configuration_is_rejected():
    params = apogee.Params()
    radar = params.blue_radar
    radar.range_step_m = float("nan")
    params.blue_radar = radar

    with pytest.raises(ValueError, match="finite and positive"):
        apogee.run_sim(params)


def test_synthetic_grid_logs_to_memory(memory_recording):
    result = apogee.Result()
    result.grids = [_grid([-90.0, -80.0, -70.0, -60.0, -50.0, -40.0])]
    recording, memory = memory_recording

    blueprint = log_result(result, recording)

    assert blueprint is not None
    assert memory.num_msgs() > 0
    assert len(memory.drain_as_bytes()) > 0


def test_global_3d_analysis_logs_to_memory(memory_recording):
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

    recording, memory = memory_recording
    blueprint = log_result(result, recording)

    assert blueprint is not None
    assert memory.num_msgs() > 0
    assert len(memory.drain_as_bytes()) > 0


def test_series_path_collision_raises_value_error(memory_recording):
    result = apogee.Result()
    result.axes = [
        _axis(
            "sample",
            [0.0],
            name="Sample",
        )
    ]

    scalar = apogee.ScalarSeries()
    scalar.entity_id = 0
    scalar.system = "radar"
    scalar.key = "response"
    scalar.name = "Scalar Response"
    scalar.axis_key = "sample"
    scalar.values = [1.0]

    vector = apogee.VectorSeries3()
    vector.entity_id = 0
    vector.system = "radar"
    vector.key = "response"
    vector.name = "Vector Response"
    vector.frame = "analysis_space"
    vector.axis_key = "sample"
    vector.values = [_vector(1.0, 2.0, 3.0)]

    result.scalars = [scalar]
    result.vectors = [vector]

    recording, _ = memory_recording
    with pytest.raises(ValueError, match="same path"):
        log_result(result, recording)


def test_malformed_scalar_shape_raises_value_error(memory_recording):
    result = apogee.Result()
    result.axes = [
        _axis(
            "simulation_time",
            [0.0, 1.0],
            kind="time",
            name="Simulation Time",
            unit="s",
        )
    ]

    series = apogee.ScalarSeries()
    series.entity_id = 0
    series.system = "analysis"
    series.key = "bad_scalar"
    series.name = "Bad Scalar"
    series.unit = "unit"
    series.axis_key = "simulation_time"
    series.values = [1.0]
    result.scalars = [series]

    recording, _ = memory_recording
    with pytest.raises(ValueError, match="has 1 values.*has 2"):
        log_result(result, recording)


def test_malformed_vector_shape_raises_value_error(memory_recording):
    result = apogee.Result()

    entity = apogee.EntityDescriptor()
    entity.id = 1
    entity.key = "test_entity"
    entity.display_name = "Test Entity"
    entity.type = "test"
    entity.team = "blue"
    result.entities = [entity]
    result.axes = [
        _axis(
            "simulation_time",
            [0.0, 1.0],
            kind="time",
            name="Simulation Time",
            unit="s",
        )
    ]

    value = apogee.Vec3()
    value.x = 1.0
    value.y = 2.0
    value.z = 3.0

    series = apogee.VectorSeries3()
    series.entity_id = entity.id
    series.system = "kinematics"
    series.key = "position"
    series.name = "Position"
    series.unit = "m"
    series.frame = "ECI"
    series.axis_key = "simulation_time"
    series.values = [value]
    result.vectors = [series]

    recording, _ = memory_recording
    with pytest.raises(ValueError, match="has 1 values.*has 2"):
        log_result(result, recording)


def test_malformed_grid_shape_raises_value_error(memory_recording):
    result = apogee.Result()
    result.grids = [_grid([-90.0, -80.0, -70.0, -60.0, -50.0])]

    recording, _ = memory_recording
    with pytest.raises(ValueError, match="data does not match its shape"):
        log_result(result, recording)
