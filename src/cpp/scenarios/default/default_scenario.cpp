#include "scenarios/default/default_scenario.hpp"

#include "scenarios/default/entities.hpp"

ScenarioParams make_default_scenario()
{
    // Assemble global settings and fresh entity definitions for one parameter set.
    return ScenarioParams{
        .simulation = SimulationParams{
            .dt_s = 0.1,
            .duration_s = 10.0
        },
        .radar_analysis = RadarAnalysisParams{
            .max_range_m = 10000.0,
            .range_samples = 1000
        },
        // Keeping entity creation in factories separates structure from default values.
        .entities = {
            make_blue_radar_definition(),
            make_blue_satellite_definition(),
            make_red_missile_definition(),
            make_blue_interceptor_definition()
        }
    };
}
