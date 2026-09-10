#include "systems/ground_motion.hpp"

#include <cmath>

#include "core/constants.hpp"

void advance_ground(KinematicState& state, double dt_s)
{
    const double omega = constants::earth_rotation_rate_rad_s;
    const double angle_rad = omega * dt_s;
    const double cosine = std::cos(angle_rad);
    const double sine = std::sin(angle_rad);
    const double x = cosine * state.pos_m.x - sine * state.pos_m.y;
    const double y = sine * state.pos_m.x + cosine * state.pos_m.y;

    state.pos_m = Vec3{x, y, state.pos_m.z};
    state.vel_mps = Vec3{-omega * y, omega * x, 0.0};
    state.accel_mps2 = Vec3{
        -omega * omega * x,
        -omega * omega * y,
        0.0
    };
}
