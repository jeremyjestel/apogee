"""Editable radar bandwidth reaches the sampled chirp waveform."""

import numpy as np

import apogee
from scenario import create_params_from_text, default_parameter_values


def test_bandwidth_parameter_sets_chirp_rate_and_waveform_sample_count():
    for bandwidth in (40_000.0, 80_000.0):
        values = default_parameter_values()
        values.update({
            "simulation.duration_s": "0.1",
            "blue_radar.radar.bandwidth_hz": str(bandwidth),
            "blue_radar.radar.pulse_width_us": "100",
            "blue_radar.radar.pri_us": "1000",
        })
        params = create_params_from_text(values)
        assert params.entity("blue_radar").radar.bandwidth_hz == bandwidth
        result = apogee.run_sim(params)
        series = next(item for item in result.arrays
                      if item.system == "radars" and item.key == "index:0/state/wf")
        waveform = np.array(series.values[0].values, dtype=complex)
        sample_rate, pulse_width = 3 * bandwidth, 100e-6
        assert len(waveform) == int(sample_rate * pulse_width)
        np.testing.assert_allclose(np.abs(waveform), 1, atol=1e-13)
        # The second phase difference removes the carrier and isolates chirp curvature.
        phase_curvature = waveform[2:] * waveform[:-2] / waveform[1:-1] ** 2
        expected = np.exp(2j * np.pi * (bandwidth / pulse_width) / sample_rate ** 2)
        np.testing.assert_allclose(phase_curvature, expected, atol=1e-8)
