#include "analysis/radar_range.hpp"

#include <cmath>
#include <numbers>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

constexpr double BOLTZMANN_CONSTANT = 1.380649e-23;

void append_radar_range_analysis(
    const BlueRadarParams& radar,
    int entity_id,
    Result& result
)
{
    if (!(radar.range_step_m > 0.0 &&
          radar.max_range_m >= radar.range_step_m &&
          radar.wavelength_m > 0.0 &&
          radar.bandwidth_hz > 0.0))
    {
        throw std::invalid_argument(
            "Radar range, wavelength, and bandwidth must be positive"
        );
    }

    std::vector<double> ranges_km;
    std::vector<double> snr_db;

    const double numerator =
        radar.power_dbw + radar.tx_gain_db + radar.rx_gain_db +
        radar.RCS_dbsm + 20.0 * std::log10(radar.wavelength_m);

    const double noise =
        10.0 * std::log10(BOLTZMANN_CONSTANT) +
        10.0 * std::log10(290.0) + radar.noise_figure_db +
        10.0 * std::log10(radar.bandwidth_hz);

    const int number_of_ranges = static_cast<int>(
        radar.max_range_m / radar.range_step_m
    );

    for (int index = 1; index <= number_of_ranges; ++index)
    {
        const double range_m = index * radar.range_step_m;
        ranges_km.push_back(range_m / 1000.0);

        const double denominator =
            3.0 * std::log10(4.0 * std::numbers::pi) +
            40.0 * std::log10(range_m) + radar.system_loss_db + noise;

        snr_db.push_back(numerator - denominator);
    }

    const std::string axis_key =
        "radar_range_km_entity_" + std::to_string(entity_id);

    result.axes.push_back(Axis{
        .key = axis_key,
        .name = "Range",
        .unit = "km",
        .kind = "continuous",
        .values = std::move(ranges_km)
    });
    result.scalars.push_back(ScalarSeries{
        .entity_id = entity_id,
        .system = "radar",
        .key = "snr",
        .name = "SNR",
        .unit = "dB",
        .axis_key = axis_key,
        .values = std::move(snr_db)
    });
}
