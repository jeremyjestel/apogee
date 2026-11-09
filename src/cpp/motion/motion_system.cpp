#include "motion/motion_system.hpp"
#include <vector>
#include "core/entity.hpp"
#include "math/constants.hpp"
#include "motion/models/gravity.hpp"
#include "motion/models/ground_motion.hpp"
#include "motion/models/drag.hpp"
#include "motion/models/thrust.hpp"
#include <algorithm> 

namespace apogee {

    void motion_step(std::vector<Entity> &entities, double dt){

        for (auto& entity : entities){
            if (!entity.active) continue;
            for (auto& other_entity : entities){
                Vec3 diff_pos = (entity.kinematics.pos_m - other_entity.kinematics.pos_m).norm();
                if (diff_pos > std::max(entity.blast_radius, entity.size_radius)){
                    entity.active = false;
                    other_entity.active = false;
                }
            }
            KinematicStateECI& state = entity.kinematics;

            if (entity.motion_type == MotionType::EarthFixed){ //When should update occur
                advance_ground(state, dt);
                state.vel_mps = constants::omega_earth.cross(state.pos_m);
                state.accel_mps2 = constants::omega_earth.cross(state.vel_mps);
            } 
            else if (entity.motion_type == MotionType::FreeFlight){
                Vec3 accel_sum = Vec3::Zero();

                accel_sum += gravity(state.pos_m, entity.mass);
                // accel_sum += drag(state.vel_mps, entity.mass, entity.drag_coeff, entity.area_m2); //Should return 0 if velocity 0, needs an atmospheric part
                // accel_sum += thrust(state.pos_m, entity.mass);
                accel_sum += entity.controls.accel_actual;

                state.accel_mps2 = accel_sum;

                state.vel_mps += state.accel_mps2 * dt;
                state.pos_m += state.vel_mps * dt;
            }
        }
    }
}
