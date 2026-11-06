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
        Vec3 d = pos_b - pos_a;
        int t = -1 * pos_a.dot(pos_b) / std::pow(d.norm(), 2);
        int t_clamped = std::clamp(t, 0, 1);

        Vec3 minima = pos_a + d * t;

        if (minima.norm() > constants::earth_radius_m) {
            return true;
        }
        return false;
        
    }

}
