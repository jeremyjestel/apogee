import numpy as np
import pytest
import rerun as rr

import apogee
from parameter_window import create_params_from_text, default_parameter_values
from visualization import save_result
from visualization.chart_renderer import render_grid_chart, render_xy_chart
from visualization.rerun_adapter import _log_result
from visualization.view_catalog import (
    CURVE_SOURCE,
    GRID_SOURCE,
    SNAPSHOT_SOURCE,
    SPATIAL_2D_VIEW,
    TEXT_VIEW,
    build_view_catalog,
)


def _parameter_values(params):
    # Materialize the dynamic parameter schema as a path-to-value mapping for comparisons.
    return {
        spec.path: apogee.get_parameter(params, spec.path)
        for spec in apogee.parameter_specs()
    }


def _axis(key, values, *, name="Axis", unit=""):
    # Build a bound C++ axis object for focused visualization tests.
    axis = apogee.Axis()
    axis.key = key
    axis.name = name
    axis.unit = unit
    axis.kind = "continuous"
    axis.values = values
    return axis


def _vector(x, y, z):
    # Build a bound C++ vector because analysis series require Vec3 values.
    value = apogee.Vec3()
    value.x = x
    value.y = y
    value.z = z
    return value


def test_parameter_schema_defaults_and_text_round_trip():
    # Collect both metadata and defaults from the same schema exposed to the UI.
    specs = apogee.parameter_specs()
    paths = [spec.path for spec in specs]
    defaults = _parameter_values(apogee.Params())
    displayed = default_parameter_values()
    groups = list(dict.fromkeys(spec.group for spec in specs))
    specs_by_path = {spec.path: spec for spec in specs}

    # The schema must expose each parameter exactly once with usable display metadata.
    assert specs
    assert len(paths) == len(set(paths))
    assert set(paths) == set(defaults)
    assert displayed.keys() == defaults.keys()
    assert all(spec.group and spec.name for spec in specs)

    # Stable group order keeps the parameter window organized by scenario object.
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

    # These representative paths cover global, component, and entity-level values.
    assert {
        "radar_analysis.max_range_m",
        "radar_analysis.range_samples",
        "blue_radar.radar.frequency_hz",
        "blue_radar.radar.pulse_width_us",
        "blue_radar.radar.pri_us",
        "blue_radar.radar_signature_dbsm",
        "blue_satellite.radar_signature_dbsm",
        "red_missile.radar_signature_dbsm",
        "blue_interceptor.radar_signature_dbsm",
    } <= set(paths)

    # Representative metadata and defaults guard the intended scenario configuration.
    assert specs_by_path["simulation.dt_s"].unit == "s"
    assert specs_by_path["blue_radar.radar.frequency_hz"].name == "Frequency"
    assert defaults["blue_radar.radar.frequency_hz"] == pytest.approx(5e9)
    assert defaults["red_missile.radar_signature_dbsm"] == pytest.approx(-10.0)
    assert defaults["blue_radar.radar_signature_dbsm"] == pytest.approx(0.0)
    assert defaults["blue_satellite.radar_signature_dbsm"] == pytest.approx(0.0)
    assert defaults["blue_interceptor.radar_signature_dbsm"] == pytest.approx(0.0)

    # Entity-specific parameter classes should not return after the generic schema refactor.
    for old_type in (
        "BlueRadarParams",
        "BlueSatelliteParams",
        "RedMissileParams",
        "BlueInterceptorParams",
    ):
        assert not hasattr(apogee, old_type)

    # String edits mimic text-box input and verify every generated path can round-trip.
    edited_text = {
        path: str(value + 0.125)
        for path, value in defaults.items()
    }
    edited = _parameter_values(create_params_from_text(edited_text))

    # The displayed defaults and parsed edits must retain their numeric values.
    for path, original in defaults.items():
        assert float(displayed[path]) == pytest.approx(original)
        assert edited[path] == pytest.approx(original + 0.125)


