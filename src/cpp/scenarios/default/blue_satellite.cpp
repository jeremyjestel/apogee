#include "scenarios/default/entities.hpp"

#include "core/constants.hpp"

EntityDefinition make_blue_satellite_definition()
{
    // This factory is the single home for Blue Satellite's scenario-specific defaults.
    return EntityDefinition{
        .id = 2,
        .key = "blue_satellite",
        .display_name = "Blue Satellite",
        .type = "satellite",
        .team = "blue",
        // Start the satellite in a plausible circular orbit 500 km above Earth.
        .initial_kinematics = KinematicState{
            Vec3{0.0, constants::earth_mean_radius_m + 500'000.0, 0.0},
            Vec3{-7'616.6, 0.0, 0.0},
            Vec3{0.0, -8.44, 0.0}
        },
        .radar_signature_dbsm = 0.0
    };
}
