#pragma once
#include <string>
#include "components/kinematic_state.hpp"

struct Entity
{
    int id = 0;
    std::string key;
    std::string name;
    std::string type;
    std::string team;
    KinematicState kinematics;
};
