#pragma once

#include "core/kinematic_state.hpp"
#include "core/radar_module.hpp"

// Update the radar module from the current radar and target kinematics.
void range_doppler_map(
    RadarModule& radar,
    const KinematicState& radar_kinematics,
    const KinematicState& target_kinematics
);
