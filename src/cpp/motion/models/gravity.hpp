#pragma once

#include "math/types.hpp"

namespace apogee
{
	// Return the gravity model's acceleration contribution at an ECI position.
	Vec3 gravity(Vec3 pos_m, double mass);

} // namespace apogee
