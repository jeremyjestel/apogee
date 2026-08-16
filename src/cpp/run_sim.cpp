#include "run_sim.hpp"
#include "radar_range.hpp"
#include "result.hpp"

Result run_sim(const Params& p)
{
    Result result;
    double sim_time_s = 0.0;
    //Simulation
    while (sim_time_s < p.simulation.duration_s){   
        // Need to assign objects in the world

    }   

    // System Analysis
    // Run the simulation functions
    auto packaged_rre = compute_radar_range(p.radar);

    // Add the analysis to the result
    result.analysis_2d.push_back(packaged_rre);



    return result;
}
