#pragma once

#include "core/result.hpp"
#include "core/scenario_params.hpp"

// Execute one fresh simulation from the supplied scenario snapshot.
Result run_sim(const ScenarioParams& params);
