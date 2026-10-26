#pragma once

#include "math/types.hpp"

namespace apogee
{
    Vec3 drag(
        Vec3 vel_m,
        double mass,
        double drag_coeff,
        double area_m2);
}