#include "run_sim.hpp"

#include "analysis/radar_range.hpp"
#include "core/entity.hpp"
#include "logging.hpp"
#include "systems/motion_system.hpp"
#include "systems/radar_system.hpp"

#include <cmath>
#include <cstddef>
#include <stdexcept>
#include <vector>

Result run_sim(const Params& p)
{
    if (!std::isfinite(p.simulation.dt_s) || p.simulation.dt_s <= 0.0 ||
        !std::isfinite(p.simulation.duration_s) ||
        p.simulation.duration_s < 0.0)
    {
        throw std::invalid_argument(
            "Simulation time step must be positive and duration cannot be negative"
        );
    }

    std::vector<Entity> entities{
        Entity{
            .id = 1,
            .key = "blue_radar",
            .display_name = "Blue Radar",
            .type = "radar",
            .team = "blue",
            .kinematics = p.blue_radar.initial_kinematics,
            .radar = RadarModule{
                .params = p.blue_radar.radar
            }
        },
        Entity{
            .id = 2,
            .key = "blue_satellite",
            .display_name = "Blue Satellite",
            .type = "satellite",
            .team = "blue",
            .kinematics = p.blue_satellite.initial_kinematics
        },
        Entity{
            .id = 3,
            .key = "red_missile",
            .display_name = "Red Missile",
            .type = "missile",
            .team = "red",
            .kinematics = p.red_missile.initial_kinematics
        },
        Entity{
            .id = 4,
            .key = "blue_interceptor",
            .display_name = "Blue Interceptor",
            .type = "interceptor",
            .team = "blue",
            .kinematics = p.blue_interceptor.initial_kinematics
        }
    };

    Entity& blue_radar = entities[0];
    Entity& red_missile = entities[2];
    Result result;
    initialize_entity_state_logging(entities, result);

    const double dt_s = p.simulation.dt_s;

    for (std::size_t step = 0;
         static_cast<double>(step) * dt_s < p.simulation.duration_s;
         ++step)
    {
        const double sim_time_s = static_cast<double>(step) * dt_s;
        log_entity_states(entities, sim_time_s, result);

        for (Entity& entity : entities)
        {
            update_kinematics(entity.kinematics, dt_s);
        }

        radar_update(blue_radar, red_missile);
    }

    append_radar_range_analysis(
        blue_radar.radar->params,
        p.red_missile.radar_cross_section_dbsm,
        p.blue_radar.max_range_m,
        p.blue_radar.range_step_m,
        blue_radar.id,
        result
    );

    return result;
}
