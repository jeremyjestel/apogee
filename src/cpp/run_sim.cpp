#include "run_sim.hpp"

#include <cstddef>
#include <optional>
#include <utility>
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
    const LoggingLayout logging_layout = initialize_entity_state_logging(
        entities,
        result
    );
    std::optional<RangePulseProduct> latest_range_pulse;

    // Log the current state, advance motion, then update radar once per timestep.
    for (std::size_t step = 0;
         static_cast<double>(step) * dt_s < duration_s;
         ++step)
    {
        const double sim_time_s = static_cast<double>(step) * dt_s;
        log_entity_states(entities, logging_layout, sim_time_s, result);

        for (Entity& entity : entities)
        {
            update_kinematics(entity.kinematics, dt_s);
        }

        if (auto range_pulse = radar_update(radar_entity, radar_target))
        {
            latest_range_pulse = std::move(*range_pulse);
        }
    }

    // Convert the most recent detectable product into one static analysis grid.
    if (latest_range_pulse)
    {
        result.grids.push_back(make_noisy_range_doppler_grid(
            *latest_range_pulse,
            radar_entity.radar->p,
            radar_entity.id
        ));
    }

    // A snapshot represents labeled values directly, without a synthetic sample axis.
    result.snapshots.push_back(Snapshot{
        .entity_id = radar_entity.id,
        .system = "radar",
        .key = "state",
        .name = "State Variables",
        .metrics = {
            Metric{
                .key = "target_range",
                .name = "Target Range",
                .unit = "m",
                .value = radar_entity.radar->state.target_range_m
            },
            Metric{
                .key = "target_velocity",
                .name = "Target Velocity",
                .unit = "m/s",
                .value = radar_entity.radar->state.target_vel_mps
            },
            Metric{
                .key = "signal_to_noise",
                .name = "Signal-to-Noise Ratio",
                .unit = "dB",
                .value = radar_entity.radar->state.signal_to_noise_db
            },
            Metric{
                .key = "pulse_width",
                .name = "Pulse Width",
                .unit = "us",
                .value = radar_entity.radar->p.pw_us
            },
            Metric{
                .key = "pulse_repetition_interval",
                .name = "Pulse Repetition Interval",
                .unit = "us",
                .value = radar_entity.radar->p.pri_us
            }
        },
        .presentation = Presentation{
            .order = 30
        }
    });

    // Run non-timestep analysis after the scenario history is complete.
    radar_range_analysis(
        radar_entity.radar->p,
        radar_target.radar_signature_dbsm,
        params.radar_analysis,
        radar_entity.id,
        result
    );

    return result;
}
