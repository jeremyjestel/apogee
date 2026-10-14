#pragma once

#include "math/types.hpp"

namespace apogee {

    bool has_line_of_sight(
        const Vec3& pos_a,
        const Vec3& pos_b,
        double earth_radius_m
    );

}