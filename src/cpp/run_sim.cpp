#include "run_sim.hpp"
#include "rre.hpp"
#include "result.hpp"

Result run_sim(const Params& p)
{
    Result result;

    // Run the simulation functions
    auto packaged_rre = compute_rre(p.radar);

    // Add the analysis to the result
    result.analysis_2d.push_back(packaged_rre);

    return result;
}
