#include "analysis/radar_range.hpp"

#include <cstddef>
#include <utility>
#include <vector>

#include "core/constants.hpp"
#include "math/radar_range_equation.hpp"

void add_snr_range_curve(
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

    // Evaluate the shared radar equation at each analysis range.
    for (std::size_t index = 1; index <= sample_count; ++index)
    {
        const double range_m = static_cast<double>(index) * range_step_m;

        ranges_km.push_back(range_m / constants::meters_per_kilometer);
        const auto radar_equation_result = radar_range_equation(
            radar,
            target_radar_cross_section_dbsm,
            range_m
        );
        snr_db.push_back(radar_equation_result.snr_db);
    }

    // Publish a self-contained static analysis curve.
    result.curves.push_back(Curve1D{
        .entity_id = entity_id,
        .system = "radar",
        .key = "snr",
        .name = "SNR",
        .x_axis = Axis{
            .key = "radar_range_km",
            .name = "Range",
            .unit = "km",
            .kind = "continuous",
            .values = std::move(ranges_km)
        },
        .value_unit = "dB",
        .values = std::move(snr_db),
        .presentation = Presentation{
            .order = 10
        }
    });
}
