#include "scenarios/default/entities.hpp"

EntityDefinition make_red_missile_definition()
{
    // This factory is the single home for Red Missile's scenario-specific defaults.
    return EntityDefinition{
        .id = 3,
        .key = "red_missile",
        .display_name = "Red Missile",
        .type = "missile",
        .team = "red",
        .initial_kinematics = KinematicState{
            Vec3{-1000.0, -2000.0, 500.0},
            Vec3{100.0, 50.0, 25.0},
            Vec3{5.0, -2.0, 1.0}
        },
        .radar_signature_dbsm = -10.0
    };
}
