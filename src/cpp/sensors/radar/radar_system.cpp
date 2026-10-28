#include "sensors/radar/radar_system.hpp"
#include "math/constants.hpp"
#include "math/geometry/boresight_angle.hpp"
#include "math/geometry/los_occluded.hpp"

#include "sensors/radar/models/radar_processing.hpp"
#include "sensors/radar/models/radar_returns.hpp"

namespace apogee
{
	void radar_system(std::vector<Entity> &entities, std::mt19937& rng)
	{
        for (auto& entity : entities){
			for (auto& radar : entity.radars){
				radar.targets.clear();
				const RadarParams& params = radar.params;
				RadarState& state = radar.state;

						// Add the check for earth occlusion

				if (!radar.state.enabled)
                	continue;
				if (entity.motion_type == MotionType::EarthFixed)
				{radar.pointing_vec = entity.kinematics.pos_m;}
				else {radar.pointing_vec = entity.kinematics.vel_mps;}
        		for (auto& target : entities){
					if (target.id == entity.id ||
						(target.kinematics.pos_m - entity.kinematics.pos_m).squaredNorm() == 0.0) {
						continue;
					}
					if (!has_line_of_sight(entity.kinematics.pos_m,target.kinematics.pos_m,		constants::earth_radius_m)) {
						continue;
					}
					if (target.motion_type == MotionType::FreeFlight){
						Vec3 radar_to_target_vec = target.kinematics.pos_m - entity.kinematics.pos_m;
						double boresight_angle_deg = boresight_angle(radar.pointing_vec, radar_to_target_vec);
						if (boresight_angle_deg <= 180){ // assumption made here of hemispherical area of awareness
							radar.targets.push_back(target);
						}
					}
					
				}

				//Do I split these here or have a separate radar processing function, seems like depth not needed
				generate_returns(entity.kinematics, radar, radar.targets, rng);
				// process_returns(entity.kinematics, radar, radar.targets);
				// detect_targets(radar); // gating? does this happen else where? mnight want association to be its own subsystem or subset of tracking
				// provide_measurements(radar); // entity.measurements so tracker subsystem can access that for sensor fusion, probably will do separate trackers for each sensor but eventually a combiner




			}
				





				

				

			
		}
	}

} // namespace apogee
