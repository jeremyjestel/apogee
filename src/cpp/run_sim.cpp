#include "run_sim.hpp"

#include <algorithm>
#include <cstddef>
#include <optional>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

#include "analysis/radar_range.hpp"
#include "core/entity.hpp"
#include "logging.hpp"
#include "systems/motion_system.hpp"
#include "systems/radar_system.hpp"

namespace
{
Entity instantiate(const EntityDefinition& definition)
{
    Entity entity{
        .id = definition.id,
        .key = definition.key,
        .display_name = definition.display_name,
        .type = definition.type,
        .team = definition.team,
        .kinematics = definition.initial_kinematics,
        .radar_signature_dbsm = definition.radar_signature_dbsm
    };
    if (definition.radar)
    {
        entity.radar.emplace(*definition.radar);
    }
    return entity;
}

Entity& require_entity(std::vector<Entity>& entities, const std::string& key)
{
    const auto match = std::find_if(
        entities.begin(),
        entities.end(),
        [&](const Entity& entity) { return entity.key == key; }
    );
    if (match == entities.end())
    {
        throw std::invalid_argument("Scenario is missing entity: " + key);
    }
    return *match;
}
}

Result run_sim(const ScenarioParams& params)
{
    const double dt_s = params.simulation.dt_s;
    const double duration_s = params.simulation.duration_s;

    // Recreate all runtime entities so state starts fresh on every run.
    std::vector<Entity> entities;
    entities.reserve(params.entities.size());
    for (const EntityDefinition& definition : params.entities)
    {
        entities.push_back(instantiate(definition));
    }

    // Select the fixed radar engagement by the entities' stable identities.
    Entity& radar_entity = require_entity(entities, "blue_radar");
    Entity& radar_target = require_entity(entities, "red_missile");

    // Create the result series before the timestep loop starts appending values.
    Result result;
    const LoggingLayout logging_layout = initialize_entity_state_logging(
        entities,
        result
    );
    std::optional<GridSeries2D> range_doppler_history;
    MetricTable radar_state_history{
        .entity_id = radar_entity.id,
        .system = "radar",
        .key = "state",
        .name = "State Variables",
        .time_axis = Axis{
            .key = "simulation_time",
            .name = "Time",
            .unit = "s",
            .kind = "time"
        },
        .metrics = {
            MetricSeries{
                .key = "target_range",
                .name = "Target Range",
                .unit = "m"
            },
            MetricSeries{
                .key = "target_velocity",
                .name = "Target Velocity",
                .unit = "m/s"
            },
            MetricSeries{
                .key = "signal_to_noise",
                .name = "Signal-to-Noise Ratio",
                .unit = "dB"
            },
            MetricSeries{
                .key = "pulse_width",
                .name = "Pulse Width",
                .unit = "us",
                .values = {radar_entity.radar->p.pw_us}
            },
            MetricSeries{
                .key = "pulse_repetition_interval",
                .name = "Pulse Repetition Interval",
                .unit = "us",
                .values = {radar_entity.radar->p.pri_us}
            }
        },
        .presentation = Presentation{
            .order = 30
        }
    };

    // Log the current state, advance motion, then update radar once per timestep.
    for (std::size_t step = 0;
         static_cast<double>(step) * dt_s < duration_s;
         ++step)
    {
        const double sim_time_s = static_cast<double>(step) * dt_s;
        log_entity_states(entities, logging_layout, sim_time_s, result);

        for (Entity& entity : entities)
        {
            advance_kinematics(entity.kinematics, dt_s);
        }

        auto range_pulse = update_radar(radar_entity, radar_target);
        const RadarState& radar_state = radar_entity.radar->state;
        radar_state_history.time_axis.values.push_back(sim_time_s);
        radar_state_history.metrics[0].values.push_back(
            radar_state.target_range_m
        );
        radar_state_history.metrics[1].values.push_back(
            radar_state.target_vel_mps
        );
        radar_state_history.metrics[2].values.push_back(
            radar_state.signal_to_noise_db
        );

        if (range_pulse)
        {
            GridSeries2D frame = make_noisy_range_doppler_series(
                *range_pulse,
                radar_entity.radar->p,
                radar_entity.id,
                sim_time_s
            );
            if (!range_doppler_history)
            {
                range_doppler_history = std::move(frame);
            }
            else
            {
                range_doppler_history->time_axis.values.push_back(sim_time_s);
                range_doppler_history->values.insert(
                    range_doppler_history->values.end(),
                    frame.values.begin(),
                    frame.values.end()
                );
            }
        }
    }

    if (range_doppler_history)
    {
        result.grid_series.push_back(std::move(*range_doppler_history));
    }
    result.metric_tables.push_back(std::move(radar_state_history));

    // Run non-timestep analysis after the scenario history is complete.
    add_snr_range_curve(
        radar_entity.radar->p,
        radar_target.radar_signature_dbsm,
        params.radar_analysis,
        radar_entity.id,
        result
    );

    return result;
}
