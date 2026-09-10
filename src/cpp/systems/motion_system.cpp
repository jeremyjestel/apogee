#include "motion_system.hpp"

void advance_kinematics(KinematicState& state, double dt_s)
{
    // Advance position using the velocity at the start of the time step.
    state.pos_m += state.vel_mps * dt_s;

    // Advance velocity using the constant acceleration for this time step.
    state.vel_mps += state.accel_mps2 * dt_s;
}
