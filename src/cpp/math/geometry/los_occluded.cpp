#include "math/geometry/los_occluded.hpp"
#include <cmath> 
#include <algorithm>
#include "math/constants.hpp"

namespace apogee {

    bool has_line_of_sight(
        const Vec3& pos_a,
        const Vec3& pos_b
    )
    {
        const Vec3 d = pos_b - pos_a;
        const double distance_squared = d.squaredNorm();
        const double t = distance_squared > 0.0
            ? std::clamp(-pos_a.dot(d) / distance_squared, 0.0, 1.0) : 0.0;
        const Vec3 closest = pos_a + d * t;
        return closest.squaredNorm() >= constants::earth_radius_m * constants::earth_radius_m;
        
    }

}
