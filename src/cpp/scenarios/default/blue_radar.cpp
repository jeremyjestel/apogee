#include "scenarios/default/entities.hpp"

#include "params.hpp"

EntityDefinition make_blue_radar_definition()
{
    // This factory is the single home for Blue Radar's scenario-specific defaults.
    return EntityDefinition{
        .id = 1,
        .key = "blue_radar",
        .display_name = "Blue Radar",
        .type = "radar",
        .team = "blue",
        // Place the ground radar on the equator with Earth's ECI rotation motion.
        .initial_kinematics = KinematicState{
            Vec3{6'371'000.0, 0.0, 0.0},
            Vec3{0.0, 464.6, 0.0},
            Vec3{-0.0339, 0.0, 0.0}
        },
        // Supplying RadarParams attaches a radar component when the entity is created.
        .radar = RadarParams{
            .frequency_hz = 5e9,
            .power_dbw = 50.0,
            .tx_gain_db = 35.0,
            .rx_gain_db = 20.0,
            .noise_figure_db = 3.0,
            .bandwidth_hz = 1e6,
            .system_loss_db = 3.0,
            .pulse_width_us = 1.0,
            .pri_us = 3000.0
        },
        .radar_signature_dbsm = 0.0
    };
}
