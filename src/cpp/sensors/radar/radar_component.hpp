#pragma once

#include <string>
#include <vector>

#include "core/data_fields.hpp"
#include "math/types.hpp"
#include "params.hpp"
#include "sensors/radar/models/radar_state.hpp"

namespace apogee
{
	struct Entity;

	struct RadarComponent
	{
		std::string name;
		RadarParams params;
		RadarState state;
		Vec3 pointing_vec = Vec3::Zero();
		std::vector<Entity> targets;

		static constexpr auto data_fields()
		{
			return std::tuple{ data_field("name", &RadarComponent::name, "Name"),
				data_field("params", &RadarComponent::params, "Parameters"),
				data_field("state", &RadarComponent::state, "State"),
				data_field("pointing_vec", &RadarComponent::pointing_vec, "Pointing vector", "", "eci"),
				data_field("targets", &RadarComponent::targets, "Target IDs") };
		}
	};

} // namespace apogee
