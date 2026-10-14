#pragma once

#include "core/kinematic_state.hpp"

namespace apogee
{
	// Keep a ground-fixed entity attached to the naturally rotating Earth.
	void advance_ground(KinematicStateECI &state, double dt_s);

} // namespace apogee
