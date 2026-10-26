#include "motion/models/drag.hpp"
#include "math/constants.hpp"
#include <cmath>

namespace apogee
{
	Vec3 drag(Vec3 vel_m, double mass, double drag_coeff, double area_m2)
	{
		const double velocity_mps = vel_m.norm();
		Vec3 F_drag = -.6125 * velocity_mps * vel_m * drag_coeff * area_m2;
        Vec3 accel_drag = F_drag / mass;
		return accel_drag;
	}

} // namespace apogee
