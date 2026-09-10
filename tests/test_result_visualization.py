from unittest.mock import Mock

import numpy as np
import pytest
import rerun as rr

import apogee
from parameter_window import create_params_from_text, default_parameter_values
from visualization import rerun_adapter
from visualization.rerun_adapter import _log_result
from visualization.telemetry_catalog import build_telemetry_catalog


def _parameter_values(params):
    return {
        spec.path: apogee.get_parameter(params, spec.path)
        for spec in apogee.parameter_specs()
    }


def _short_result():
    params = apogee.Params()
    apogee.set_parameter(params, "simulation.duration_s", 0.1)
    return apogee.run_sim(params)


def test_parameter_schema_defaults_and_text_round_trip():
    specs = apogee.parameter_specs()
    paths = [spec.path for spec in specs]
    defaults = _parameter_values(apogee.Params())
    displayed = default_parameter_values()
    groups = list(dict.fromkeys(spec.group for spec in specs))
    specs_by_path = {spec.path: spec for spec in specs}

    assert specs
    assert len(paths) == len(set(paths))
    assert set(paths) == set(defaults)
    assert displayed.keys() == defaults.keys()
    assert all(spec.group and spec.name for spec in specs)

    expected_groups = [
        "Simulation",
        "Radar Analysis",
        "Blue Radar",
        "Blue Satellite",
        "Red Missile",
        "Blue Interceptor",
    ]
    assert set(expected_groups) <= set(groups)
    assert [groups.index(group) for group in expected_groups] == sorted(
        groups.index(group) for group in expected_groups
    )

    required_paths = {
        "radar_analysis.max_range_m",
        "radar_analysis.range_samples",
        "blue_radar.ground.latitude_deg",
        "blue_radar.ground.longitude_deg",
        "blue_radar.ground.altitude_m",
        "blue_radar.radar.frequency_hz",
        "blue_radar.radar.pulse_width_us",
        "blue_radar.radar.pri_us",
        "blue_radar.radar_signature_dbsm",
        "blue_satellite.satellite.orbital_altitude_m",
        "blue_satellite.satellite.orbit_direction",
        "blue_satellite.satellite.inclination_deg",
        "blue_satellite.satellite.ascending_node_deg",
        "blue_satellite.satellite.orbital_phase_deg",
        "blue_satellite.radar_signature_dbsm",
        "red_missile.initial_pursuit.latitude_deg",
        "red_missile.initial_pursuit.longitude_deg",
        "red_missile.initial_pursuit.altitude_m",
        "red_missile.initial_pursuit.speed_mps",
        "red_missile.radar_signature_dbsm",
        "blue_interceptor.initial_pursuit.latitude_deg",
        "blue_interceptor.initial_pursuit.longitude_deg",
        "blue_interceptor.initial_pursuit.altitude_m",
        "blue_interceptor.initial_pursuit.speed_mps",
        "blue_interceptor.radar_signature_dbsm",
    }
    assert required_paths <= set(paths)
    assert specs_by_path["simulation.dt_s"].unit == "s"
    assert specs_by_path["blue_radar.radar.frequency_hz"].name == "Frequency"
    assert defaults["blue_radar.radar.frequency_hz"] == pytest.approx(5e9)
    assert defaults["blue_satellite.satellite.orbital_altitude_m"] == pytest.approx(
        500_000.0
    )
    assert defaults["red_missile.radar_signature_dbsm"] == pytest.approx(-10.0)

    assert not any(
        path.startswith("blue_satellite.initial_kinematics") for path in paths
    )
    assert not any(
        path.startswith("red_missile.initial_kinematics") for path in paths
    )
    assert not any(
        path.startswith("blue_interceptor.initial_kinematics") for path in paths
    )

    edited_text = {path: str(value + 0.125) for path, value in defaults.items()}
    edited = _parameter_values(create_params_from_text(edited_text))
    for path, original in defaults.items():
        assert float(displayed[path]) == pytest.approx(original)
        assert edited[path] == pytest.approx(original + 0.125)


def test_edited_run_contains_complete_kinematic_histories():
    values = default_parameter_values()
    values["simulation.dt_s"] = "0.25"
    values["simulation.duration_s"] = "0.5"
    values["blue_radar.ground.latitude_deg"] = "0"
    values["blue_radar.ground.longitude_deg"] = "0"
    values["blue_radar.ground.altitude_m"] = "629000"

    result = apogee.run_sim(create_params_from_text(values))
    expected_keys = {
        "blue_radar",
        "blue_satellite",
        "red_missile",
        "blue_interceptor",
    }
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
    assert radar_position.values[0].x == pytest.approx(7_000_000.0)

    for entity in result.entities:
        vectors = [
            series
            for series in result.vectors
            if series.entity_id == entity.id and series.system == "kinematics"
        ]
        speed = next(
            series
            for series in result.scalars
            if series.entity_id == entity.id and series.key == "speed"
        )
        assert [series.key for series in vectors] == [
            "position",
            "velocity",
            "acceleration",
        ]
        assert all(series.frame == "eci" for series in vectors)
        assert all(len(series.values) == len(simulation_time) for series in vectors)
        assert len(speed.values) == len(simulation_time)


