#include "run_sim.hpp"

#include <cstddef>
#include <vector>

#include "analysis/radar_range.hpp"
#include "core/entity.hpp"
#include "core/entity_factory.hpp"
#include "core/find_entity.hpp"
#include "logging.hpp"
#include "systems/motion_system.hpp"
#include "systems/radar_system.hpp"

Result run_sim(const ScenarioParams& params)
{
    const double dt_s = params.simulation.dt_s;
    const double duration_s = params.simulation.duration_s;

    // Recreate all runtime entities so state starts fresh on every run.
    std::vector<Entity> entities;
    entities.reserve(params.entities.size());
    for (const EntityDefinition& definition : params.entities)
    {
        entities.push_back(instantiate_entity(definition));
    }

    // Select the fixed radar engagement by the entities' stable identities.
    Entity& radar_entity = find_entity(entities, "blue_radar");
    Entity& radar_target = find_entity(entities, "red_missile");

    // Create the result series before the timestep loop starts appending values.
    Result result;
    initialize_entity_state_logging(entities, result);

    // Log the current state, advance motion, then update radar once per timestep.
    for (std::size_t step = 0;
         static_cast<double>(step) * dt_s < duration_s;
         ++step)
    {
        const double sim_time_s = static_cast<double>(step) * dt_s;
        log_entity_states(entities, sim_time_s, result);

        for (Entity& entity : entities)
        {
            update_kinematics(entity.kinematics, dt_s);
        }

        radar_update(radar_entity, radar_target);
    }

    // Run non-timestep analysis after the scenario history is complete.
    radar_range_analysis(
        radar_entity.radar->params,
        radar_target.radar_signature_dbsm,
        params.radar_analysis,
        radar_entity.id,
        result
    );

    return result;
}
