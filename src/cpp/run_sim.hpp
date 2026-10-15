#pragma once

#include "core/result.hpp"
#include "scenarios/scenario_params.hpp"

namespace apogee
{
	// Execute one fresh simulation from the supplied scenario snapshot.
	Result run_sim(const ScenarioParams &params);

} // namespace apogee
