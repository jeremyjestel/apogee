#pragma once
#include <vector>
#include "core/entity.hpp"
#include "core/constants.hpp"
#include "motion/models/gravity.hpp"


namespace apogee {

    inline void motion_step(std::vector<Entity> &entities, double dt){

        for (auto& entity : entities){
            KinematicStateECI& state = entity.kinematic_state;

            if (entity.motion_type == MotionType::EarthFixed){ //When should update occur
                state.pos_m = earth_rotation(state.pos_m, dt);
                state.vel_mps = constants::omega_earth.cross(state.pos_m);
                state.accel_mps2 = constants::omega_earth.cross(state.vel_mps);
            } 
            else if (entity.motion_type == MotionType::FreeFlight){
                Vec3 accel_sum = Vec3::Zero();

                accel_sum += gravity(state.pos_m, entity.mass);
                accel_sum += drag(state, entity.mass entity.drag_coeff); //Should return 0 if velocity 0, needs an atmospheric part
                accel_sum += thrust(state); // Will ahve to decide if this calls controls api or controls updates motio

                state.accel_mps2 = accel_sum;

                state.vel_mps += state.accel_mps2 * dt;
                state.pos_m += state.vel_mps * dt;
            }
        }
    }
}