def test_edited_run_contains_the_fixed_four_entities():
    # Apply a short run and one visible position edit through the same text interface as the UI.
    values = default_parameter_values()
    values["simulation.dt_s"] = "0.25"
    values["simulation.duration_s"] = "0.5"
    values["blue_radar.initial_kinematics.pos_m.x"] = "7000000"

    params = create_params_from_text(values)
    result = apogee.run_sim(params)

    # The default scenario always produces these four uniquely keyed entities.
    expected_keys = {
        "blue_radar",
        "blue_satellite",
        "red_missile",
        "blue_interceptor",
    }
    assert len(result.entities) == 4
    assert {entity.key for entity in result.entities} == expected_keys

    # A half-second run with quarter-second steps logs the state at each step start.
    axes = {axis.key: axis for axis in result.axes}
    simulation_time = axes["simulation_time"].values
    assert simulation_time == pytest.approx([0.0, 0.25])

    # Locate the radar's position series by identity rather than relying on list order.
    radar = next(entity for entity in result.entities if entity.key == "blue_radar")
    radar_position = next(
        series
        for series in result.vectors
        if series.entity_id == radar.id and series.key == "position"
    )
    assert radar_position.values[0].x == pytest.approx(7000000.0)

    # Every entity should have a complete ECI kinematic history aligned to simulation time.
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
    # Keep the analysis grid tiny so parameter sensitivity is easy to verify numerically.
    params = apogee.Params()
    apogee.set_parameter(params, "simulation.duration_s", 0.0)
    apogee.set_parameter(params, "radar_analysis.max_range_m", 30.0)
    apogee.set_parameter(params, "radar_analysis.range_samples", 3.0)

    # Capture the self-contained SNR curve and owning radar identity.
    baseline = apogee.run_sim(params)
    baseline_snr_curve = next(curve for curve in baseline.curves if curve.key == "snr")
    range_axis = baseline_snr_curve.x_axis
    baseline_snr = baseline_snr_curve.values
    radar = next(entity for entity in baseline.entities if entity.key == "blue_radar")

    # Raising transmit power by 10 dB should raise every SNR sample by 10 dB.
    power_path = "blue_radar.radar.power_dbw"
    apogee.set_parameter(
        params,
        power_path,
        apogee.get_parameter(params, power_path) + 10.0,
    )
    powered = apogee.run_sim(params)
    powered_snr = next(
        curve.values for curve in powered.curves if curve.key == "snr"
    )

    # Raising target radar cross-section by 10 dB should add another 10 dB to SNR.
    rcs_path = "red_missile.radar_signature_dbsm"
    apogee.set_parameter(
        params,
        rcs_path,
        apogee.get_parameter(params, rcs_path) + 10.0,
    )
    larger_target = apogee.run_sim(params)
    larger_target_snr = next(
        curve.values for curve in larger_target.curves if curve.key == "snr"
    )

    # Doubling frequency halves wavelength and therefore reduces this model's SNR by about 6 dB.
    frequency_path = "blue_radar.radar.frequency_hz"
    apogee.set_parameter(
        params,
        frequency_path,
        apogee.get_parameter(params, frequency_path) * 2.0,
    )
    higher_frequency = apogee.run_sim(params)
    higher_frequency_snr = next(
        curve.values for curve in higher_frequency.curves if curve.key == "snr"
    )

    # Check the absolute baseline and each cumulative radar-equation sensitivity.
    assert range_axis.values == pytest.approx([0.01, 0.02, 0.03])
    assert range_axis.key == "radar_range_km"
    assert baseline_snr_curve.entity_id == radar.id
    assert baseline_snr_curve.value_unit == "dB"
    assert baseline_snr[0] == pytest.approx(135.5559052454)
    assert np.subtract(powered_snr, baseline_snr) == pytest.approx([10.0] * 3)
    assert np.subtract(larger_target_snr, powered_snr) == pytest.approx([10.0] * 3)
    assert np.subtract(higher_frequency_snr, larger_target_snr) == pytest.approx(
        [-6.0205999133] * 3
    )


