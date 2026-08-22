#include "run_sim.hpp"
#include "analysis/radar_range.hpp"
#include "core/entity.hpp"
#include "logging.hpp"
#include "parameter/result.hpp"
#include "params.hpp"
#include "systems/motion_system.hpp"

#include <cstddef>
#include <cmath>
#include <stdexcept>

Result run_sim(const Params& p)
{
    if (!std::isfinite(p.simulation.dt_s) || p.simulation.dt_s <= 0.0)
    {
        throw std::invalid_argument("Simulation dt_s must be finite and positive");
    }
    if (!std::isfinite(p.simulation.duration_s) || p.simulation.duration_s < 0.0)
    {
        throw std::invalid_argument("Simulation duration_s must be finite and non-negative");
    }
    if (p.simulation.coordinate_frame.empty())
    {
        throw std::invalid_argument("Simulation coordinate_frame cannot be empty");
    }

    std::vector<Entity> entities{
        Entity{
            .id = 1,
            .key = "blue_radar_1",
            .name = "Blue Radar",
            .type = "radar",
            .team = "blue",
            .kinematics = p.blue_radar.initial_kinematics
        },
        Entity{
            .id = 2,
            .key = "blue_satellite_1",
            .name = "Blue Satellite",
            .type = "satellite",
            .team = "blue",
            .kinematics = p.blue_satellite.initial_kinematics
        },
        Entity{
            .id = 3,
            .key = "red_missile_1",
            .name = "Red Missile",
            .type = "missile",
            .team = "red",
            .kinematics = p.red_missile.initial_kinematics
        },
        Entity{
            .id = 4,
            .key = "blue_interceptor_1",
            .name = "Blue Interceptor",
            .type = "interceptor",
            .team = "blue",
            .kinematics = p.blue_interceptor.initial_kinematics
        }
    };
    Result result;
    initialize_entity_state_logging(
        entities,
        p.simulation.coordinate_frame,
        result
    );

    const double dt_s = p.simulation.dt_s;

    // Simulation
    for (std::size_t step = 0; ; ++step)
    {
        const double sim_time_s = static_cast<double>(step) * dt_s;
        if (sim_time_s >= p.simulation.duration_s)
        {
            break;
        }

        log_entity_states(entities, sim_time_s, result);

        for (auto& entity : entities)
        {
            kinematic_update(entity, dt_s);
        }
    }

    // System analysis
    append_radar_range_analysis(p.blue_radar, entities.front().id, result);

    return result;
}
