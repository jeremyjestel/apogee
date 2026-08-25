#pragma once

#include <tuple>

#include "params.hpp"

// Return received power, noise power, linear SNR, and SNR in dB for one range.
std::tuple<double, double, double, double> radar_snr_db(
    const RadarParams& radar,
    double target_rcs_dbsm,
    double range_m
);
