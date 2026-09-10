#include "motion_system.hpp"
#include <cmath>
#include <complex>
#include "core/constants.hpp"
#include <iostream>


void advance_orbit(KinematicState& state, double dt_s)
{
    const double radius_m = std::hypot(
        state.pos_m.x,
        state.pos_m.y,
        state.pos_m.z
    );

    state.accel_mps2 = state.pos_m * (-constants::earth_mu_m3_s2 / (radius_m * radius_m * radius_m));

    // Advance velocity using the orbital acceleration for this time step.
    state.vel_mps += state.accel_mps2 * dt_s;

    // Advance position using the velocity from the start of the time step.
    state.pos_m += state.vel_mps * dt_s;



}
