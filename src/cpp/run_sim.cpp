#include "run_sim.hpp"
#include "analysis/radar_range.hpp"
#include "core/entity.hpp"
#include "logging.hpp"
#include "parameter/result.hpp"
#include "params.hpp"
#include "systems/motion_system.hpp"

Result run_sim(const Params& p)
{
    std::vector<Entity> entities{
        Entity{1, "blue radar", p.blue_radar.initial_kinematics},
        Entity{2, "blue satellite", p.blue_satellite.initial_kinematics},
        Entity{3, "red missile", p.red_missile.initial_kinematics},
        Entity{4, "blue interceptor", p.blue_interceptor.initial_kinematics}
    };
    Result result;

    double sim_time_s = 0.0;
    double dt_s = p.simulation.dt_s;

    //Simulation
    while (sim_time_s < p.simulation.duration_s){   
        log_entity_states(entities, sim_time_s, result.simulation_3d);

        for (auto& entity : entities){
            kinematic_update(entity, dt_s);
        }

        sim_time_s += dt_s;
    }   

    // System Analysis
    // Run the simulation functions
    auto packaged_rre = compute_radar_range(p.blue_radar);

    // Add the analysis to the result
    result.analysis_2d.push_back(packaged_rre);



    return result;
}
