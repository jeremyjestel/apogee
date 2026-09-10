#pragma once

#include "core/kinematic_state.hpp"

// Keep a ground-fixed entity attached to the naturally rotating Earth.
void advance_ground(KinematicState& state, double dt_s);