def test_ground_lla_and_earth_rotation_define_radar_kinematics():
    params = apogee.Params()
    apogee.set_parameter(params, "simulation.dt_s", 1.0)
    apogee.set_parameter(params, "simulation.duration_s", 2.0)
    apogee.set_parameter(params, "blue_radar.ground.latitude_deg", 0.0)
    apogee.set_parameter(params, "blue_radar.ground.longitude_deg", 0.0)
    apogee.set_parameter(params, "blue_radar.ground.altitude_m", 0.0)

    result = apogee.run_sim(params)
    radar = next(entity for entity in result.entities if entity.key == "blue_radar")
    position = next(
        item for item in result.vectors
        if item.entity_id == radar.id and item.key == "position"
    )
    velocity = next(
        item for item in result.vectors
        if item.entity_id == radar.id and item.key == "velocity"
    )

    assert position.values[0].x == pytest.approx(apogee.constants.earth_mean_radius_m)
    assert position.values[0].y == pytest.approx(0.0, abs=1e-9)
    assert position.values[1].y > 0.0
    assert velocity.values[0].y == pytest.approx(
        apogee.constants.earth_rotation_rate_rad_s
        * apogee.constants.earth_mean_radius_m
    )


def test_initial_pursuit_velocities_point_at_initial_targets():
    params = apogee.Params()
    apogee.set_parameter(params, "simulation.duration_s", 0.1)
    result = apogee.run_sim(params)
    entities = {entity.key: entity for entity in result.entities}

    def initial_vector(entity_key, vector_key):
        entity = entities[entity_key]
        value = next(
            item for item in result.vectors
            if item.entity_id == entity.id and item.key == vector_key
        ).values[0]
        return np.array([value.x, value.y, value.z])

    for entity_key, target_key in (
        ("red_missile", "blue_satellite"),
        ("blue_interceptor", "red_missile"),
    ):
        position = initial_vector(entity_key, "position")
        target_position = initial_vector(target_key, "position")
        velocity = initial_vector(entity_key, "velocity")
        acceleration = initial_vector(entity_key, "acceleration")
        target_direction = target_position - position

        assert np.linalg.norm(np.cross(velocity, target_direction)) == pytest.approx(
            0.0, abs=1e-3
        )
        assert np.dot(velocity, target_direction) > 0.0
        assert acceleration == pytest.approx(np.zeros(3))


def test_satellite_altitude_and_direction_define_circular_state():
    params = apogee.Params()
    altitude_m = 1_000_000.0
    apogee.set_parameter(params, "simulation.duration_s", 0.1)
    apogee.set_parameter(
        params, "blue_satellite.satellite.orbital_altitude_m", altitude_m
    )
    apogee.set_parameter(
        params, "blue_satellite.satellite.orbit_direction", -1.0
    )

    result = apogee.run_sim(params)
    satellite = next(
        entity for entity in result.entities if entity.key == "blue_satellite"
    )
    position = next(
        item for item in result.vectors
        if item.entity_id == satellite.id and item.key == "position"
    ).values[0]
    velocity = next(
        item for item in result.vectors
        if item.entity_id == satellite.id and item.key == "velocity"
    ).values[0]
    radius_m = apogee.constants.earth_mean_radius_m + altitude_m

    assert position.y == pytest.approx(radius_m)
    assert velocity.x == pytest.approx(
        (apogee.constants.earth_mu_m3_s2 / radius_m) ** 0.5
    )


