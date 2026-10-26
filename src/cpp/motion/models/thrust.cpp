#include "motion/models/thrust.hpp"
#include "math/constants.hpp"

namespace apogee
{
	Vec3 thrust(double mass){
        Vec3 F_thrust = Vec3::Zero(); // for now thrust will be zero
        Vec3 accel_thrust = F_thrust / mass;

        return accel_thrust;
    }

}
