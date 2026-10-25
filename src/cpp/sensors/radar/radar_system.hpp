#pragma once

#include <optional>

#include "core/entity.hpp"
#include "sensors/radar/models/range_doppler_map.hpp"

namespace apogee
{
	// Run the radar processing chain for one radar-target pair.
	std::optional<RangePulseProduct> update_radar(Entity &radar, const Entity &target, std::mt19937& rng);

} // namespace apogee
