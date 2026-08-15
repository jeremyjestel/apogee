#include "run_sim.hpp"
#include "rre.hpp"
#include "result.hpp"

Result run_sim(const Params& p)
{
    Result result;

    double t = 0.0;
    double x = 0.0;


    auto [ranges_m, snr_db] = compute_rre(p.radar);

    

    return result;
}
