#pragma once

#include "core/data_fields.hpp"
#include "math/types.hpp"

namespace apogee
{
	struct EkfParams
	{
		// Q: discrete process covariance for one prediction interval.
		// TODO: derive this from the selected motion model and elapsed time.
		Mat6 process_noise = Mat6::Zero();
		// Measurement noise R is supplied by each Detection, not shared by sensors.

		static constexpr auto data_fields()
		{
			return std::tuple{
				data_field("process_noise", &EkfParams::process_noise, "Process noise covariance") };
		}
	};

} // namespace apogee
