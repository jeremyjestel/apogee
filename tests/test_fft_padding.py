"""Zero padding interpolates the spectrum without changing returns or gain."""

import json

import apogee
import numpy as np
import pytest

from analysis.catalog import RANGE_VELOCITY_MAP, build_analysis_catalog
from scenario import (
    create_params_from_text, decode_scenario_definition, default_parameter_values, encode_scenario,
)


def _run(pulses, factor):
    values = default_parameter_values()
    values.update({
        "simulation.duration_s": "0.1",
        "blue_radar.ground.altitude_m": "100",
        "blue_radar.radar.bandwidth_hz": "10000",
        "blue_radar.radar.pulse_width_us": "100",
        "blue_radar.radar.pri_us": "1000",
        "blue_radar.radar.pulse_num": str(pulses),
        "blue_radar.radar.doppler_zero_pad_factor": str(factor),
        "red_missile.initial_pursuit.latitude_deg": "0",
        "red_missile.initial_pursuit.longitude_deg": "180",
        "red_missile.initial_pursuit.altitude_m": "100000",
    })
    result = apogee.run_sim(create_params_from_text(values))
    arrays = {item.key: item for item in result.arrays if item.system == "radars"}
    def matrix(field):
        sample = arrays[f"index:0/state/{field}"].values[0]
        return np.array(sample.values).reshape(sample.rows, sample.columns)
    velocity = next(product for product in build_analysis_catalog(result).products
                    if product.kind == RANGE_VELOCITY_MAP)
    return matrix("range_pulse_map"), matrix("range_doppler_map"), matrix("range_velocity_map"), velocity


@pytest.mark.parametrize("pulses", [7, 8])
def test_padding_retains_original_bins_gain_and_velocity_bounds(pulses):
    raw, original, _, original_view = _run(pulses, 1)
    padded_raw, padded, velocity_map, padded_view = _run(pulses, 4)
    np.testing.assert_array_equal(raw, padded_raw)
    assert original.shape == (27, pulses)
    assert padded.shape == (27, 4 * pulses)
    assert np.max(np.abs(original)) > 0
    np.testing.assert_array_equal(padded, velocity_map)
    # Original frequency samples occur every fourth padded bin, including odd N.
    indices = (np.arange(pulses) - pulses // 2) * 4 + (4 * pulses) // 2
    np.testing.assert_allclose(padded[:, indices], original, rtol=1e-10, atol=1e-30)
    old_axis = original_view.sample_axes[0][0].values
    new_axis = padded_view.sample_axes[0][0].values
    np.testing.assert_allclose(new_axis[indices], old_axis)
    assert padded_view.sample_x_limits == original_view.sample_x_limits
    assert np.diff(new_axis)[0] == pytest.approx(np.diff(old_axis)[0] / 4)


@pytest.mark.parametrize("version", [1, 2])
def test_older_scenarios_default_missing_padding_settings(version):
    params = apogee.Params()
    if version == 2:
        params.entities = [*params.entities, apogee.make_entity_definition("radar", "extra", 5)]
    values = default_parameter_values(params)
    document = json.loads(encode_scenario(values, params if version == 2 else None))
    paths = [path for path in values if path.endswith(".radar.doppler_zero_pad_factor")]
    for path in paths:
        document["parameters"].pop(path)
    definition, restored = decode_scenario_definition(json.dumps(document))
    runtime = create_params_from_text(restored, definition)
    for path in paths:
        assert apogee.get_parameter(runtime, path) == 4
