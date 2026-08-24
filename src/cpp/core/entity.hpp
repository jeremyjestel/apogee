#pragma once

#include <optional>
#include <string>

#include "core/kinematic_state.hpp"
#include "core/radar_module.hpp"

// An Entity contains the mutable component data used by systems during a run.
struct Entity
{
    int id = 0;
    std::string key;
    std::string display_name;
    std::string type;
    std::string team;
    KinematicState kinematics;
    // Optional components let only radar-equipped entities carry radar runtime data.
    std::optional<RadarModule> radar;
    double radar_signature_dbsm = 0.0;
};
