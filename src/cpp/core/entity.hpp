#pragma once

#include <string>
#include <vector>

#include "core/data_fields.hpp"
#include "motion/kinematic_state.hpp"
#include "sensors/radar/radar_component.hpp"

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
		MotionType motion_type = MotionType::FreeFlight;
		double mass = 1.0;
		double drag_coeff = 0.0;
		double area_m2 = 0.0;
		std::vector<RadarComponent> radars;
		double radar_signature_dbsm = 0.0;

		static constexpr auto data_fields()
		{
			return std::tuple{ data_field("id", &Entity::id, "ID"),
				data_field("key", &Entity::key, "Key"),
				data_field("display_name", &Entity::display_name, "Display name"),
				data_field("type", &Entity::type, "Type"),
				data_field("team", &Entity::team, "Team"),
				data_field("kinematics", &Entity::kinematics, "Kinematics"),
				data_field("motion_type", &Entity::motion_type, "Motion type"),
				data_field("mass", &Entity::mass, "Mass", "kg"),
				data_field("drag_coeff", &Entity::drag_coeff, "Drag coefficient"),
				data_field("area_m2", &Entity::area_m2, "Area", "m^2"),
				data_field("radars", &Entity::radars, "Radars"),
				data_field("radar_signature_dbsm", &Entity::radar_signature_dbsm, "Radar signature", "dBsm") };
		}
	};

} // namespace apogee
