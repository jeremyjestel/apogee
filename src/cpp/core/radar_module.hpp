#pragma once

#include <cmath>
#include <utility>

#include "params.hpp"

// RadarState contains only measurements that may change while the simulation runs.
struct RadarState
{
    double range_to_target_m = 0.0;
};

struct RadarModule
{
    // Each module owns a finalized snapshot so parameter edits cannot leak into a run.
    explicit RadarModule(RadarParams input)
        : params(conversions(std::move(input)))
    {
    }

    const RadarParams params;
    RadarState state;

private:
    // Convert editable units and decibel quantities into runtime-ready values once.
    static RadarParams conversions(RadarParams params)
    {
        constexpr double SOL = 2.99792458e8; 

        // Convert frequency, power, gain, noise, and loss into calculation units.
        params.frequency_ghz = params.frequency_hz / 1e9;
        params.wavelength_m = 299792458.0 / params.frequency_hz;
        params.power_w = std::pow(10.0, params.power_dbw / 10.0);
        params.tx_gain_linear = std::pow(10.0, params.tx_gain_db / 10.0);
        params.rx_gain_linear = std::pow(10.0, params.rx_gain_db / 10.0);
        params.noise_figure_linear =
            std::pow(10.0, params.noise_figure_db / 10.0);
        params.system_loss_linear =
            std::pow(10.0, params.system_loss_db / 10.0);

        // Derive sample timing and range limits from bandwidth and pulse timing.
        params.sampling_rate_hz = params.bandwidth_hz * 3.0;
        params.pulse_width_s = params.pulse_width_us / 1e6;
        params.pri_s = params.pri_us / 1e6;
        params.minimum_detection_range_m = SOL * params.pulse_width_s / 2.0;
        params.maximum_unambiguous_range_m = SOL * params.pri_s / 2.0;

        return params;
    }
};
