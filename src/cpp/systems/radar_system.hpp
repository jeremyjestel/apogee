#pragma once

#include "core/entity.hpp"

// Run the radar processing chain for one radar-target pair.
void radar_update(Entity& radar,
                  const Entity& target);
