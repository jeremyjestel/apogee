#pragma once

#include <vector>

#include "core/entity.hpp"
#include "parameter/result.hpp"


void log_entity_states(
    const std::vector<Entity>& entities,
    double time_s,
    SimulationData3D& simulation_data
);
