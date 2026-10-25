#include "sensors/radar/radar_system.hpp"
#include "math/geometry/boresight_angle.hpp"
#include "math/geometry/los_occluded.hpp"

#include "sensors/radar/models/range_doppler_map.hpp"

namespace apogee
{
	void radar_system(std::vector<Entity> &entities &target, std::mt19937& rng)
	{
        for (auto& entity : entities){
			for (auto& radar : entity.radars){
				const RadarParams& params = radar.params;
				RadarState& state = radar.state;

						// Add the check for earth occlusion

				if (!radar.state.enabled)
                	continue;
				if (entity.motion_type == MotionType::GroundFixed)
				{Vec3 radar.pointing_vec = entity.kinematics.pos_m;}
				else {Vec3 radar.pointing_vec = entity.kinematics.vel_mps;}
        		for (auto& target : entities){
					if !has_line_of_sight(entity.kinematics.pos_m,target.kinematics.pos_m,constants::) {
						continue;
					}
					if (target.motion_type == MotionType::FreeFlight){
						Vec3 radar_to_target_vec = target.kinematics.pos_m - entity.pos_m;
						double boresight_angle_deg = boresight_angle(radar.pointing_vec, radar_to_target_vec);
						if (boresight_angle_deg <= 180){
							std::vector<Entity> radar.targets.push_back(target); 
						}
					}
					
				}

				//Do I split these here or have a separate radar processing function, seems like depth not needed
				generate_returns(entity.kinematics.pos_m, radar, targets);
				process_signals(radars);
				detect_targets(radars); // gating? does this happen else where? mnight want association to be its own subsystem or subset of tracking
				provide_measurements(radars); // entity.measurements so tracker subsystem can access that for sensor fusion, probably will do separate trackers for each sensor but eventually a combiner




			}
				





				

				

			
		}
	}

} // namespace apogee
