#include "motion_system.hpp"


void kinematic_update(Entity& entity, double dt_s)
{
    entity.kinematics.pos_m.x += entity.kinematics.vel_mps.x * dt_s;
    entity.kinematics.pos_m.y += entity.kinematics.vel_mps.y * dt_s;
    entity.kinematics.pos_m.z += entity.kinematics.vel_mps.z * dt_s;

    entity.kinematics.vel_mps.x += entity.kinematics.accel_mps2.x * dt_s;
    entity.kinematics.vel_mps.y += entity.kinematics.accel_mps2.y * dt_s;
    entity.kinematics.vel_mps.z += entity.kinematics.accel_mps2.z * dt_s;
}
