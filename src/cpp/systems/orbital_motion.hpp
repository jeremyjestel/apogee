#pragma once

#include "core/kinematic_state.hpp"

// Advances one kinematic state by a single explicit-Euler time step.
void advance_orbit(KinematicState& state, double dt_s);