def test_noisy_range_doppler_map_is_published_as_a_db_grid():
    # Use one short update and a small swath while preserving the processing output.
    params = apogee.Params()
    apogee.set_parameter(params, "simulation.duration_s", 0.1)
    apogee.set_parameter(params, "blue_radar.radar.bandwidth_hz", 10_000.0)
    apogee.set_parameter(params, "blue_radar.radar.pulse_width_us", 100.0)
    apogee.set_parameter(params, "blue_radar.radar.pri_us", 1_000.0)

    result = apogee.run_sim(params)
    radar = next(entity for entity in result.entities if entity.key == "blue_radar")
    grid = next(grid for grid in result.grids if grid.key == "range_doppler_noisy")

    assert grid.entity_id == radar.id
    assert grid.system == "radar"
    assert grid.value_unit == "dB"
    assert grid.rows == 27
    assert grid.columns == 16
    assert grid.x_axis.key == "pulse_index"
    assert grid.y_axis.key == "range_km"
    assert grid.y_axis.name == "Range"
    assert grid.y_axis.unit == "km"
    assert grid.x_axis.values == pytest.approx(list(range(grid.columns)))
    minimum_range_km = (
        apogee.constants.speed_of_light_mps * 100e-6 / 2.0 / 1_000.0
    )
    detectable_range_km = (
        apogee.constants.speed_of_light_mps * (1_000e-6 - 100e-6)
        / 2.0
        / 1_000.0
    )
    assert grid.y_axis.values == pytest.approx(
        [
            minimum_range_km + index * detectable_range_km / grid.rows
            for index in range(grid.rows)
        ]
    )
    assert len(grid.values) == grid.rows * grid.columns
    assert np.isfinite(grid.values).all()

    snapshot = next(
        snapshot
        for snapshot in result.snapshots
        if snapshot.system == "radar" and snapshot.key == "state"
    )
    state = {
        metric.key: metric
        for metric in snapshot.metrics
    }
    assert snapshot.entity_id == radar.id
    assert snapshot.key == "state"
    assert set(state) == {
        "target_range",
        "target_velocity",
        "signal_to_noise",
        "pulse_width",
        "pulse_repetition_interval",
    }
    assert {metric.unit for metric in state.values()} == {"m", "m/s", "dB", "us"}
    assert state["pulse_width"].value == pytest.approx(100.0)
    assert state["pulse_repetition_interval"].value == pytest.approx(1_000.0)
    assert np.isfinite([metric.value for metric in state.values()]).all()

    # The shared catalog is the single ordering and path contract for both logging
    # and the blueprint. Each Blue Radar product receives a full analysis tab while
    # its raw data remains separate from its rendered artifact.
    catalog = build_view_catalog(result)
    radar_analysis = [
        view
        for view in catalog.in_section("analysis")
        if view.owner_id == radar.id
    ]
    assert [view.source_type for view in radar_analysis] == [
        CURVE_SOURCE,
        GRID_SOURCE,
        SNAPSHOT_SOURCE,
    ]
    assert [view.item.key for view in radar_analysis] == [
        "snr",
        "range_doppler_noisy",
        "state",
    ]
    assert [view.order for view in radar_analysis] == [10, 20, 30]
    assert all(not view.group for view in radar_analysis)
    assert [view.view_type for view in radar_analysis] == [
        SPATIAL_2D_VIEW,
        SPATIAL_2D_VIEW,
        TEXT_VIEW,
    ]
    for view in radar_analysis:
        assert view.base_path == (
            f"/analysis/entities/blue_radar/{view.item.system}/{view.item.key}"
        )
        assert view.data_path == f"{view.base_path}/data"
        assert view.plot_path == f"{view.base_path}/plot"
        assert view.data_path != view.plot_path


def test_continuous_analysis_chart_renders():
    # Render a curve with enough contrast to detect a blank or incorrectly shaped image.
    image = np.asarray(
        render_xy_chart(
            [10.0, 1000.0, 5000.0, 10000.0],
            [90.0, 45.0, 20.0, -15.0],
            x_name="Range",
            x_unit="m",
            y_name="SNR",
            y_unit="dB",
            color=[40, 110, 255],
        )
    )

    # The chart renderer should return a non-uniform RGB byte image for Rerun.
    assert image.ndim == 3
    assert image.shape[2] == 3
    assert image.dtype == np.uint8
    assert image.std() > 10.0


def test_grid_analysis_chart_renders_with_formal_axes_and_color_scale():
    image = np.asarray(
        render_grid_chart(
            [[-90.0, -60.0, -30.0], [-75.0, -45.0, 0.0]],
            x_values=[0.0, 1.0, 2.0],
            y_values=[100.0, 200.0],
            title="Noisy Range-Doppler Map",
            x_name="Pulse",
            x_unit="",
            y_name="Range Sample",
            y_unit="",
            value_unit="dB",
        )
    )

    assert image.shape == (495, 880, 3)
    assert image.dtype == np.uint8
    assert image.std() > 10.0


