#pragma once

#include <cstdint>
#include <cmath>
#include <random>
#include <utility>

#include "core/constants.hpp"
#include "params.hpp"

// RadarState contains only measurements that may change while the simulation runs.
struct RadarState
{
    double target_range_m = 0.0;
    double target_vel_mps = 0.0;
    double signal_to_noise_db = 0.0;

};

struct RadarModule
{
    // Each module owns a finalized snapshot so parameter edits cannot leak into a run.
    explicit RadarModule(
        RadarParams input,
        std::uint32_t noise_seed = std::random_device{}()
    )
        : p(conversions(std::move(input))),
          noise_generator(noise_seed)
    {
    }

    const RadarParams p;
    RadarState state;
    std::mt19937 noise_generator;

private:
    // Convert editable units and decibel quantities into runtime-ready values once.
    static RadarParams conversions(RadarParams p)
    {

        // Convert frequency, power, gain, noise, and loss into calculation units.
        p.frequency_ghz =
            p.frequency_hz / constants::hertz_per_gigahertz;
        p.wavelength_m =
            constants::speed_of_light_mps / p.frequency_hz;
        p.power_w = std::pow(10.0, p.power_dbw / 10.0);
        p.tx_gain_lin = std::pow(10.0, p.tx_gain_db / 10.0);
        p.rx_gain_lin = std::pow(10.0, p.rx_gain_db / 10.0);
        p.noise_figure_lin =
            std::pow(10.0, p.noise_figure_db / 10.0);
        p.system_loss_lin =
            std::pow(10.0, p.system_loss_db / 10.0);

        // Derive sample timing and range limits from bandwidth and pulse timing.
        p.sampling_rate_hz =
        p.bandwidth_hz * constants::radar_sampling_rate_multiplier;
        p.pw_s = p.pw_us / constants::microseconds_per_second;
        p.pri_s = p.pri_us / constants::microseconds_per_second;
        p.mdr_m = constants::speed_of_light_mps * p.pw_s / 2.0;
        p.mur_m = constants::speed_of_light_mps * p.pri_s / 2.0;
        p.wavenumber = 2 * constants::pi / p.wavelength_m;

        return p;
    }
};
