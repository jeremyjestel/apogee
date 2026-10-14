#pragma once

#include "core/kinematic_state.hpp"

namespace apogee
{
	// Advances one kinematic state by a single explicit-Euler time step.
	void advance_orbit(KinematicStateECI &state, double dt_s);

} // namespace apogee
