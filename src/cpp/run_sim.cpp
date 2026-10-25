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
#include "motion/motion_system.hpp"

namespace apogee
{
	Result run_sim(const ScenarioParams &params)
	{
		int seed = 42; // might actually create a world struct or class for seeds, generators, timing
		std::mt19937 rng{seed};
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
		Logger logger(entities, result);

		// Log the current state, advance motion, then update radar once per timestep.
		for (std::size_t step = 0; static_cast<double>(step) * dt_s < duration_s; ++step)
		{
			const double sim_time_s = static_cast<double>(step) * dt_s;


			sense(entities, rng);
			estimate(entities);
			guidance_commands(entities);
			controls_update(entities);
			logger.log(entities, sim_time_s);
			motion_step(entities, dt_s);

		}
		// // Run non-timestep analysis after the scenario history is complete.
		// add_snr_range_curve(radar_entity.radar->p,
		// 	radar_target.radar_signature_dbsm,
		// 	params.radar_analysis,
		// 	radar_entity.id,
		// 	result);

		return result;
	}

} // namespace apogee
