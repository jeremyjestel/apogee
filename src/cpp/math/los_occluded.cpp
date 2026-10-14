#include "los_occluded.hpp"
#include <cmath> 
#include <algorithm>


namespace apogee {

    bool has_line_of_sight(
        const Vec3& pos_a,
        const Vec3& pos_b,
        double earth_radius_m
    )
    {
        Vec3 d = pos_b - pos_a;
        int t = -1 * pos_a.dot(pos_b) / std::pow(d.norm(), 2);
        int t_clamped = std::clamp(t, 0, 1);

        Vec3 minima = pos_a + d * t;

        if (minima.norm() > earth_radius_m) {
            return true;
        }
        return false;
        
    }

}