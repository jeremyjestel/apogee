#pragma once

#include "estimation/ekf_state.hpp"
#include "sensors/detection.hpp"

namespace apogee
{
	enum class EkfUpdateStatus
	{
		NotImplemented,
		Updated
	};

	// Correct a shared track already initialized and predicted to detection.time_s.
	// h/H depend on detection.kind and sensor pose; R is detection.covariance.
	// Until implemented, returns NotImplemented without changing the track.
	EkfUpdateStatus update_track(EkfState &track, const Detection &detection);

} // namespace apogee
