#pragma once

#include "core/data_fields.hpp"
#include "math/types.hpp"

namespace apogee
{
	// One fused, locally identified track updated by any associated sensor.
	// The state is sensor-independent and separate from true entity kinematics.
	struct EkfState
	{
		int track_id = 0;
		// ECI [x, y, z, vx, vy, vz], in metres and metres/second.
		Vec6 state = Vec6::Zero();
		// Covariance follows the same position/velocity ordering and units.
		Mat6 covariance = Mat6::Zero();
		double time_s = 0.0;
		// Zero-filled storage is not a valid estimate until initialized.
		bool initialized = false;

		static constexpr auto data_fields()
		{
			return std::tuple{
				data_field("track_id", &EkfState::track_id, "Track ID"),
				data_field("state", &EkfState::state, "Position/velocity state", "", "eci"),
				data_field("covariance", &EkfState::covariance, "Covariance"),
				data_field("time_s", &EkfState::time_s, "Estimate time", "s"),
				data_field("initialized", &EkfState::initialized, "Initialized") };
		}
	};

} // namespace apogee
