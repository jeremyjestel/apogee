#pragma once
#include <string>
#include "core/kinematic_state.hpp"

struct Entity
{
    int id = 0;
    std::string key;
    std::string name;
    std::string type;
    std::string team;
    KinematicState kinematics;
};
