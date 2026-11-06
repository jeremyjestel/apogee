#include "guidance/models/point_nav.hpp"

#include <cmath>
#include "math/geometry/los_occluded.hpp"

#include "core/entity.hpp"
#include "math/constants.hpp"

namespace apogee
{
	Vec3 point_nav(const Entity &entity, const Entity &target)
	{
        Vec3 r_hat_ent = entity.kinematics.pos_m / entity.kinematics.pos_m.norm();
        Vec3 closest_point = target.kinematics.pos_m;
        while (true){
            Vec3 r_hat_targ = closest_point / closest_point.norm();
            Vec3 r_hat_mid = (r_hat_ent + r_hat_targ) / (r_hat_ent + r_hat_targ).norm();
            Vec3 waypoint = (constants::earth_radius_m + 1.05 * constants::altitude_minimum_m) * r_hat_mid;

            if (has_line_of_sight(entity.kinematics.pos_m, waypoint)){
                Vec3 waypoint_dir = waypoint - entity.kinematics.pos_m;
                Vec3 waypoint_dir_norm = waypoint_dir / waypoint_dir.norm();
                Vec3 vel_desired = entity.kinematics.vel_mps.norm() * waypoint_dir_norm;
                Vec3 accel_cmd = entity.guidance.guidance_gain * (vel_desired - entity.kinematics.vel_mps);

                return accel_cmd;     
            }
            else{
                closest_point = waypoint;
            }
            
        }

	}
}
