#pragma once

#include "params.hpp"

struct RadarEquationResult
{
    double received_power_w = 0.0;
    double noise_power_w = 0.0;
    double snr_linear = 0.0;
    double snr_db = 0.0;
};

// Evaluate the monostatic radar equation for one range.
RadarEquationResult radar_range_equation(
    const RadarParams& radar,
    double target_rcs_dbsm,
    double range_m
);
