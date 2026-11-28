#pragma once

#include <vector>

namespace apogee
{
	struct Entity;

	// Fuse all sensors' detections into each observer's single track collection.
	// Runs after sensing and before guidance; sensor components do not own tracks.
	// Scaffold only: estimates remain unchanged until the stages are implemented.
	void estimate(std::vector<Entity> &entities, double sim_time_s);
}
