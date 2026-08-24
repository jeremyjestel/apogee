#include "analysis/radar_range.hpp"

#include <cmath>
#include <cstddef>
#include <numbers>
#include <utility>
#include <vector>

namespace
{
constexpr double BOLTZMANN_CONSTANT = 1.380649e-23;
constexpr double NOISE_TEMPERATURE_K = 290.0;
}

void radar_range_analysis(
    const RadarParams& radar,
    double target_radar_cross_section_dbsm,
    const RadarAnalysisParams& analysis,
    int entity_id,
    Result& result
)
{
    // Convert the UI sample count into evenly spaced physical ranges.
    const std::size_t sample_count =
        static_cast<std::size_t>(analysis.range_samples);
    const double range_step_m = analysis.max_range_m / sample_count;

    // Reserve both output arrays because their final size is known up front.
    std::vector<double> ranges_km;
    std::vector<double> snr_db;
    ranges_km.reserve(sample_count);
    snr_db.reserve(sample_count);

    // Combine the range-independent radar-equation terms in decibels.
    const double signal_db =
        radar.power_dbw +
        radar.tx_gain_db +
        radar.rx_gain_db +
        target_radar_cross_section_dbsm +
        20.0 * std::log10(radar.wavelength_m);

    // Express thermal noise and receiver noise figure in the same dB domain.
    const double noise_db =
        10.0 * std::log10(BOLTZMANN_CONSTANT) +
        10.0 * std::log10(NOISE_TEMPERATURE_K) +
        radar.noise_figure_db +
        10.0 * std::log10(radar.bandwidth_hz);

    // Apply propagation loss at each range and record the resulting SNR.
    for (std::size_t index = 1; index <= sample_count; ++index)
    {
        const double range_m = static_cast<double>(index) * range_step_m;
        const double loss_db =
            30.0 * std::log10(4.0 * std::numbers::pi) +
            40.0 * std::log10(range_m) +
            radar.system_loss_db +
            noise_db;

        ranges_km.push_back(range_m / 1000.0);
        snr_db.push_back(signal_db - loss_db);
    }

    // Publish one shared range axis and its associated scalar analysis series.
    constexpr const char* axis_key = "radar_range_km";

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
