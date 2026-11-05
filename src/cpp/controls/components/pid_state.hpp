#pragma once

#include "core/data_fields.hpp"

namespace apogee
{
	// Runtime data for a PID controller.
	struct PIDState
	{
		static constexpr auto data_fields()
		{
			return std::tuple{};
		}
	};
}
