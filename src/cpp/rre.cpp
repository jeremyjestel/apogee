#include "rre.hpp"

#include <vector>
#include <cmath>


#include "params.hpp"
constexpr double BOLTZMANN_CONSTANT = 1.380649e-23;

std::pair<std::vector<double>, std::vector<double>> compute_rre(const RadarParams& radar)
{   
    std::vector<double> ranges_m;
    std::vector<double> snr_db;

    for (double x = 0.0; x <= radar.max_range_m; x += radar.range_step_m)
    {
        ranges_m.push_back(x);
        
        double numerator = radar.power_dbw + radar.tx_gain_db + radar.rx_gain_db + radar.RCS_dbsm + 20 * log10(radar.wavelength_m);

        double noise_term =  10 * log10(BOLTZMANN_CONSTANT) + 10 * log10(290) + radar.noise_figure_db + 10 * log10(radar.bandwidth_hz);
        double denominator = 3 * log10(4 * 3.141) + 40 * log10(x) + radar.system_loss_db + noise_term;

        double snr = numerator - denominator;

        snr_db.push_back(snr);
    }

    return {ranges_m, snr_db};
}
