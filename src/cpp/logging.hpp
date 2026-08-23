#pragma once

#include <vector>

#include "core/entity.hpp"
#include "core/result.hpp"

void initialize_entity_state_logging(const std::vector<Entity>& entities,
                                     Result& result);

void log_entity_states(const std::vector<Entity>& entities,
                       double time_s,
                       Result& result);
