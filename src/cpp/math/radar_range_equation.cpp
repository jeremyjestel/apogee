#include "math/radar_range_equation.hpp"

#include <cmath>
#include <numbers>

#include "core/constants.hpp"

RadarEquationResult radar_snr_db(
    const RadarParams& radar,
    double target_rcs_dbsm,
    double range_m
)
{
    const double wavelength_m =
        constants::speed_of_light_mps / radar.frequency_hz;

    // Apply the monostatic radar range equation using linear power values.
    const double received_power_w =
        (radar.power_w *
         radar.tx_gain_lin *
         radar.rx_gain_lin *
         std::pow(wavelength_m, 2) *
         std::pow(10.0, target_rcs_dbsm / 10.0)) /
        (std::pow(4.0 * std::numbers::pi, 3) *
         std::pow(range_m, 4) *
         radar.system_loss_lin);

    // Thermal noise includes the reference temperature and receiver noise figure.
    const double noise_power_w =
        constants::boltzmann_constant_j_per_k *
        constants::reference_noise_temperature_k *
        radar.noise_figure_lin *
        radar.bandwidth_hz;

    const double snr_lin = received_power_w / noise_power_w;
    const double snr_db = 10 * std::log10(snr_lin);
    return RadarEquationResult{
        .received_power_w = received_power_w,
        .noise_power_w = noise_power_w,
        .snr_linear = snr_lin,
        .snr_db = snr_db
    };
}
