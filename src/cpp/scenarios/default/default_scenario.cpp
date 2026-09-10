#include "scenarios/default/default_scenario.hpp"

#include "core/constants.hpp"
#include "params.hpp"

namespace
{
EntityDefinition make_blue_radar()
{
    return EntityDefinition{
        .id = 1,
        .key = "blue_radar",
        .display_name = "Blue Radar",
        .type = "radar",
        .team = "blue",
        .ground = GroundParams{
            .latitude_deg = 0.0,
            .longitude_deg = 180.0,
            .altitude_m = 0.0
        },
        .radar = RadarParams{
            .frequency_hz = 5e9,
            .power_dbw = 50.0,
            .tx_gain_db = 35.0,
            .rx_gain_db = 20.0,
            .noise_figure_db = 3.0,
            .bandwidth_hz = 1e6,
            .system_loss_db = 3.0,
            .pw_us = 1.0,
            .pri_us = 3000.0
        },
        .radar_signature_dbsm = 0.0
    };
}

EntityDefinition make_blue_satellite()
{
    return EntityDefinition{
        .id = 2,
        .key = "blue_satellite",
        .display_name = "Blue Satellite",
        .type = "satellite",
        .team = "blue",
        .satellite = SatelliteParams{
            .orbital_altitude_m = 500'000.0,
            .orbit_direction = 1.0,
            .inclination_deg = 0.0,
            .ascending_node_deg = 0.0,
            .orbital_phase_deg = 90.0
        },
        .radar_signature_dbsm = 0.0
    };
}

EntityDefinition make_red_missile()
{
    return EntityDefinition{
        .id = 3,
        .key = "red_missile",
        .display_name = "Red Missile",
        .type = "missile",
        .team = "red",
        .initial_pursuit = InitialPursuitParams{
            .latitude_deg = 89.5572968683,
            .longitude_deg = 90.0,
            .altitude_m = 100'193.166642,
            .speed_mps = 1'520.690633,
            .target_key = "blue_satellite"
        },
        .radar_signature_dbsm = -10.0
    };
}

EntityDefinition make_blue_interceptor()
{
    return EntityDefinition{
        .id = 4,
        .key = "blue_interceptor",
        .display_name = "Blue Interceptor",
        .type = "interceptor",
        .team = "blue",
        .initial_pursuit = InitialPursuitParams{
            .latitude_deg = 0.4482395509,
            .longitude_deg = -0.2689502051,
            .altitude_m = 20'265.993526,
            .speed_mps = 1'345.362405,
            .target_key = "red_missile"
        },
        .radar_signature_dbsm = 0.0
    };
}
}

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
        .entities = {
            make_blue_radar(),
            make_blue_satellite(),
            make_red_missile(),
            make_blue_interceptor()
        }
    };
}
