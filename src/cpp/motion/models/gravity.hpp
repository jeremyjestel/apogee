#pragma once

#include "motion/kinematic_state.hpp"

namespace apogee
{
	// Advances one kinematic state by a single explicit-Euler time step.
	Vec3 gravity(Vec3 pos_m, double mass);

} // namespace apogee
