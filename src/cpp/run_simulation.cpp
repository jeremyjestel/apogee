#include "run_simulation.hpp"
#include "rre.hpp"

Result run_simulation(const Params& p)
{
    Result r;

    double t = 0.0;
    double x = 0.0;

    while (t <= p.simulation.duration_s)
    {
        r.history.push_back({t, x});

        x += p.missile.speed_mps * p.simulation.dt_s;
        t += p.simulation.dt_s;
    }

    auto [ranges_m, snr_db] = compute_rre(p.radar);

    r.ranges_m = ranges_m;
    r.snr_db = snr_db;

    return r;
}