def test_catalog_orders_and_groups_products_without_key_specific_ui_code():
    result = apogee.Result()

    def curve(key, order=0, group=""):
        item = apogee.Curve1D()
        item.entity_id = 0
        item.system = "radar"
        item.key = key
        item.name = key.replace("_", " ").title()
        item.x_axis = _axis("range_km", [1.0], name="Range", unit="km")
        item.value_unit = "dB"
        item.values = [1.0]
        presentation = apogee.Presentation()
        presentation.order = order
        presentation.group = group
        item.presentation = presentation
        return item

    result.curves = [
        curve("automatic"),
        curve("second", order=20, group="Detection"),
        curve("first", order=10, group="Detection"),
    ]

    views = build_view_catalog(result).in_section("analysis")
    assert [view.item.key for view in views] == ["first", "second", "automatic"]
    assert [view.group for view in views] == ["Detection", "Detection", ""]


def test_catalog_claims_empty_product_paths_before_filtering():
    result = apogee.Result()

    def empty_curve(name):
        item = apogee.Curve1D()
        item.entity_id = 0
        item.system = "radar"
        item.key = "duplicate"
        item.name = name
        item.x_axis = _axis("range_km", [], name="Range", unit="km")
        item.value_unit = "dB"
        item.values = []
        return item

    result.curves = [empty_curve("First"), empty_curve("Second")]
    with pytest.raises(ValueError, match="Multiple result items map"):
        build_view_catalog(result)


def test_grid_raw_values_are_logged_as_a_native_tensor():
    result = apogee.Result()
    grid = apogee.Grid2D()
    grid.entity_id = 0
    grid.system = "radar"
    grid.key = "map"
    grid.name = "Map"
    grid.x_axis = _axis("pulse", [0.0, 1.0], name="Pulse")
    grid.y_axis = _axis("range", [1.0, 2.0], name="Range", unit="km")
    grid.value_unit = "dB"
    grid.rows = 2
    grid.columns = 2
    grid.values = [1.0, 2.0, 3.0, 4.0]
    result.grids = [grid]

    class RecordingSpy:
        def __init__(self):
            self.logs = []

        def log(self, path, *archetypes, **kwargs):
            self.logs.append((path, archetypes, kwargs))

        def send_columns(self, *args, **kwargs):
            pass

        def send_blueprint(self, blueprint):
            self.blueprint = blueprint

        def flush(self):
            pass

    recording = RecordingSpy()
    _log_result(result, recording)

    data_path = "/analysis/entities/global/radar/map/data"
    data_archetypes = [
        archetype
        for path, archetypes, unused_kwargs in recording.logs
        if path == data_path
        for archetype in archetypes
    ]
    assert any(type(archetype).__name__ == "Tensor" for archetype in data_archetypes)
    plot_archetypes = [
        archetype
        for path, archetypes, unused_kwargs in recording.logs
        if path == "/analysis/entities/global/radar/map/plot"
        for archetype in archetypes
    ]
    assert any(
        type(archetype).__name__ == "EncodedImage"
        for archetype in plot_archetypes
    )


def test_real_result_saves_to_rrd(tmp_path):
    # Saving an actual simulation exercises the full result-to-Rerun serialization path.
    output = tmp_path / "simulation.rrd"

    saved_path = save_result(apogee.run_sim(apogee.Params()), output)

    assert saved_path == output.resolve()
    assert output.stat().st_size > 0


def test_real_result_logs_data_to_memory():
    # An in-memory recording verifies logging without starting the interactive viewer.
    recording = rr.RecordingStream("apogee-tests")
    memory = recording.memory_recording()

    try:
        # A successful adapter pass must emit at least one drainable Rerun message.
        _log_result(apogee.run_sim(apogee.Params()), recording)
        assert memory.num_msgs() > 0
        assert len(memory.drain_as_bytes()) > 0
    finally:
        recording.disconnect()


def test_grid_and_3d_analysis_save_to_rrd(tmp_path):
    # Assemble a minimal result containing both 3D samples and a two-dimensional grid.
    result = apogee.Result()
    result.axes = [
        _axis(
            "look_angle_rad",
            [0.0, 0.5, 1.0],
            name="Look Angle",
            unit="rad",
        )
    ]

    # The vector series represents arbitrary 3D analysis coordinates over look angle.
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

    # The flattened values use row-major order across Doppler rows and range columns.
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

    # A non-empty recording confirms both uncommon analysis types serialize together.
    output = tmp_path / "analysis.rrd"
    save_result(result, output)

    assert output.stat().st_size > 0
