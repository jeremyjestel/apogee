#pragma once

#include <vector>

#include "core/entity.hpp"
#include "core/result.hpp"

// Creates the entity metadata and empty time-series layout used by each log step.
void initialize_entity_state_logging(const std::vector<Entity>& entities,
                                     Result& result);

// Appends one timestamp and one kinematic sample for every entity.
void log_entity_states(const std::vector<Entity>& entities,
                       double time_s,
                       Result& result);
