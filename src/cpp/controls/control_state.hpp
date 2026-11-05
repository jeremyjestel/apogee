#pragma once

#include "core/data_fields.hpp"
#include "math/types.hpp"

namespace apogee
{
	// Per-entity runtime data for control models and their outputs.
	struct ControlState
	{
		Vec3 accel_actual = Vec3::Zero();
		double time_constant_s = 0.1;

		static constexpr auto data_fields()
		{
			return std::tuple{
				data_field("accel_actual", &ControlState::accel_actual, "Actual acceleration", "m/s^2", "eci"),
				data_field("time_constant_s", &ControlState::time_constant_s, "Control time constant", "s") };
		}
	};
}
