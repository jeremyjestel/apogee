#pragma once

#include <optional>
#include <string>

#include "motion/kinematic_state.hpp"
#include "sensors/radar/radar_state.hpp"

namespace apogee
{
	// An Entity contains the mutable component data used by systems during a run.
	struct Entity
	{
		int id = 0;
		std::string key;
		std::string display_name;
		std::string type;
		std::string team;
		KinematicStateECI kinematics;    
		std::vector<RadarComponent> radars;
		double radar_signature_dbsm = 0.0;
	};

} // namespace apogee