def test_satellite_angles_orient_the_circular_orbit():
    params = apogee.Params()
    altitude_m = 500_000.0
    apogee.set_parameter(params, "simulation.duration_s", 0.1)
    apogee.set_parameter(
        params, "blue_satellite.satellite.inclination_deg", 63.0
    )
    apogee.set_parameter(
        params, "blue_satellite.satellite.ascending_node_deg", 25.0
    )
    apogee.set_parameter(
        params, "blue_satellite.satellite.orbital_phase_deg", 40.0
    )

    result = apogee.run_sim(params)
    satellite = next(
        entity for entity in result.entities if entity.key == "blue_satellite"
    )
    position_value = next(
        item for item in result.vectors
        if item.entity_id == satellite.id and item.key == "position"
    ).values[0]
    velocity_value = next(
        item for item in result.vectors
        if item.entity_id == satellite.id and item.key == "velocity"
    ).values[0]
    position = np.array([position_value.x, position_value.y, position_value.z])
    velocity = np.array([velocity_value.x, velocity_value.y, velocity_value.z])
    radius_m = apogee.constants.earth_mean_radius_m + altitude_m

    assert np.linalg.norm(position) == pytest.approx(radius_m)
    assert np.linalg.norm(velocity) == pytest.approx(
        (apogee.constants.earth_mu_m3_s2 / radius_m) ** 0.5
    )
    assert np.dot(position, velocity) == pytest.approx(0.0, abs=1e-5)
    assert position[2] != pytest.approx(0.0)


def test_radar_analysis_uses_radar_and_missile_parameters():
    params = apogee.Params()
    apogee.set_parameter(params, "simulation.duration_s", 0.0)
    apogee.set_parameter(params, "radar_analysis.max_range_m", 30.0)
    apogee.set_parameter(params, "radar_analysis.range_samples", 3.0)

    baseline = apogee.run_sim(params)
    baseline_curve = next(curve for curve in baseline.curves if curve.key == "snr")
    baseline_snr = baseline_curve.values
    radar = next(entity for entity in baseline.entities if entity.key == "blue_radar")

    power_path = "blue_radar.radar.power_dbw"
    apogee.set_parameter(
        params,
        power_path,
        apogee.get_parameter(params, power_path) + 10.0,
    )
    powered_snr = next(
        curve.values
        for curve in apogee.run_sim(params).curves
        if curve.key == "snr"
    )

    rcs_path = "red_missile.radar_signature_dbsm"
    apogee.set_parameter(
        params,
        rcs_path,
        apogee.get_parameter(params, rcs_path) + 10.0,
    )
    larger_target_snr = next(
        curve.values
        for curve in apogee.run_sim(params).curves
        if curve.key == "snr"
    )

    frequency_path = "blue_radar.radar.frequency_hz"
    apogee.set_parameter(
        params,
        frequency_path,
        apogee.get_parameter(params, frequency_path) * 2.0,
    )
    higher_frequency_snr = next(
        curve.values
        for curve in apogee.run_sim(params).curves
        if curve.key == "snr"
    )

    assert baseline_curve.x_axis.key == "radar_range_km"
    assert baseline_curve.x_axis.values == pytest.approx([0.01, 0.02, 0.03])
    assert baseline_curve.entity_id == radar.id
    assert baseline_curve.value_unit == "dB"
    assert baseline_snr[0] == pytest.approx(135.5559052454)
    assert np.subtract(powered_snr, baseline_snr) == pytest.approx([10.0] * 3)
    assert np.subtract(larger_target_snr, powered_snr) == pytest.approx([10.0] * 3)
    assert np.subtract(higher_frequency_snr, larger_target_snr) == pytest.approx(
        [-6.0205999133] * 3
    )


def test_noisy_range_doppler_grid_and_radar_metric_table_contract():
    params = apogee.Params()
    apogee.set_parameter(params, "simulation.duration_s", 0.3)
    apogee.set_parameter(params, "blue_radar.radar.bandwidth_hz", 10_000.0)
    apogee.set_parameter(params, "blue_radar.radar.pulse_width_us", 100.0)
    apogee.set_parameter(params, "blue_radar.radar.pri_us", 1_000.0)

    result = apogee.run_sim(params)
    radar = next(entity for entity in result.entities if entity.key == "blue_radar")
    grid = next(
        grid for grid in result.grid_series if grid.key == "range_doppler_noisy"
    )

    assert grid.entity_id == radar.id
    assert grid.system == "radar"
    assert grid.value_unit == "dB"
    assert (grid.rows, grid.columns) == (27, 16)
    assert grid.x_axis.key == "pulse_index"
    assert grid.y_axis.key == "range_km"
    assert grid.y_axis.unit == "km"
    assert grid.x_axis.values == pytest.approx(list(range(grid.columns)))
    assert grid.time_axis.key == "simulation_time"
    assert grid.time_axis.unit == "s"
    assert grid.time_axis.values == pytest.approx([0.0, 0.1, 0.2])
    assert len(grid.values) == (
        len(grid.time_axis.values) * grid.rows * grid.columns
    )
    assert np.isfinite(grid.values).all()

    minimum_range_km = apogee.constants.speed_of_light_mps * 100e-6 / 2e3
    detectable_range_km = (
        apogee.constants.speed_of_light_mps * (1_000e-6 - 100e-6) / 2e3
    )
    assert grid.y_axis.values == pytest.approx(
        [
            minimum_range_km + index * detectable_range_km / grid.rows
            for index in range(grid.rows)
        ]
    )

    metric_table = next(
        item
        for item in result.metric_tables
        if item.system == "radar" and item.key == "state"
    )
    metrics = {metric.key: metric for metric in metric_table.metrics}
    assert metric_table.entity_id == radar.id
    assert metric_table.time_axis.key == "simulation_time"
    assert metric_table.time_axis.values == pytest.approx([0.0, 0.1, 0.2])
    assert set(metrics) == {
        "target_range",
        "target_velocity",
        "signal_to_noise",
        "pulse_width",
        "pulse_repetition_interval",
    }
    for key in ("target_range", "target_velocity", "signal_to_noise"):
        assert len(metrics[key].values) == len(metric_table.time_axis.values)
        assert np.isfinite(metrics[key].values).all()
    assert metrics["pulse_width"].values == pytest.approx([100.0])
    assert metrics["pulse_repetition_interval"].values == pytest.approx(
        [1_000.0]
    )


