#pragma once

#include <cstddef>
#include <vector>

#include "core/entity.hpp"
#include "core/result.hpp"

namespace apogee
{
	struct EntityLoggingHandles
	{
		std::size_t position_series = 0;
		std::size_t velocity_series = 0;
		std::size_t acceleration_series = 0;
		std::size_t speed_series = 0;
	};

	struct LoggingLayout
	{
		std::size_t simulation_time_axis = 0;
		std::vector<EntityLoggingHandles> entities;
	};

	// Create result series and return stable handles used by each logging step.
	LoggingLayout initialize_entity_state_logging(
		const std::vector<Entity> &entities, Result &result);

	// Appends one timestamp and one kinematic sample for every entity.
	void log_entity_states(const std::vector<Entity> &entities,
		const LoggingLayout &layout,
		double time_s,
		Result &result);

	MetricTable initialize_radar_state_logging(int entity_id, const RadarParams &params);
	void log_radar_state(const RadarState &state, double time_s, MetricTable &table);

} // namespace apogee
