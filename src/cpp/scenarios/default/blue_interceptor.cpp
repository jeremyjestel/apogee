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
        // Place the interceptor about 20 km above Earth near the engagement.
        .initial_kinematics = KinematicState{
            Vec3{6'391'000.0, -30'000.0, 0.0},
            Vec3{100.0, 1'200.0, 600.0},
            Vec3{-9.76, 0.046, 0.0}
        },
        .radar_signature_dbsm = 0.0
    };
}
