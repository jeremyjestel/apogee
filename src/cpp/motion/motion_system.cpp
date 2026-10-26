#include "motion/motion_system.hpp"
#include <vector>
#include "core/entity.hpp"
#include "math/constants.hpp"
#include "motion/models/gravity.hpp"
#include "motion/models/ground_motion.hpp"
#include "motion/models/drag.hpp"
#include "motion/models/thrust.hpp"


namespace apogee {

    void motion_step(std::vector<Entity> &entities, double dt){

        for (auto& entity : entities){
            KinematicStateECI& state = entity.kinematics;

            if (entity.motion_type == MotionType::EarthFixed){ //When should update occur
                advance_ground(state, dt);
                state.vel_mps = constants::omega_earth.cross(state.pos_m);
                state.accel_mps2 = constants::omega_earth.cross(state.vel_mps);
            } 
            else if (entity.motion_type == MotionType::FreeFlight){
                Vec3 accel_sum = Vec3::Zero();

                accel_sum += gravity(state.pos_m, entity.mass);
                accel_sum += drag(state.vel_mps, entity.mass, entity.drag_coeff, entity.area_m2); //Should return 0 if velocity 0, needs an atmospheric part
                accel_sum += thrust(entity.mass); // Will ahve to decide if this calls controls api or controls updates motio

                state.accel_mps2 = accel_sum;

                state.vel_mps += state.accel_mps2 * dt;
                state.pos_m += state.vel_mps * dt;
            }
        }
    }
}
