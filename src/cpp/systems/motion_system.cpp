#include "motion_system.hpp"

void advance_kinematics(KinematicState& state, double dt_s)
{
    // Advance position using the velocity at the start of the time step.
    state.pos_m.x += state.vel_mps.x * dt_s;
    state.pos_m.y += state.vel_mps.y * dt_s;
    state.pos_m.z += state.vel_mps.z * dt_s;

    // Advance velocity using the constant acceleration for this time step.
    state.vel_mps.x += state.accel_mps2.x * dt_s;
    state.vel_mps.y += state.accel_mps2.y * dt_s;
    state.vel_mps.z += state.accel_mps2.z * dt_s;
}
