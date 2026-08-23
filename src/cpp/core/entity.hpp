#pragma once

#include <optional>
#include <string>

#include "core/kinematic_state.hpp"
#include "core/radar_module.hpp"

struct Entity
{
    int id = 0;
    std::string key;
    std::string display_name;
    std::string type;
    std::string team;
    KinematicState kinematics;
    std::optional<RadarModule> radar;
};
