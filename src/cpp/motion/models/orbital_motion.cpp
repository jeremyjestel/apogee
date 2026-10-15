#include "motion/models/orbital_motion.hpp"
#include "core/constants.hpp"

namespace apogee
{
	void advance_orbit(KinematicStateECI &state, double dt_s)
	{
		const double radius_m = state.pos_m.norm();

		state.accel_mps2 = state.pos_m * (-constants::earth_mu_m3_s2 / (radius_m * radius_m * radius_m));

		// Advance velocity using the orbital acceleration for this time step.
		state.vel_mps += state.accel_mps2 * dt_s;

		// Advance position using the velocity from the start of the time step.
		state.pos_m += state.vel_mps * dt_s;
	}

} // namespace apogee
