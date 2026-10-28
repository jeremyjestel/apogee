#include "motion/models/thrust.hpp"
#include "math/constants.hpp"

namespace apogee
{
	Vec3 thrust(Vec3 pos_m, double mass){
        // Vec3 F_thrust = Vec3::Zero(); // for now thrust will be zero
        // Vec3 accel_thrust = F_thrust / mass;

		const double radius_m = pos_m.norm();
		Vec3 F_thrust = pos_m * (-constants::earth_mu_m3_s2 / (radius_m * radius_m * radius_m));
		Vec3 accel_thrust = -1 * F_thrust / mass;
		return accel_thrust;
    }

}
