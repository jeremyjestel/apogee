#include "analysis/radar_range.hpp"

#include <cstddef>
#include <cmath>
#include <limits>
#include <numbers>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

#include "params.hpp"
#include "core/result.hpp"
constexpr double BOLTZMANN_CONSTANT = 1.380649e-23;

void append_radar_range_analysis(
    const BlueRadarParams& radar,
    int entity_id,
    Result& result
)
{
    if (entity_id <= 0)
    {
        throw std::invalid_argument("Radar analysis requires a valid entity ID");
    }
    if (!std::isfinite(radar.range_step_m) ||
        !std::isfinite(radar.max_range_m) ||
        radar.range_step_m <= 0.0 ||
        radar.max_range_m < radar.range_step_m)
    {
        throw std::invalid_argument(
            "Radar range limits and step must be finite and positive"
        );
    }
    if (!std::isfinite(radar.wavelength_m) ||
        !std::isfinite(radar.bandwidth_hz) ||
        radar.wavelength_m <= 0.0 ||
        radar.bandwidth_hz <= 0.0)
    {
        throw std::invalid_argument(
            "Radar wavelength and bandwidth must be finite and positive"
        );
    }
    const double db_parameters[] = {
        radar.power_dbw,
        radar.tx_gain_db,
        radar.rx_gain_db,
        radar.RCS_dbsm,
        radar.noise_figure_db,
        radar.system_loss_db
    };
    for (const double value : db_parameters)
    {
        if (!std::isfinite(value))
        {
            throw std::invalid_argument(
                "Radar equation parameters must be finite"
            );
        }
    }

    std::vector<double> ranges_m;
    std::vector<double> ranges_km;
    std::vector<double> snr_db;

    const double sample_count_value = std::floor(
        radar.max_range_m / radar.range_step_m
    );
    if (!std::isfinite(sample_count_value) ||
        sample_count_value >= static_cast<double>(
            std::numeric_limits<std::size_t>::max()
        ))
    {
        throw std::length_error("Radar range analysis has too many samples");
    }

    const std::size_t sample_count = static_cast<std::size_t>(sample_count_value);
    ranges_m.reserve(sample_count);
    ranges_km.reserve(sample_count);
    snr_db.reserve(sample_count);

    for (std::size_t index = 1; index <= sample_count; ++index)
    {
        const double range_m = static_cast<double>(index) * radar.range_step_m;
        ranges_m.push_back(range_m);
        ranges_km.push_back(range_m / 1000.0);
        
        const double numerator =
            radar.power_dbw + radar.tx_gain_db + radar.rx_gain_db +
            radar.RCS_dbsm + 20.0 * std::log10(radar.wavelength_m);

        const double noise_term =
            10.0 * std::log10(BOLTZMANN_CONSTANT) +
            10.0 * std::log10(290.0) + radar.noise_figure_db +
            10.0 * std::log10(radar.bandwidth_hz);
        const double denominator =
            3.0 * std::log10(4.0 * std::numbers::pi) +
            40.0 * std::log10(range_m) + radar.system_loss_db + noise_term;

        const double snr = numerator - denominator;
        if (!std::isfinite(snr))
        {
            throw std::runtime_error("Radar analysis produced a non-finite SNR");
        }

        snr_db.push_back(snr);
    }

    const std::string axis_key =
        "radar_range_m_entity_" + std::to_string(entity_id);

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
