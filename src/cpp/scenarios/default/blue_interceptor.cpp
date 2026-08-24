#include "scenarios/default/entities.hpp"

EntityDefinition make_blue_interceptor_definition()
{
    // This factory is the single home for Blue Interceptor's scenario-specific defaults.
    return EntityDefinition{
        .id = 4,
        .key = "blue_interceptor",
        .display_name = "Blue Interceptor",
        .type = "interceptor",
        .team = "blue",
        .initial_kinematics = KinematicState{
            Vec3{500.0, -500.0, 100.0},
            Vec3{-25.0, 40.0, 15.0},
            Vec3{2.0, 3.0, -1.0}
        },
        .radar_signature_dbsm = 0.0
    };
}
