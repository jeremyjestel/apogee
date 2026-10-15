#pragma once

#include <string>
#include <vector>

#include "core/entity.hpp"
#include "scenarios/scenario_params.hpp"

namespace apogee
{
	std::vector<Entity> instantiate_entities(const ScenarioParams &params);
	void initialize_pursuits(const ScenarioParams &params, std::vector<Entity> &entities);
	Entity &require_entity(std::vector<Entity> &entities, const std::string &key);
	void advance_entities(std::vector<Entity> &entities, double dt_s);
}
