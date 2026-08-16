#pragma once
#include "math/vec3.hpp"

struct KinematicState
{
    Vec3 pos_m;
    Vec3 vel_mps;
    Vec3 accel_mps2;
};