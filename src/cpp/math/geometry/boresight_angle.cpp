#include "math/geometry/boresight_angle.hpp"
#include <cmath>
#include "math/constants.hpp"
#include "math/types.hpp"

namespace apogee {
    double boresight_angle(Vec3 boresight, Vec3 target){

        double a_dot_b = boresight.dot(target);
        double boresight_norm = boresight.norm();
        double target_norm = target.norm();

        double radians = std::acos(a_dot_b / (boresight_norm * target_norm));
        double theta = radians * 180.0 / constants::pi;
        return theta;
    }
}
