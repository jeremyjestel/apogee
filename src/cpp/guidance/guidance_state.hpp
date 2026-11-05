#pragma once

#include <cstddef>
#include <optional>

#include "core/data_fields.hpp"
#include "math/types.hpp"

namespace apogee
{
	// Per-entity runtime data for guidance models and their output commands.
	struct GuidanceState
	{
		std::optional<std::size_t> target_index;
		Vec3 accel_command = Vec3::Zero();

		static constexpr auto data_fields()
		{
			return std::tuple{
				data_field("accel_command", &GuidanceState::accel_command, "Acceleration command", "m/s^2", "eci") };
		}
	};
}