def test_telemetry_catalog_contains_only_timeline_series():
    catalog = build_telemetry_catalog(_short_result())

    assert catalog.views
    assert all(view.axis.kind in {"time", "sequence"} for view in catalog.views)
    assert all(view.path.startswith("/telemetry/") for view in catalog.views)
    assert all(not view.coordinates.flags.writeable for view in catalog.views)
    assert all(not view.values.flags.writeable for view in catalog.views)
    assert {view.item.key for view in catalog.views} >= {
        "position",
        "velocity",
        "acceleration",
        "speed",
    }


def test_rerun_logging_emits_scene_and_telemetry_but_no_analysis_artifacts():
    class NoAnalysisAccess:
        def __init__(self, result):
            self._result = result

        def __getattr__(self, name):
            if name in {"curves", "grid_series", "metric_tables"}:
                raise AssertionError(f"Rerun accessed analysis collection {name}")
            return getattr(self._result, name)

    class RecordingSpy:
        def __init__(self):
            self.logs = []
            self.column_paths = []
            self.blueprint = None

        def log(self, path, *archetypes, **kwargs):
            self.logs.append((path, archetypes, kwargs))

        def send_columns(self, path, **kwargs):
            self.column_paths.append(path)

        def send_blueprint(self, blueprint):
            self.blueprint = blueprint

        def flush(self):
            pass

    recording = RecordingSpy()
    _log_result(NoAnalysisAccess(_short_result()), recording)

    paths = [path for path, unused, unused_kwargs in recording.logs]
    paths.extend(recording.column_paths)
    assert any(path.startswith("/world") for path in paths)
    assert any(path.startswith("/telemetry") for path in paths)
    assert not any(path.startswith("/analysis") for path in paths)

    archetype_names = {
        type(archetype).__name__
        for unused_path, archetypes, unused_kwargs in recording.logs
        for archetype in archetypes
    }
    assert archetype_names.isdisjoint(
        {"Image", "EncodedImage", "Tensor", "TextDocument"}
    )
    assert recording.blueprint is not None


def test_real_result_logs_scene_and_telemetry_to_memory():
    recording = rr.RecordingStream("apogee-tests")
    memory = recording.memory_recording()
    try:
        _log_result(_short_result(), recording)
        assert memory.num_msgs() > 0
        assert len(memory.drain_as_bytes()) > 0
    finally:
        recording.disconnect()


def test_view_rerun_uses_an_available_port_and_no_recording_file(monkeypatch):
    port_socket = Mock()
    port_socket.__enter__ = Mock(return_value=port_socket)
    port_socket.__exit__ = Mock(return_value=None)
    port_socket.getsockname.return_value = ("127.0.0.1", 43210)
    recording = Mock()
    spawn = Mock()
    log_result = Mock()
    monkeypatch.setattr(
        rerun_adapter.socket,
        "socket",
        Mock(return_value=port_socket),
    )
    monkeypatch.setattr(
        rerun_adapter.rr,
        "RecordingStream",
        Mock(return_value=recording),
    )
    monkeypatch.setattr(rerun_adapter.rr, "spawn", spawn)
    monkeypatch.setattr(rerun_adapter, "_log_result", log_result)

    result = object()
    rerun_adapter.view_rerun(result)

    port_socket.bind.assert_called_once_with(("127.0.0.1", 0))
    assert spawn.call_args.kwargs["port"] == 43210
    log_result.assert_called_once_with(result, recording)
    recording.save.assert_not_called()
    recording.disconnect.assert_called_once()
