#include "scenarios/default/entities.hpp"

#include "core/constants.hpp"

EntityDefinition make_red_missile_definition()
{
    // This factory is the single home for Red Missile's scenario-specific defaults.
    return EntityDefinition{
        .id = 3,
        .key = "red_missile",
        .display_name = "Red Missile",
        .type = "missile",
        .team = "red",
        // Place the missile roughly 100 km above the radar's side of Earth.
        .initial_kinematics = KinematicState{
            Vec3{constants::earth_mean_radius_m + 100'000.0, 50'000.0, 0.0},
            Vec3{0.0, 1'500.0, 250.0},
            Vec3{-9.52, -0.074, 0.0}
        },
        .radar_signature_dbsm = -10.0
    };
}
