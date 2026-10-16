#pragma once

#include <cstddef>
#include <unordered_map>
#include <vector>

#include "core/entity.hpp"
#include "core/result.hpp"

namespace apogee
{
	// Creates the entity histories once, then records their current state each step.
	class Logger
	{
	  public:
		Logger(const std::vector<Entity> &entities, Result &result);

		// Log every registered entity at this time, even if the list is reordered.
		void log(const std::vector<Entity> &entities, double time_s);

	  private:
		struct EntitySeries
		{
			std::size_t position = 0;
			std::size_t velocity = 0;
			std::size_t acceleration = 0;
			std::size_t speed = 0;
		};

		Result &result_;
		std::size_t simulation_time_axis_;
		std::unordered_map<int, EntitySeries> entity_series_;
	};

	MetricTable initialize_radar_state_logging(int entity_id, const RadarParams &params);
	void log_radar_state(const RadarState &state, double time_s, MetricTable &table);

} // namespace apogee
