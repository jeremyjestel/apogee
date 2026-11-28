#pragma once

#include <vector>

#include "core/data_fields.hpp"
#include "estimation/ekf_params.hpp"
#include "estimation/ekf_state.hpp"
#include "sensors/detection.hpp"

namespace apogee
{
	// One shared track collection for an observing entity and all its sensors.
	struct BeliefState
	{
		bool enabled = true;
		EkfParams params;
		// Track identity is local to this estimator, independent of sensor identity.
		std::vector<EkfState> tracks;
		// Every sensor appends here. Only estimation associates detections to tracks.
		// Preserve unprocessed detections until the estimator can consume them.
		// This transient inbox is not registered as a persistent logged component.
		std::vector<Detection> pending_detections;

		static constexpr auto data_fields()
		{
			return std::tuple{
				data_field("enabled", &BeliefState::enabled, "Enabled"),
				data_field("params", &BeliefState::params, "Parameters"),
				data_field("tracks", &BeliefState::tracks, "Tracks") };
		}
	};
}
