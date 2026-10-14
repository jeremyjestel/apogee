#pragma once

#include <vector>

#include "core/entity_definition.hpp"
#include "params.hpp"

namespace apogee
{
	// ScenarioParams groups every editable input needed to construct one simulation run.
	struct ScenarioParams
	{
		SimulationParams simulation;
		RadarAnalysisParams radar_analysis;
		std::vector<EntityDefinition> entities;
	};

} // namespace apogee
