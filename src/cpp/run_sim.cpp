#include "run_sim.hpp"

#include <cstddef>
#include <optional>
#include <utility>
#include <vector>

#include "analysis/radar_range.hpp"
#include "core/entity.hpp"
#include "logging/logging.hpp"
#include "simulation/scenario_runtime.hpp"
#include "sensors/radar/radar_system.hpp"

namespace apogee
{
	Result run_sim(const ScenarioParams &params)
	{
		const double dt_s = params.simulation.dt_s;
		const double duration_s = params.simulation.duration_s;

		// Recreate all runtime entities so state starts fresh on every run.
		std::vector<Entity> entities = instantiate_entities(params);
		// Aim pursuit entities once at their targets' initial positions.
		initialize_pursuits(params, entities);

		// Select the fixed radar engagement by the entities' stable identities.
		Entity &radar_entity = require_entity(entities, "blue_radar");
		Entity &radar_target = require_entity(entities, "red_missile");

		// Create the result series before the timestep loop starts appending values.
		Result result;
		const LoggingLayout logging_layout = initialize_entity_state_logging(entities, result);
		std::optional<GridSeries2D> range_doppler_history;
		MetricTable radar_state_history =
			initialize_radar_state_logging(radar_entity.id, radar_entity.radar->p);

		// Log the current state, advance motion, then update radar once per timestep.
		for (std::size_t step = 0; static_cast<double>(step) * dt_s < duration_s; ++step)
		{
			const double sim_time_s = static_cast<double>(step) * dt_s;
			log_entity_states(entities, logging_layout, sim_time_s, result);

			advance_entities(entities, dt_s);

			auto range_pulse = update_radar(radar_entity, radar_target);
			log_radar_state(radar_entity.radar->state, sim_time_s, radar_state_history);

			if (range_pulse)
			{
				GridSeries2D frame = make_noisy_range_doppler_series(
					*range_pulse, radar_entity.radar->p, radar_entity.id, sim_time_s);
				if (!range_doppler_history)
				{
					range_doppler_history = std::move(frame);
				}
				else
				{
					range_doppler_history->time_axis.values.push_back(sim_time_s);
					range_doppler_history->values.insert(range_doppler_history->values.end(),
						frame.values.begin(),
						frame.values.end());
				}
			}
		}

		if (range_doppler_history)
		{
			result.grid_series.push_back(std::move(*range_doppler_history));
		}
		result.metric_tables.push_back(std::move(radar_state_history));

		// Run non-timestep analysis after the scenario history is complete.
		add_snr_range_curve(radar_entity.radar->p,
			radar_target.radar_signature_dbsm,
			params.radar_analysis,
			radar_entity.id,
			result);

		return result;
	}

} // namespace apogee
