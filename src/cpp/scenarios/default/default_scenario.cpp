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
        .initial_kinematics = KinematicState{
            Vec3{-constants::earth_mean_radius_m, 0.0, 0.0},
            Vec3{0.0, 464.6, 0.0},
            Vec3{-0.0339, 0.0, 0.0}
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
        .initial_kinematics = KinematicState{
            Vec3{0.0, constants::earth_mean_radius_m + 500'000.0, 0.0},
            Vec3{-7'616.6, 0.0, 0.0},
            Vec3{0.0, -8.44, 0.0}
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
        .initial_kinematics = KinematicState{
            Vec3{0.0, 50'000.0, constants::earth_mean_radius_m + 100'000.0},
            Vec3{0.0, 1'500.0, 250.0},
            Vec3{-9.52, -0.074, 0.0}
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
        .initial_kinematics = KinematicState{
            Vec3{constants::earth_mean_radius_m + 20'000.0, -30'000.0, 50000},
            Vec3{100.0, 1'200.0, 600.0},
            Vec3{-9.76, 0.046, 0.0}
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
