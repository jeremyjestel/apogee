#pragma once

#include <vector>

namespace apogee
{
	struct Entity;

	// Update per-entity control outputs before the motion system runs.
	void controls_update(std::vector<Entity> &entities, double dt_s);
}
