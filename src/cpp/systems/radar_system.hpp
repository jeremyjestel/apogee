#pragma once

#include <optional>

#include "core/entity.hpp"
#include "systems/range_doppler_map.hpp"

// Run the radar processing chain for one radar-target pair.
std::optional<RangePulseProduct> radar_update(
    Entity& radar,
    const Entity& target
);
