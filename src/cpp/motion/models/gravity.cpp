#include "motion/models/gravity.hpp"
#include "core/constants.hpp"

namespace apogee
{
	Vec3 gravity(Vec3 pos_m, double mass)
	{
		const double radius_m = pos_m.norm();
		Vec3 F_grav = pos_m * (-constants::earth_mu_m3_s2 / (radius_m * radius_m * radius_m));
		Vec3 accel_grav = F_grav / mass;
		return accel_grav;
	}

} // namespace apogee
