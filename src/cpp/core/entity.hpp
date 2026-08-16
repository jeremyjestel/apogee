#pragma once
#include <string>
#include <optional>
#include "components/kinematic_state.hpp"

struct Entity
{
    int id;
    std::string name;
    KinematicState kinematics;

};