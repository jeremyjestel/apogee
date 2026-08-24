#include "scenarios/default/entities.hpp"

EntityDefinition make_blue_satellite_definition()
{
    // This factory is the single home for Blue Satellite's scenario-specific defaults.
    return EntityDefinition{
        .id = 2,
        .key = "blue_satellite",
        .display_name = "Blue Satellite",
        .type = "satellite",
        .team = "blue",
        .initial_kinematics = KinematicState{
            Vec3{1000.0, 2000.0, 3000.0},
            Vec3{10.0, 20.0, 30.0},
            Vec3{1.0, 2.0, 3.0}
        },
        .radar_signature_dbsm = 0.0
    };
}
