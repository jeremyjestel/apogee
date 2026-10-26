#pragma once

#include <random>
#include <vector>

#include "core/entity.hpp"

namespace apogee
{
	// Run the radar processing chain for each radar component.
	void radar_system(std::vector<Entity> &entities, std::mt19937 &rng);

} // namespace apogee
