#pragma once

#include <vector>
#include <random>

namespace apogee
{
	struct Entity;

	// Update per-entity guidance commands before the control system runs.
	void guidance_commands(std::vector<Entity> &entities, std::mt19937 &rng);
}
